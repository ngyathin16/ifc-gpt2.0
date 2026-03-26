"""
Repair node: if validation fails, ask the LLM to fix the BuildingPlan and rebuild.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.schemas import BuildingPlan

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def repair(state: dict[str, Any]) -> dict[str, Any]:
    """
    If validation failed, use the LLM to repair the BuildingPlan.

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
        # Stop after 2 repair attempts to avoid infinite loops
        return {
            **state,
            "error": "Validation failed after 2 repair attempts.",
        }

    from agent.llm import get_llm

    llm = get_llm(temperature=0.1)

    system_prompt = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
    repair_template = (PROMPTS_DIR / "repair.txt").read_text(encoding="utf-8")

    # Prefer the flat error list for the repair prompt — much easier for the LLM to parse
    validation_result = state.get("validation_result", {})
    error_list = validation_result.get("all_errors", [])
    if error_list:
        validation_text = "\n".join(f"  - {e}" for e in error_list)
    else:
        validation_text = json.dumps(validation_result, indent=2)

    user_prompt = repair_template.replace(
        "{validation_results}", validation_text
    ).replace(
        "{building_plan}", json.dumps(state.get("building_plan_json", {}), indent=2)
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    from agent.llm import extract_text

    response = llm.invoke(messages)
    content = extract_text(response)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    repaired_plan = BuildingPlan.model_validate_json(content)

    return {
        **state,
        "building_plan": repaired_plan,
        "building_plan_json": repaired_plan.model_dump(),
        "repair_attempts": attempts + 1,
        "validation_passed": False,  # Will be re-validated
    }
