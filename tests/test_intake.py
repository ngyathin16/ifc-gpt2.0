"""Tests for agent/nodes/intake.py — input validation and heuristics."""
from __future__ import annotations

from agent.nodes.intake import intake, MAX_INPUT_LENGTH


class TestIntakeBasic:
    def test_empty_message_returns_error(self):
        state = {"user_message": ""}
        result = intake(state)
        assert result["error"] == "No message provided."
        assert result["needs_clarification"] is False

    def test_whitespace_only_returns_error(self):
        state = {"user_message": "   \n\t  "}
        result = intake(state)
        assert result["error"] == "No message provided."

    def test_valid_message_passes_through(self):
        state = {"user_message": "Build a 5-storey residential tower"}
        result = intake(state)
        assert result["user_message"] == "Build a 5-storey residential tower"
        assert "error" not in result


class TestIntakeSmartHeuristic:
    """Short messages with building keywords should NOT trigger clarification."""

    def test_short_but_valid_no_clarification(self):
        """'5-storey residential tower' is 3 words but perfectly clear."""
        state = {"user_message": "5-storey residential tower"}
        result = intake(state)
        assert result["needs_clarification"] is False

    def test_short_with_dimensions_no_clarification(self):
        state = {"user_message": "20m x 30m office"}
        result = intake(state)
        assert result["needs_clarification"] is False

    def test_vague_single_word_needs_clarification(self):
        state = {"user_message": "building"}
        result = intake(state)
        assert result["needs_clarification"] is True

    def test_vague_no_building_context(self):
        state = {"user_message": "make something nice"}
        result = intake(state)
        assert result["needs_clarification"] is True

    def test_detailed_prompt_no_clarification(self):
        state = {"user_message": "Build a 10-storey commercial office with curtain walls and a flat roof"}
        result = intake(state)
        assert result["needs_clarification"] is False


class TestIntakeInputSanitisation:
    def test_truncates_extremely_long_input(self):
        long_msg = "build a house " * 5000  # ~70K chars
        state = {"user_message": long_msg}
        result = intake(state)
        assert len(result["user_message"]) <= MAX_INPUT_LENGTH

    def test_strips_leading_trailing_whitespace(self):
        state = {"user_message": "  build a house  "}
        result = intake(state)
        assert result["user_message"] == "build a house"

    def test_preserves_original_state_keys(self):
        state = {"user_message": "build a house", "job_id": "abc123"}
        result = intake(state)
        assert result["job_id"] == "abc123"
