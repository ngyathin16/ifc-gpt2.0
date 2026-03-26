"""
Intake node: receives the raw user message and prepares state for the pipeline.
"""
from __future__ import annotations

from typing import Any


def intake(state: dict[str, Any]) -> dict[str, Any]:
    """
    Initial node that validates input and normalises the user message.

    Expected state keys:
        - user_message: str — raw user input

    Produces:
        - user_message: str — cleaned message
        - needs_clarification: bool — whether the message needs clarification
    """
    message = state.get("user_message", "").strip()

    if not message:
        return {
            **state,
            "error": "No message provided.",
            "needs_clarification": False,
        }

    # Basic heuristic: if message is too short, flag for clarification
    needs_clarification = len(message.split()) < 5

    return {
        **state,
        "user_message": message,
        "needs_clarification": needs_clarification,
    }
