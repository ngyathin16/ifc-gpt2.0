"""Tests for building_blocks.primitives.ramp."""
from __future__ import annotations

from building_blocks.primitives.ramp import create_ramp


def test_create_ramp(ifc_setup):
    ifc, contexts, storey = ifc_setup
    ramp = create_ramp(
        ifc, contexts, storey,
        start_point=(0.0, 0.0),
        direction=(1.0, 0.0),
        width=1.5, length=6.0, rise=0.5,
        name="Ramp-1",
    )
    assert ramp is not None
    assert ramp.is_a("IfcRamp")
    assert ramp.Name == "Ramp-1"

    ramps = ifc.by_type("IfcRamp")
    assert len(ramps) == 1
