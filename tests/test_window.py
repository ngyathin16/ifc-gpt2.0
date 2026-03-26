"""Tests for building_blocks.primitives.window."""
from __future__ import annotations

from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.window import create_window


def test_create_window(ifc_setup):
    ifc, contexts, storey = ifc_setup

    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(8.0, 0.0),
        height=3.0, thickness=0.2,
    )

    window = create_window(
        ifc, contexts, storey, wall,
        distance_along_wall=4.0,
        sill_height=0.9,
        width=1.2, height=1.5,
        name="Test Window",
    )
    assert window is not None
    assert window.is_a("IfcWindow")
    assert window.Name == "Test Window"

    windows = ifc.by_type("IfcWindow")
    assert len(windows) == 1

    openings = ifc.by_type("IfcOpeningElement")
    assert len(openings) == 1
