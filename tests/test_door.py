"""Tests for building_blocks.primitives.door."""
from __future__ import annotations

from building_blocks.primitives.door import create_door
from building_blocks.primitives.wall import create_wall


def test_create_door(ifc_setup):
    ifc, contexts, storey = ifc_setup

    # First create a host wall
    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(6.0, 0.0),
        height=3.0, thickness=0.2,
    )

    door = create_door(
        ifc, contexts, storey, wall,
        distance_along_wall=3.0,
        sill_height=0.0,
        width=0.9, height=2.1,
        name="Test Door",
    )
    assert door is not None
    assert door.is_a("IfcDoor")
    assert door.Name == "Test Door"

    doors = ifc.by_type("IfcDoor")
    assert len(doors) == 1

    # Verify opening was created
    openings = ifc.by_type("IfcOpeningElement")
    assert len(openings) == 1
