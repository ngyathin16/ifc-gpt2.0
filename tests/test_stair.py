"""Tests for building_blocks.primitives.stair."""
from __future__ import annotations

from building_blocks.primitives.stair import create_stair


def test_create_stair(ifc_setup):
    ifc, contexts, storey = ifc_setup
    stair = create_stair(
        ifc, contexts, storey,
        start_point=(0.0, 0.0),
        direction=(1.0, 0.0),
        width=1.2,
        num_risers=18,
        riser_height=0.175,
        tread_depth=0.25,
        name="Main Stair",
    )
    assert stair is not None
    assert stair.is_a("IfcStairFlight")
    assert stair.Name == "Main Stair"

    stairs = ifc.by_type("IfcStairFlight")
    assert len(stairs) == 1
