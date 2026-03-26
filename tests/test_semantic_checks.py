"""Tests for validation/semantic_checks.py — post-build IFC validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from building_blocks.context import add_storey, create_ifc_project
from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.slab import create_slab
from validation.semantic_checks import (
    check_disconnected_storeys,
    check_element_geometry,
    check_floating_openings,
    check_spatial_containment,
    check_wall_count,
    run_all_checks,
)


@pytest.fixture
def good_ifc(tmp_path):
    """Create a minimal valid IFC file with 4 walls and a slab."""
    ifc, contexts = create_ifc_project(
        project_name="Test", site_name="Site", building_name="Bldg",
    )
    storey = add_storey(ifc, contexts["building"], name="GF", elevation=0.0)

    create_wall(ifc, contexts, storey, p1=(0, 0), p2=(4, 0), height=3.0, thickness=0.2, name="W1")
    create_wall(ifc, contexts, storey, p1=(4, 0), p2=(4, 3), height=3.0, thickness=0.2, name="W2")
    create_wall(ifc, contexts, storey, p1=(4, 3), p2=(0, 3), height=3.0, thickness=0.2, name="W3")
    create_wall(ifc, contexts, storey, p1=(0, 3), p2=(0, 0), height=3.0, thickness=0.2, name="W4")
    create_slab(ifc, contexts, storey, boundary_points=[(0, 0), (4, 0), (4, 3), (0, 3)], depth=0.2)

    out = tmp_path / "good.ifc"
    ifc.write(str(out))
    return str(out)


@pytest.fixture
def single_wall_ifc(tmp_path):
    """IFC with only 1 wall — should fail wall_count check."""
    ifc, contexts = create_ifc_project(
        project_name="Test", site_name="Site", building_name="Bldg",
    )
    storey = add_storey(ifc, contexts["building"], name="GF", elevation=0.0)
    create_wall(ifc, contexts, storey, p1=(0, 0), p2=(4, 0), height=3.0, thickness=0.2, name="W1")

    out = tmp_path / "single_wall.ifc"
    ifc.write(str(out))
    return str(out)


class TestRunAllChecks:
    def test_good_ifc_passes(self, good_ifc):
        result = run_all_checks(good_ifc)
        assert result["valid"] is True
        assert result["error_count"] == 0

    def test_single_wall_fails_wall_count(self, single_wall_ifc):
        result = run_all_checks(single_wall_ifc)
        wall_errors = [
            i for i in result["issues"]
            if i.get("check") == "wall_count" and i["severity"] == "error"
        ]
        assert len(wall_errors) >= 1


class TestSpatialContainment:
    def test_contained_elements_pass(self, good_ifc):
        import ifcopenshell
        ifc_file = ifcopenshell.open(good_ifc)
        issues = check_spatial_containment(ifc_file)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0


class TestElementGeometry:
    def test_elements_have_geometry(self, good_ifc):
        import ifcopenshell
        ifc_file = ifcopenshell.open(good_ifc)
        issues = check_element_geometry(ifc_file)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0


class TestDisconnectedStoreys:
    def test_storeys_aggregated(self, good_ifc):
        import ifcopenshell
        ifc_file = ifcopenshell.open(good_ifc)
        issues = check_disconnected_storeys(ifc_file)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0
