"""
Plan node: converts the detailed description into a structured BuildingPlan JSON.
Uses the LLM with structured output to produce valid BuildingPlan schema.

Supports **storey replication**: for multi-storey buildings the LLM only outputs
elements for ground floor, one typical floor, and the top floor.  This node
copies the typical-floor elements to every intermediate storey, cutting LLM
output by 80-90 % and avoiding timeouts.
"""
from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.schemas import BuildingPlan

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Regex to find the first top-level JSON object in a string
_JSON_OBJECT_RE = re.compile(r"\{", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any]:
    """Robustly extract a JSON object from LLM output.

    Handles:
    - Clean JSON
    - Markdown-fenced JSON (```json ... ``` or ``` ... ```)
    - Stray text before/after the JSON object
    - Multiple markdown blocks (takes the first valid one)

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    text = text.strip()
    if not text:
        raise ValueError("Could not extract valid JSON from empty response")

    # Strategy 1: Strip markdown fences
    fence_pattern = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)
    fence_matches = fence_pattern.findall(text)
    for candidate in fence_matches:
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Strategy 2: Find the first '{' and try to parse from there
    for match in _JSON_OBJECT_RE.finditer(text):
        start = match.start()
        # Try progressively shorter substrings from this position
        candidate = text[start:]
        # Find matching closing brace by trying json.loads
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Try trimming trailing non-JSON text
            for end_pos in range(len(candidate), 0, -1):
                if candidate[end_pos - 1] == '}':
                    try:
                        return json.loads(candidate[:end_pos])
                    except json.JSONDecodeError:
                        continue
            continue

    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:200]}")


def _expand_typical_storey(raw: dict) -> dict:
    """Replicate typical-floor elements to all intermediate storeys.

    If the LLM set ``typical_storey_ref`` (e.g. ``"F01"``), every element
    on that storey is cloned to storeys F02 … F(N-2) (all storeys between
    the typical floor and the top floor that have no elements yet).
    """
    typical_ref = raw.pop("typical_storey_ref", None)
    if not typical_ref:
        return raw

    storey_refs = [s["storey_ref"] for s in raw.get("storeys", [])]
    if typical_ref not in storey_refs:
        logger.warning("typical_storey_ref %r not in storeys; skipping replication", typical_ref)
        return raw

    # Identify which storeys already have elements
    populated = {e["storey_ref"] for e in raw.get("elements", [])}
    # Storeys that need replication: between typical and top, not already populated
    typical_idx = storey_refs.index(typical_ref)
    top_idx = len(storey_refs) - 1
    targets = [
        storey_refs[i]
        for i in range(typical_idx + 1, top_idx)
        if storey_refs[i] not in populated
    ]

    if not targets:
        return raw

    # Collect template elements + junctions from the typical floor
    template_elements = [e for e in raw["elements"] if e["storey_ref"] == typical_ref]
    template_junctions = [
        j for j in raw.get("wall_junctions", [])
        if any(
            e.get("wall_ref") == j.get("wall_ref_1") or e.get("wall_ref") == j.get("wall_ref_2")
            for e in template_elements
        )
    ]

    logger.info(
        "Replicating %d elements from %s to %d storeys (%s … %s)",
        len(template_elements), typical_ref, len(targets), targets[0], targets[-1],
    )

    for target_ref in targets:
        for elem in template_elements:
            clone = copy.deepcopy(elem)
            clone["storey_ref"] = target_ref
            # Rename refs to avoid collisions (append _FXX suffix)
            for key in ("wall_ref", "column_ref", "beam_ref", "name"):
                if key in clone and isinstance(clone[key], str):
                    clone[key] = clone[key].replace(typical_ref, target_ref)
            # host_wall_ref for doors/windows
            if "host_wall_ref" in clone and isinstance(clone["host_wall_ref"], str):
                clone["host_wall_ref"] = clone["host_wall_ref"].replace(typical_ref, target_ref)
            raw["elements"].append(clone)

        for junc in template_junctions:
            clone_j = copy.deepcopy(junc)
            for key in ("wall_ref_1", "wall_ref_2"):
                if key in clone_j and isinstance(clone_j[key], str):
                    clone_j[key] = clone_j[key].replace(typical_ref, target_ref)
            raw.setdefault("wall_junctions", []).append(clone_j)

    return raw


def plan(state: dict[str, Any]) -> dict[str, Any]:
    """
    Use the LLM to generate a BuildingPlan from the detailed description.

    Expected state keys:
        - detailed_description: str

    Produces:
        - building_plan: BuildingPlan — validated Pydantic model
        - building_plan_json: dict — raw JSON for serialisation
    """
    from agent.llm import get_llm

    llm = get_llm(temperature=0.1)

    system_prompt = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
    plan_template = (PROMPTS_DIR / "plan.txt").read_text(encoding="utf-8")
    user_prompt = plan_template.replace("{user_message}", state["detailed_description"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    from agent.llm import extract_text

    response = llm.invoke(messages)
    content = extract_text(response)

    try:
        raw = _extract_json(content)
    except ValueError as e:
        logger.error("[plan] JSON extraction failed: %s", e)
        raise

    # Check if the LLM returned high-level parameters (new fast path)
    # vs a full BuildingPlan (legacy path)
    if "features" in raw and "elements" not in raw:
        # LLM returned building parameters — use deterministic plan generator
        logger.info("[plan] LLM returned parameters, using deterministic generator")
        from generate_highrise import generate_plan as _gen_plan
        plan_dict = _gen_plan(
            features=raw.get("features"),
            num_storeys=raw.get("num_storeys"),
            floor_height=raw.get("floor_to_floor_height"),
            building_width=raw.get("building_width"),
            building_length=raw.get("building_length"),
        )
        # Merge LLM-provided metadata
        plan_dict["description"] = state.get("detailed_description", plan_dict.get("description", ""))
        if raw.get("building_name"):
            plan_dict.setdefault("building", {})["name"] = raw["building_name"]
        if raw.get("building_type"):
            plan_dict.setdefault("building", {})["building_type"] = raw["building_type"]
        building_plan = BuildingPlan.model_validate(plan_dict)
    else:
        # Legacy path: LLM returned a full BuildingPlan JSON
        raw = _expand_typical_storey(raw)
        building_plan = BuildingPlan.model_validate(raw)

    return {
        **state,
        "building_plan": building_plan,
        "building_plan_json": building_plan.model_dump(),
    }
