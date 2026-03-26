"""Tests for building_blocks/bsdd.py — cache, fallbacks, enrichment, and validation."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from building_blocks.bsdd import (
    COMMON_PSET_MAP,
    FALLBACK_PSET_PROPERTIES,
    _cache,
    _get_cached,
    _set_cached,
    clear_cache,
    get_pset_summary_for_features,
    get_standard_psets_sync,
    get_valid_pset_property_names,
)


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Ensure each test starts with a clean cache."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------

class TestCache:
    def test_set_and_get(self):
        _set_cached("key1", {"data": 42})
        assert _get_cached("key1") == {"data": 42}

    def test_missing_key_returns_none(self):
        assert _get_cached("nonexistent") is None

    def test_clear_cache(self):
        _set_cached("a", 1)
        _set_cached("b", 2)
        clear_cache()
        assert _get_cached("a") is None
        assert _get_cached("b") is None

    def test_expired_entry_returns_none(self):
        import time as _time

        _set_cached("old", "value")
        # Manually expire the entry
        _cache["old"] = (_time.time() - 7200, "value")
        assert _get_cached("old") is None


# ---------------------------------------------------------------------------
# Fallback data integrity
# ---------------------------------------------------------------------------

class TestFallbackData:
    def test_common_pset_map_covers_main_classes(self):
        for cls in ("IfcWall", "IfcDoor", "IfcWindow", "IfcColumn",
                     "IfcBeam", "IfcSlab", "IfcRoof", "IfcStair"):
            assert cls in COMMON_PSET_MAP, f"{cls} missing from COMMON_PSET_MAP"

    def test_fallback_properties_match_pset_map(self):
        """Every Pset in COMMON_PSET_MAP should have a fallback property list."""
        for ifc_cls, pset_name in COMMON_PSET_MAP.items():
            assert pset_name in FALLBACK_PSET_PROPERTIES, (
                f"Fallback missing for {pset_name} (from {ifc_cls})"
            )

    def test_fallback_properties_not_empty(self):
        for pset_name, props in FALLBACK_PSET_PROPERTIES.items():
            assert len(props) > 0, f"{pset_name} has empty property list"

    def test_isexternal_in_wall_common(self):
        assert "IsExternal" in FALLBACK_PSET_PROPERTIES["Pset_WallCommon"]

    def test_firerating_in_door_common(self):
        assert "FireRating" in FALLBACK_PSET_PROPERTIES["Pset_DoorCommon"]


# ---------------------------------------------------------------------------
# get_standard_psets_sync — with bSDD mocked out (offline tests)
# ---------------------------------------------------------------------------

class TestGetStandardPsetsSync:
    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_falls_back_to_hardcoded(self, _mock):
        """When bSDD returns nothing, should fall back to FALLBACK_PSET_PROPERTIES."""
        psets = get_standard_psets_sync("IfcWall")
        assert "Pset_WallCommon" in psets
        assert "IsExternal" in psets["Pset_WallCommon"]

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[
        {"propertySet": "Pset_WallCommon", "name": "IsExternal"},
        {"propertySet": "Pset_WallCommon", "name": "FireRating"},
        {"propertySet": "Pset_WallCommon", "name": "CustomFromBsdd"},
    ])
    def test_uses_bsdd_when_available(self, _mock):
        """When bSDD returns data, should use it instead of fallback."""
        psets = get_standard_psets_sync("IfcWall")
        assert "Pset_WallCommon" in psets
        assert "CustomFromBsdd" in psets["Pset_WallCommon"]

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_unknown_class_returns_empty(self, _mock):
        """Unknown IFC class not in COMMON_PSET_MAP should return empty dict."""
        psets = get_standard_psets_sync("IfcSomethingWeird")
        assert psets == {}


# ---------------------------------------------------------------------------
# get_valid_pset_property_names
# ---------------------------------------------------------------------------

class TestGetValidPsetPropertyNames:
    @patch("building_blocks.bsdd.get_class_properties_sync", return_value={})
    def test_known_pset_uses_fallback(self, _mock):
        names = get_valid_pset_property_names("Pset_WallCommon")
        assert names is not None
        assert "IsExternal" in names
        assert "FireRating" in names

    @patch("building_blocks.bsdd.get_class_properties_sync", return_value={})
    def test_unknown_pset_returns_none(self, _mock):
        result = get_valid_pset_property_names("Custom_MyAppPset")
        assert result is None

    @patch("building_blocks.bsdd.get_class_properties_sync", return_value={
        "classProperties": [
            {"name": "Prop1"},
            {"name": "Prop2"},
        ]
    })
    def test_bsdd_data_preferred(self, _mock):
        names = get_valid_pset_property_names("Pset_SlabCommon")
        assert names == ["Prop1", "Prop2"]


# ---------------------------------------------------------------------------
# get_pset_summary_for_features (enrichment for clarify node)
# ---------------------------------------------------------------------------

class TestPsetSummaryForFeatures:
    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_includes_wall_pset_for_exterior_walls(self, _mock):
        summary = get_pset_summary_for_features(["exterior_walls"])
        assert "Pset_WallCommon" in summary
        assert "IsExternal" in summary

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_includes_multiple_psets(self, _mock):
        summary = get_pset_summary_for_features(["exterior_walls", "columns", "entrance_doors"])
        assert "Pset_WallCommon" in summary
        assert "Pset_ColumnCommon" in summary
        assert "Pset_DoorCommon" in summary

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_empty_for_no_matching_features(self, _mock):
        summary = get_pset_summary_for_features(["open_plan", "elevators"])
        assert summary == ""

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_deduplicates_psets(self, _mock):
        """exterior_walls and core_walls both map to IfcWall — Pset_WallCommon should appear once."""
        summary = get_pset_summary_for_features(["exterior_walls", "core_walls"])
        assert summary.count("Pset_WallCommon") == 1


# ---------------------------------------------------------------------------
# Clarify node integration
# ---------------------------------------------------------------------------

class TestClarifyBsddIntegration:
    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_clarify_includes_pset_section(self, _mock):
        from agent.nodes.clarify import clarify

        state = {"user_message": "build a house", "needs_clarification": True}
        result = clarify(state)
        desc = result["detailed_description"]
        assert "STANDARD PROPERTY SETS" in desc
        assert "Pset_WallCommon" in desc

    @patch("building_blocks.bsdd.get_pset_properties_for_element_sync", return_value=[])
    def test_clarify_highrise_includes_beam_pset(self, _mock):
        from agent.nodes.clarify import clarify

        state = {"user_message": "20-storey highrise tower", "needs_clarification": False}
        result = clarify(state)
        desc = result["detailed_description"]
        assert "Pset_BeamCommon" in desc
        assert "Pset_ColumnCommon" in desc


# ---------------------------------------------------------------------------
# Semantic check integration
# ---------------------------------------------------------------------------

class TestPsetPropertyNameCheck:
    def test_valid_properties_pass(self, ifc_setup):
        """Standard property names should not produce warnings."""
        from building_blocks.psets import apply_wall_common_pset
        from building_blocks.primitives.wall import create_wall
        from validation.semantic_checks import check_pset_property_names

        ifc, contexts, storey = ifc_setup
        wall = create_wall(
            ifc, contexts, storey,
            p1=[0, 0], p2=[5, 0],
            height=3.0, thickness=0.2,
        )
        apply_wall_common_pset(ifc, wall, is_external=True, fire_rating="1hr")

        issues = check_pset_property_names(ifc)
        pset_issues = [i for i in issues if i["check"] == "pset_property_name"]
        assert len(pset_issues) == 0

    def test_invalid_property_flagged(self, ifc_setup):
        """A non-standard property name in Pset_WallCommon should produce a warning."""
        import ifcopenshell.api.pset
        from building_blocks.primitives.wall import create_wall
        from validation.semantic_checks import check_pset_property_names

        ifc, contexts, storey = ifc_setup
        wall = create_wall(
            ifc, contexts, storey,
            p1=[0, 0], p2=[5, 0],
            height=3.0, thickness=0.2,
        )
        pset = ifcopenshell.api.pset.add_pset(ifc, product=wall, name="Pset_WallCommon")
        ifcopenshell.api.pset.edit_pset(
            ifc, pset=pset,
            properties={"IsExternal": True, "BogusPropertyXyz": "bad"},
        )

        issues = check_pset_property_names(ifc)
        pset_issues = [i for i in issues if i["check"] == "pset_property_name"]
        assert len(pset_issues) >= 1
        assert "BogusPropertyXyz" in pset_issues[0]["message"]
