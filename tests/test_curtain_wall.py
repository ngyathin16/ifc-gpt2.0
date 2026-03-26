"""Tests for building_blocks.primitives.curtain_wall."""
from __future__ import annotations

from building_blocks.primitives.curtain_wall import create_curtain_wall


def test_create_curtain_wall(ifc_setup):
    ifc, contexts, storey = ifc_setup
    cw = create_curtain_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(8.0, 0.0),
        elevation=0.0, height=3.0, thickness=0.15,
        name="CW-South",
    )
    assert cw is not None
    assert cw.is_a("IfcCurtainWall")
    assert cw.Name == "CW-South"

    cws = ifc.by_type("IfcCurtainWall")
    assert len(cws) == 1
