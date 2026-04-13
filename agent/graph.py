"""
Main LangGraph definition for IFC-GPT v2.

Pipeline: intake → clarify → plan → build → validate → (repair → build → validate) → export
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes.build import build
from agent.nodes.clarify import clarify
from agent.nodes.export import export
from agent.nodes.intake import intake
from agent.nodes.plan import plan
from agent.nodes.repair import repair
from agent.nodes.validate import validate
from agent.schemas import BuildingPlan


def _should_repair(state: dict[str, Any]) -> str:
    """Conditional edge: if validation failed and repair attempts < 2, go to repair."""
    if state.get("validation_passed", False):
        return "export"
    if state.get("repair_attempts", 0) >= 2:
        return "export"
    return "repair"


def _build_graph() -> StateGraph:
    """Construct the LangGraph pipeline."""
    graph = StateGraph(dict)

    # Add nodes
    graph.add_node("intake", intake)
    graph.add_node("clarify", clarify)
    graph.add_node("plan", plan)
    graph.add_node("build", build)
    graph.add_node("validate", validate)
    graph.add_node("repair", repair)
    graph.add_node("export", export)

    # Linear edges
    graph.set_entry_point("intake")
    graph.add_edge("intake", "clarify")
    graph.add_edge("clarify", "plan")
    graph.add_edge("plan", "build")
    graph.add_edge("build", "validate")

    # Conditional: validate → export or repair
    graph.add_conditional_edges("validate", _should_repair, {
        "export": "export",
        "repair": "repair",
    })

    # Repair loops back to build
    graph.add_edge("repair", "build")

    # Export is terminal
    graph.add_edge("export", END)

    return graph


# Compiled graph singleton
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph().compile()
    return _compiled_graph


def run_pipeline(
    user_message: str,
    selected_features: list[str] | None = None,
    floor_to_floor_height: float | None = None,
) -> dict[str, Any]:
    """
    Run the full generation pipeline from a text prompt.

    Args:
        user_message: The raw user prompt.
        selected_features: Optional list of feature IDs from the frontend
            feature menu.  Passed to the clarify node.
        floor_to_floor_height: Optional user-specified floor-to-floor height
            in metres.  Passed to the clarify node.

    Returns the final state dict with keys:
        - final_ifc_path: str
        - validation_result: dict
        - status: str
    """
    graph = _get_graph()
    initial_state: dict[str, Any] = {
        "user_message": user_message,
        "repair_attempts": 0,
    }
    if selected_features:
        initial_state["selected_features"] = selected_features
    if floor_to_floor_height is not None:
        initial_state["floor_to_floor_height"] = floor_to_floor_height
    return graph.invoke(initial_state)


def run_pipeline_from_plan(plan_dict: dict) -> dict[str, Any]:
    """
    Run the build pipeline from an already-formed BuildingPlan JSON.
    Skips intake/clarify/plan nodes — goes straight to build.
    """
    building_plan = BuildingPlan.model_validate(plan_dict)

    # Build a mini-graph: build → validate → (repair → build → validate) → export
    mini = StateGraph(dict)
    mini.add_node("build", build)
    mini.add_node("validate", validate)
    mini.add_node("repair", repair)
    mini.add_node("export", export)

    mini.set_entry_point("build")
    mini.add_edge("build", "validate")
    mini.add_conditional_edges("validate", _should_repair, {
        "export": "export",
        "repair": "repair",
    })
    mini.add_edge("repair", "build")
    mini.add_edge("export", END)

    compiled = mini.compile()
    initial_state = {
        "building_plan": building_plan,
        "building_plan_json": building_plan.model_dump(),
        "repair_attempts": 0,
    }
    return compiled.invoke(initial_state)


def run_modify_pipeline(guid: str, instruction: str, ifc_url: str) -> dict[str, Any]:
    """
    Run a modification pipeline targeting a specific GUID in an existing IFC.

    This is a simplified pipeline: the LLM interprets the instruction and
    produces a modification plan that gets applied to the existing file.

    For v2.0, this is a placeholder that re-runs the full pipeline with
    the modification context. A proper element-level modification system
    will be implemented in a future iteration.
    """
    message = (
        f"Modify the element with GUID {guid} in the existing model. "
        f"Instruction: {instruction}. "
        f"Current IFC file: {ifc_url}"
    )
    return run_pipeline(message)
