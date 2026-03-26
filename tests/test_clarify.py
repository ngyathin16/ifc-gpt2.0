"""Tests for agent/nodes/clarify.py — feature menu and inference."""
from __future__ import annotations

from agent.nodes.clarify import (
    BUILDING_FEATURES,
    _infer_building_type,
    _infer_defaults,
    _infer_storeys,
    _resolve_conflicts,
    clarify,
)


class TestInferBuildingType:
    def test_residential_keywords(self):
        assert _infer_building_type("Build me a house") == "residential"
        assert _infer_building_type("3-storey apartment building") == "residential"

    def test_commercial_keywords(self):
        assert _infer_building_type("10-storey office tower") == "commercial"

    def test_highrise_keywords(self):
        assert _infer_building_type("A 40-storey highrise") == "highrise"
        assert _infer_building_type("skyscraper in CBD") == "highrise"

    def test_fallback_residential(self):
        assert _infer_building_type("build something") == "residential"


class TestInferStoreys:
    def test_extracts_storey_count(self):
        assert _infer_storeys("20 storey building") == 20
        assert _infer_storeys("a 5-floor office") == 5
        assert _infer_storeys("3 levels") == 3

    def test_default_single_storey(self):
        assert _infer_storeys("build a house") == 1


class TestInferDefaults:
    def test_highrise_override(self):
        """Many storeys should auto-promote to highrise."""
        defaults = _infer_defaults("a 10-storey residential building")
        assert defaults["building_type"] == "highrise"
        assert defaults["num_storeys"] == 10
        assert defaults["floor_to_floor_height"] == 3.5

    def test_residential_defaults(self):
        defaults = _infer_defaults("build me a house")
        assert defaults["building_type"] == "residential"
        assert "exterior_walls" in defaults["default_features"]
        assert "pitched_roof" in defaults["default_features"]

    def test_commercial_defaults(self):
        defaults = _infer_defaults("a 4-storey office")
        assert defaults["building_type"] == "commercial"
        assert "columns" in defaults["default_features"]
        assert "elevators" in defaults["default_features"]


class TestClarifyNode:
    def test_basic_expansion(self):
        state = {"user_message": "build a house", "needs_clarification": True}
        result = clarify(state)
        assert "detailed_description" in result
        assert "residential" in result["detailed_description"].lower()
        assert "storey-relative" in result["detailed_description"].lower()

    def test_selected_features_override(self):
        state = {
            "user_message": "build a 5-storey office",
            "needs_clarification": False,
            "selected_features": ["columns", "curtain_wall", "flat_roof"],
        }
        result = clarify(state)
        desc = result["detailed_description"]
        assert "Curtain wall glazing" in desc
        assert "Structural columns" in desc
        # Should NOT have pitched roof since we selected flat_roof
        assert "Pitched" not in desc

    def test_no_features_uses_defaults(self):
        state = {"user_message": "a 20-storey highrise tower", "needs_clarification": False}
        result = clarify(state)
        desc = result["detailed_description"]
        assert "highrise" in desc.lower()
        # Highrise defaults should include elevators
        assert "Elevator" in desc

    def test_inferred_defaults_in_state(self):
        state = {"user_message": "build a house", "needs_clarification": True}
        result = clarify(state)
        assert "inferred_defaults" in result
        assert result["inferred_defaults"]["building_type"] == "residential"


class TestFeatureCatalog:
    def test_catalog_not_empty(self):
        assert len(BUILDING_FEATURES) > 0

    def test_all_features_have_required_keys(self):
        for f in BUILDING_FEATURES:
            assert "id" in f
            assert "category" in f
            assert "label" in f
            assert "description" in f
            assert "default_for" in f

    def test_unique_ids(self):
        ids = [f["id"] for f in BUILDING_FEATURES]
        assert len(ids) == len(set(ids))


class TestResolveConflicts:
    """User-selected features should override conflicting defaults."""

    def test_interior_partitions_removes_open_plan(self):
        selected = ["columns", "open_plan", "interior_partitions", "floor_slabs"]
        user_chosen = ["interior_partitions"]
        result = _resolve_conflicts(selected, user_chosen)
        assert "interior_partitions" in result
        assert "open_plan" not in result

    def test_curtain_wall_removes_exterior_walls(self):
        selected = ["exterior_walls", "curtain_wall", "columns"]
        user_chosen = ["curtain_wall"]
        result = _resolve_conflicts(selected, user_chosen)
        assert "curtain_wall" in result
        assert "exterior_walls" not in result
        assert "columns" in result

    def test_pitched_roof_removes_flat_roof(self):
        selected = ["flat_roof", "pitched_roof"]
        user_chosen = ["pitched_roof"]
        result = _resolve_conflicts(selected, user_chosen)
        assert "pitched_roof" in result
        assert "flat_roof" not in result

    def test_no_conflicts_keeps_all(self):
        selected = ["columns", "beams", "stairs"]
        user_chosen = ["stairs"]
        result = _resolve_conflicts(selected, user_chosen)
        assert result == selected

    def test_user_picks_both_conflicting_keeps_both(self):
        """If user explicitly picks both conflicting features, keep both."""
        selected = ["interior_partitions", "open_plan"]
        user_chosen = ["interior_partitions", "open_plan"]
        result = _resolve_conflicts(selected, user_chosen)
        assert "interior_partitions" in result
        assert "open_plan" in result

    def test_clarify_node_resolves_conflicts(self):
        """End-to-end: clarify node with user selecting interior_partitions
        should drop the default open_plan for a highrise."""
        state = {
            "user_message": "20-storey highrise tower",
            "needs_clarification": False,
            "selected_features": ["interior_partitions"],
        }
        result = clarify(state)
        desc = result["detailed_description"]
        assert "Interior partition walls" in desc
        assert "Open-plan" not in desc
