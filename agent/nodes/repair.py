"""
Repair node: if validation fails, ask the LLM to fix the BuildingPlan and rebuild.

Uses **targeted repair**: extracts only error-relevant elements and their storey
context, sends a smaller payload to the LLM, and merges the patches back into
the full plan.  Falls back to full-plan repair when errors cannot be localised.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.schemas import BuildingPlan

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Regex patterns to extract storey refs and wall refs from error messages
_STOREY_REF_RE = re.compile(r"\b(F\d{2,3})\b")
_WALL_REF_RE = re.compile(r"\b(W\d+_F\d{2,3})\b")


# ---------------------------------------------------------------------------
# Targeted repair helpers
# ---------------------------------------------------------------------------

def _extract_error_context(
    plan_json: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    """Extract only the elements relevant to the validation errors.

    Scans error messages for storey refs (F00, F01, …) and wall refs
    (W1_F00, …), then returns a subset of the plan containing only
    those storeys and their elements.

    Falls back to the full plan if no refs can be extracted.
    """
    affected_storeys: set[str] = set()
    affected_walls: set[str] = set()

    for err in errors:
        affected_storeys.update(_STOREY_REF_RE.findall(err))
        affected_walls.update(_WALL_REF_RE.findall(err))

    # If wall refs found, include their storeys too
    for wref in affected_walls:
        # Wall ref format: W<n>_F<nn> — storey ref is the F<nn> suffix
        parts = wref.split("_")
        if len(parts) >= 2:
            sref = "_".join(parts[1:])
            affected_storeys.add(sref)

    # Fallback: if we couldn't localise, return the full plan
    if not affected_storeys:
        return {
            "storeys": list(plan_json.get("storeys", [])),
            "elements": list(plan_json.get("elements", [])),
        }

    # Filter storeys
    filtered_storeys = [
        s for s in plan_json.get("storeys", [])
        if s.get("storey_ref") in affected_storeys
    ]

    # Filter elements: include those on affected storeys OR referencing affected walls
    filtered_elements = []
    for elem in plan_json.get("elements", []):
        if elem.get("storey_ref") in affected_storeys:
            filtered_elements.append(elem)
        elif elem.get("host_wall_ref") in affected_walls:
            filtered_elements.append(elem)

    return {
        "storeys": filtered_storeys,
        "elements": filtered_elements,
    }


def _merge_repaired_elements(
    original: dict[str, Any],
    repaired: dict[str, Any],
    affected_storeys: set[str],
) -> dict[str, Any]:
    """Merge LLM-repaired elements back into the original plan.

    Replaces elements on affected storeys with the repaired versions,
    preserving all elements on unaffected storeys.
    """
    # Keep elements that are NOT on affected storeys
    kept_elements = [
        e for e in original.get("elements", [])
        if e.get("storey_ref") not in affected_storeys
    ]
    # Add repaired elements
    repaired_elements = repaired.get("elements", [])
    merged_elements = kept_elements + repaired_elements

    # Build merged plan — preserve all original keys, only replace elements
    merged = {**original, "elements": merged_elements}
    return merged


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def repair(state: dict[str, Any]) -> dict[str, Any]:
    """
    If validation failed, use the LLM to repair the BuildingPlan.

    Uses targeted repair: sends only error-relevant elements to the LLM,
    then merges the repaired subset back into the full plan.

    Expected state keys:
        - validation_passed: bool
        - validation_result: dict
        - building_plan_json: dict
        - repair_attempts: int (auto-tracked)

    Produces:
        - building_plan: BuildingPlan (repaired)
        - building_plan_json: dict
        - repair_attempts: int
    """
    if state.get("validation_passed", True):
        return state

    attempts = state.get("repair_attempts", 0)
    if attempts >= 2:
        return {
            **state,
            "error": "Validation failed after 2 repair attempts.",
        }

    from agent.llm import extract_text, get_llm
    from agent.nodes.plan import _extract_json

    llm = get_llm(temperature=0.1)

    system_prompt = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
    repair_template = (PROMPTS_DIR / "repair.txt").read_text(encoding="utf-8")

    # Prefer the flat error list — easier for LLM to parse
    validation_result = state.get("validation_result", {})
    error_list: list[str] = validation_result.get("all_errors", [])
    if error_list:
        validation_text = "\n".join(f"  - {e}" for e in error_list)
    else:
        validation_text = json.dumps(validation_result, indent=2)

    plan_json = state.get("building_plan_json", {})

    # --- Targeted repair: extract only error-relevant subset ---
    error_context = _extract_error_context(plan_json, error_list)
    affected_storeys = {s.get("storey_ref") for s in error_context.get("storeys", [])}
    is_targeted = affected_storeys and affected_storeys != {
        s.get("storey_ref") for s in plan_json.get("storeys", [])
    }

    if is_targeted:
        plan_payload = json.dumps(error_context, indent=2)
        logger.info(
            "[repair] Targeted repair: %d storeys, %d elements (vs %d total)",
            len(error_context["storeys"]),
            len(error_context["elements"]),
            len(plan_json.get("elements", [])),
        )
    else:
        plan_payload = json.dumps(plan_json, indent=2)
        logger.info("[repair] Full-plan repair (errors not localisable)")

    user_prompt = repair_template.replace(
        "{validation_results}", validation_text
    ).replace(
        "{building_plan}", plan_payload
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    content = extract_text(response)

    try:
        raw = _extract_json(content)
    except ValueError as e:
        logger.error("[repair] JSON extraction failed: %s", e)
        return {
            **state,
            "error": f"Repair LLM returned unparseable output: {e}",
            "repair_attempts": attempts + 1,
        }

    # --- Merge repaired elements back ---
    if is_targeted:
        merged = _merge_repaired_elements(plan_json, raw, affected_storeys)
    else:
        merged = raw

    try:
        repaired_plan = BuildingPlan.model_validate(merged)
    except Exception as e:
        logger.error("[repair] Repaired plan validation failed: %s", e)
        return {
            **state,
            "error": f"Repaired plan is invalid: {e}",
            "repair_attempts": attempts + 1,
        }

    return {
        **state,
        "building_plan": repaired_plan,
        "building_plan_json": repaired_plan.model_dump(),
        "repair_attempts": attempts + 1,
        "validation_passed": False,  # Will be re-validated
    }
