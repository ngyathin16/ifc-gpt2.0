"""Tests for building_blocks.primitives.elevator."""
from __future__ import annotations

from building_blocks.primitives.elevator import create_elevator_shaft


def test_create_elevator_shaft(ifc_setup):
    ifc, contexts, storey = ifc_setup
    elev = create_elevator_shaft(
        ifc, contexts, storey,
        position=(10.0, 5.0),
        elevation=0.0,
        width=2.0,
        depth=2.0,
        height=3.5,
        name="Elevator-A",
    )
    assert elev is not None
    assert elev.is_a("IfcTransportElement")
    assert elev.Name == "Elevator-A"

    elevators = ifc.by_type("IfcTransportElement")
    assert len(elevators) == 1


def test_create_elevator_with_fire_rating(ifc_setup):
    """Cover the fire_rating branch (line 89)."""
    ifc, contexts, storey = ifc_setup
    elev = create_elevator_shaft(
        ifc, contexts, storey,
        position=(5.0, 5.0),
        fire_rating="2HR",
        name="Elevator-FR",
    )
    assert elev is not None
    assert elev.is_a("IfcTransportElement")
