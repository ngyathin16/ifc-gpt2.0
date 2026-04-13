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


def test_create_window_with_type_and_fire_rating(ifc_setup):
    """Cover the window_type assignment branch (line 109) and fire_rating."""
    from building_blocks.types.window_types import create_standard_window_type
    ifc, contexts, storey = ifc_setup
    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(8.0, 0.0),
        height=3.0, thickness=0.2,
    )
    wt = create_standard_window_type(ifc, name="WIN-1200x1500")
    window = create_window(
        ifc, contexts, storey, wall,
        distance_along_wall=4.0,
        sill_height=0.9,
        width=1.2, height=1.5,
        window_type=wt,
        fire_rating="30min",
        name="Typed Window",
    )
    assert window is not None
    assert window.is_a("IfcWindow")
