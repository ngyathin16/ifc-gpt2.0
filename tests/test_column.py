"""Tests for building_blocks.primitives.column."""
from __future__ import annotations

from building_blocks.primitives.column import create_column


def test_create_rectangular_column(ifc_setup):
    ifc, contexts, storey = ifc_setup
    col = create_column(
        ifc, contexts, storey,
        position=(2.0, 3.0),
        height=3.0,
        profile_type="RECTANGULAR",
        width=0.3, depth=0.3,
        name="Col-A1",
    )
    assert col is not None
    assert col.is_a("IfcColumn")
    assert col.Name == "Col-A1"

    columns = ifc.by_type("IfcColumn")
    assert len(columns) == 1


def test_create_circular_column(ifc_setup):
    ifc, contexts, storey = ifc_setup
    col = create_column(
        ifc, contexts, storey,
        position=(0.0, 0.0),
        height=3.0,
        profile_type="CIRCULAR",
        radius=0.15,
        name="Col-Circ",
    )
    assert col is not None
    assert col.is_a("IfcColumn")
