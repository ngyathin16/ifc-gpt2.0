"""Tests for building_blocks.primitives.footing."""
from __future__ import annotations

from building_blocks.primitives.footing import create_footing


def test_create_footing(ifc_setup):
    ifc, contexts, storey = ifc_setup
    footing = create_footing(
        ifc, contexts, storey,
        position=(2.0, 3.0),
        width=1.0, length=1.0, depth=0.5,
        elevation=-0.5,
        name="Pad Footing A1",
    )
    assert footing is not None
    assert footing.is_a("IfcFooting")
    assert footing.Name == "Pad Footing A1"

    footings = ifc.by_type("IfcFooting")
    assert len(footings) == 1
