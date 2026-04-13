"""Tests for agent/nodes/plan.py — JSON extraction and storey replication."""
from __future__ import annotations


import pytest

from agent.nodes.plan import _expand_typical_storey, _extract_json


class TestExtractJson:
    """Test robust JSON extraction from LLM output."""

    def test_clean_json(self):
        raw = '{"building_name": "Tower", "num_storeys": 5}'
        assert _extract_json(raw) == {"building_name": "Tower", "num_storeys": 5}

    def test_markdown_fenced_json(self):
        raw = '```json\n{"building_name": "Tower"}\n```'
        assert _extract_json(raw) == {"building_name": "Tower"}

    def test_markdown_no_language_tag(self):
        raw = '```\n{"building_name": "Tower"}\n```'
        assert _extract_json(raw) == {"building_name": "Tower"}

    def test_text_before_json(self):
        raw = 'Here is the plan:\n{"building_name": "Tower", "num_storeys": 5}'
        assert _extract_json(raw) == {"building_name": "Tower", "num_storeys": 5}

    def test_text_after_json(self):
        raw = '{"building_name": "Tower"}\nHope this helps!'
        assert _extract_json(raw) == {"building_name": "Tower"}

    def test_nested_json(self):
        raw = '{"storeys": [{"ref": "F00"}], "elements": []}'
        result = _extract_json(raw)
        assert result["storeys"] == [{"ref": "F00"}]

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            _extract_json("This is not JSON at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            _extract_json("")

    def test_multiple_markdown_fences(self):
        raw = 'Some text\n```json\n{"a": 1}\n```\nMore text\n```json\n{"b": 2}\n```'
        # Should extract the first valid JSON
        assert _extract_json(raw) == {"a": 1}


class TestExpandTypicalStorey:
    def test_no_typical_ref_passthrough(self):
        raw = {"storeys": [{"storey_ref": "F00"}], "elements": []}
        result = _expand_typical_storey(raw)
        assert result == {"storeys": [{"storey_ref": "F00"}], "elements": []}

    def test_replicates_elements(self):
        raw = {
            "typical_storey_ref": "F01",
            "storeys": [
                {"storey_ref": "F00"},
                {"storey_ref": "F01"},
                {"storey_ref": "F02"},
                {"storey_ref": "F03"},
                {"storey_ref": "F04"},  # top
            ],
            "elements": [
                {"storey_ref": "F00", "element_type": "slab"},
                {"storey_ref": "F01", "element_type": "wall", "wall_ref": "W1_F01"},
                {"storey_ref": "F04", "element_type": "roof"},
            ],
        }
        result = _expand_typical_storey(raw)
        # F02 and F03 should get copies of F01's wall
        f02_walls = [e for e in result["elements"] if e["storey_ref"] == "F02" and e["element_type"] == "wall"]
        f03_walls = [e for e in result["elements"] if e["storey_ref"] == "F03" and e["element_type"] == "wall"]
        assert len(f02_walls) == 1
        assert f02_walls[0]["wall_ref"] == "W1_F02"
        assert len(f03_walls) == 1
        assert f03_walls[0]["wall_ref"] == "W1_F03"
