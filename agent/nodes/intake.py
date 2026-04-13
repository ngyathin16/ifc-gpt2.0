"""
Intake node: receives the raw user message and prepares state for the pipeline.
"""
from __future__ import annotations

import re
from typing import Any

MAX_INPUT_LENGTH: int = 10_000

# Keywords that indicate the user has provided meaningful building context
_BUILDING_KEYWORDS: set[str] = {
    "house", "home", "residential", "apartment", "flat", "dwelling", "villa",
    "office", "commercial", "workplace", "tower", "highrise", "high-rise",
    "skyscraper", "mixed-use", "retail", "warehouse", "factory", "hospital",
    "school", "hotel", "storey", "story", "floor", "level",
}

_DIMENSION_PATTERN: re.Pattern[str] = re.compile(
    r"\d+\s*[mx×]\s*\d+|\d+\s*(?:stor(?:e?y|ies)|floors?|levels?|m\b)",
    re.IGNORECASE,
)


def _has_building_context(message: str) -> bool:
    """Check if the message contains enough building-related context."""
    lower = message.lower()
    has_keyword = any(kw in lower for kw in _BUILDING_KEYWORDS)
    has_dimension = bool(_DIMENSION_PATTERN.search(message))
    return has_keyword or has_dimension


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

    # Truncate extremely long inputs to prevent prompt injection / token waste
    if len(message) > MAX_INPUT_LENGTH:
        message = message[:MAX_INPUT_LENGTH]

    # Smart heuristic: flag for clarification only when the message
    # lacks building-related keywords AND dimension patterns
    needs_clarification = not _has_building_context(message)

    return {
        **state,
        "user_message": message,
        "needs_clarification": needs_clarification,
    }
