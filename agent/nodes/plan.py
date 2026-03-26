"""
Plan node: converts the detailed description into a structured BuildingPlan JSON.
Uses the LLM with structured output to produce valid BuildingPlan schema.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.schemas import BuildingPlan


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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
    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    building_plan = BuildingPlan.model_validate_json(content)

    return {
        **state,
        "building_plan": building_plan,
        "building_plan_json": building_plan.model_dump(),
    }
