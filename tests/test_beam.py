"""Tests for building_blocks.primitives.beam."""
from __future__ import annotations

from building_blocks.primitives.beam import create_beam


def test_create_beam(ifc_setup):
    ifc, contexts, storey = ifc_setup
    beam = create_beam(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(6.0, 0.0),
        elevation=3.0,
        profile_type="RECTANGULAR",
        width=0.2, depth=0.4,
        name="Beam-A",
    )
    assert beam is not None
    assert beam.is_a("IfcBeam")
    assert beam.Name == "Beam-A"

    beams = ifc.by_type("IfcBeam")
    assert len(beams) == 1
