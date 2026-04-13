"""Tests for agent/nodes/repair.py — targeted repair extraction."""
from __future__ import annotations

from agent.nodes.repair import _extract_error_context, _merge_repaired_elements


class TestExtractErrorContext:
    """Verify that only error-relevant elements are extracted."""

    def test_extracts_wall_from_enclosure_error(self):
        plan_json = {
            "storeys": [
                {"storey_ref": "F00", "name": "Ground", "elevation": 0.0, "floor_to_floor_height": 3.0},
            ],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0], "height": 3.0, "thickness": 0.2},
                {"element_type": "slab", "storey_ref": "F00",
                 "boundary_points": [[0, 0], [10, 0], [10, 10], [0, 10]], "depth": 0.2},
                {"element_type": "wall", "wall_ref": "W1_F01", "storey_ref": "F01",
                 "start_point": [0, 0], "end_point": [10, 0], "height": 3.0, "thickness": 0.2},
            ],
        }
        errors = [
            "[plan] WALL ENCLOSURE: Storey F00 — walls don't form closed loop",
        ]
        context = _extract_error_context(plan_json, errors)
        # Should include F00 storey and its elements, but NOT F01
        storey_refs = {s["storey_ref"] for s in context["storeys"]}
        assert "F00" in storey_refs
        elem_storeys = {e["storey_ref"] for e in context["elements"]}
        assert "F00" in elem_storeys
        assert "F01" not in elem_storeys

    def test_extracts_opening_from_bounds_error(self):
        plan_json = {
            "storeys": [
                {"storey_ref": "F00", "name": "Ground", "elevation": 0.0, "floor_to_floor_height": 3.0},
            ],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0], "height": 3.0, "thickness": 0.2},
                {"element_type": "door", "storey_ref": "F00",
                 "host_wall_ref": "W1_F00", "distance_along_wall": 12.0,
                 "width": 0.9, "height": 2.1},
            ],
        }
        errors = [
            "[plan] OPENING BOUNDS: door on W1_F00 at 12.0 exceeds wall length",
        ]
        context = _extract_error_context(plan_json, errors)
        # Should include the door and its host wall
        element_types = {e["element_type"] for e in context["elements"]}
        assert "door" in element_types
        assert "wall" in element_types

    def test_fallback_returns_full_plan_for_unknown_errors(self):
        plan_json = {
            "storeys": [
                {"storey_ref": "F00", "name": "Ground", "elevation": 0.0, "floor_to_floor_height": 3.0},
                {"storey_ref": "F01", "name": "Floor 1", "elevation": 3.0, "floor_to_floor_height": 3.0},
            ],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0]},
                {"element_type": "wall", "wall_ref": "W1_F01", "storey_ref": "F01",
                 "start_point": [0, 0], "end_point": [10, 0]},
            ],
        }
        errors = ["[schema] Some obscure error"]
        context = _extract_error_context(plan_json, errors)
        # Fallback: returns the full plan
        assert len(context["storeys"]) == 2
        assert len(context["elements"]) == 2


class TestMergeRepairedElements:
    """Verify patched elements merge correctly into the original plan."""

    def test_merges_updated_elements(self):
        original = {
            "description": "Test",
            "storeys": [
                {"storey_ref": "F00", "name": "Ground", "elevation": 0.0, "floor_to_floor_height": 3.0},
            ],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0], "height": 3.0, "thickness": 0.2},
                {"element_type": "slab", "storey_ref": "F00",
                 "boundary_points": [[0, 0], [10, 0], [10, 10], [0, 10]], "depth": 0.2},
            ],
        }
        # LLM returned repaired elements for F00
        repaired = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0], "height": 3.0, "thickness": 0.25},
                {"element_type": "wall", "wall_ref": "W2_F00", "storey_ref": "F00",
                 "start_point": [10, 0], "end_point": [10, 10], "height": 3.0, "thickness": 0.25},
                {"element_type": "slab", "storey_ref": "F00",
                 "boundary_points": [[0, 0], [10, 0], [10, 10], [0, 10]], "depth": 0.2},
            ],
        }
        affected_storeys = {"F00"}
        merged = _merge_repaired_elements(original, repaired, affected_storeys)

        # F00 elements should be replaced with the repaired version
        f00_elements = [e for e in merged["elements"] if e["storey_ref"] == "F00"]
        assert len(f00_elements) == 3  # 2 walls + 1 slab (repaired added W2)
        # Original metadata preserved
        assert merged["description"] == "Test"

    def test_preserves_unaffected_storey_elements(self):
        original = {
            "description": "Test",
            "storeys": [
                {"storey_ref": "F00", "name": "Ground", "elevation": 0.0, "floor_to_floor_height": 3.0},
                {"storey_ref": "F01", "name": "Floor 1", "elevation": 3.0, "floor_to_floor_height": 3.0},
            ],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0]},
                {"element_type": "wall", "wall_ref": "W1_F01", "storey_ref": "F01",
                 "start_point": [0, 0], "end_point": [10, 0]},
            ],
        }
        repaired = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1_F00", "storey_ref": "F00",
                 "start_point": [0, 0], "end_point": [10, 0], "thickness": 0.25},
            ],
        }
        affected_storeys = {"F00"}
        merged = _merge_repaired_elements(original, repaired, affected_storeys)

        # F01 wall should be untouched
        f01_elements = [e for e in merged["elements"] if e["storey_ref"] == "F01"]
        assert len(f01_elements) == 1
        assert f01_elements[0]["wall_ref"] == "W1_F01"
