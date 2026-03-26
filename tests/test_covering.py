"""Tests for building_blocks.primitives.covering."""
from __future__ import annotations

from building_blocks.primitives.covering import create_covering


def test_create_covering(ifc_setup):
    ifc, contexts, storey = ifc_setup
    covering = create_covering(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (5.0, 0.0), (5.0, 4.0), (0.0, 4.0)],
        thickness=0.02,
        elevation=2.8,
        name="Ceiling-1",
        predefined_type="CEILING",
    )
    assert covering is not None
    assert covering.is_a("IfcCovering")
    assert covering.Name == "Ceiling-1"

    coverings = ifc.by_type("IfcCovering")
    assert len(coverings) == 1
