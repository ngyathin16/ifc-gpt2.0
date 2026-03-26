"""Tests for building_blocks.primitives.slab."""
from __future__ import annotations

from building_blocks.primitives.slab import create_slab


def test_create_slab(ifc_setup):
    ifc, contexts, storey = ifc_setup
    slab = create_slab(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        depth=0.2,
        elevation=0.0,
        name="Floor Slab",
    )
    assert slab is not None
    assert slab.is_a("IfcSlab")
    assert slab.Name == "Floor Slab"

    slabs = ifc.by_type("IfcSlab")
    assert len(slabs) == 1
