"""
Export node: final node that prepares the output for the API response.
"""
from __future__ import annotations

from typing import Any


def _build_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract summary statistics from the pipeline state."""
    entities = state.get("ifc_entities", {})
    validation = state.get("validation_result", {})

    # Count validation warnings across layers
    warning_count = 0
    for layer in ("schema", "semantic"):
        layer_result = validation.get(layer, {})
        warning_count += layer_result.get("warning_count", 0)

    return {
        "element_count": len(entities),
        "repair_attempts": state.get("repair_attempts", 0),
        "validation_warnings": warning_count,
        "ifc_path": state.get("final_ifc_path", ""),
    }


def export(state: dict[str, Any]) -> dict[str, Any]:
    """
    Final node: package the result for the API.

    Expected state keys:
        - final_ifc_path: str (optional)
        - error: str (optional)

    Produces:
        - status: "complete" | "error"
        - summary: dict (on success)
    """
    if state.get("error"):
        return {
            **state,
            "status": "error",
        }

    if not state.get("final_ifc_path"):
        return {
            **state,
            "status": "error",
            "error": "No IFC file was generated.",
        }

    return {
        **state,
        "status": "complete",
        "summary": _build_summary(state),
    }
