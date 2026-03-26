"""Tests for building_blocks.context."""
from __future__ import annotations

from building_blocks.context import add_storey, create_ifc_project


def test_create_ifc_project():
    ifc, ctx = create_ifc_project()
    assert ifc.schema == "IFC4"
    assert ctx["project"] is not None
    assert ctx["site"] is not None
    assert ctx["building"] is not None
    assert ctx["body"] is not None
    assert ctx["axis"] is not None

    # Verify spatial hierarchy
    projects = ifc.by_type("IfcProject")
    assert len(projects) == 1
    sites = ifc.by_type("IfcSite")
    assert len(sites) == 1
    buildings = ifc.by_type("IfcBuilding")
    assert len(buildings) == 1


def test_add_storey():
    ifc, ctx = create_ifc_project()
    storey = add_storey(ifc, ctx["building"], name="Level 1", elevation=3.0)
    assert storey is not None

    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 1
    assert storeys[0].Name == "Level 1"
