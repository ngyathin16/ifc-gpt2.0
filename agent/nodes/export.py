"""
Export node: finalises the pipeline and prepares the output state.
"""
from __future__ import annotations

from typing import Any


def export(state: dict[str, Any]) -> dict[str, Any]:
    """
    Final node that prepares the output for the API response.

    Expected state keys:
        - final_ifc_path: str
        - validation_result: dict
        - validation_passed: bool

    Produces:
        - status: str — "complete" or "error"
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
    }
