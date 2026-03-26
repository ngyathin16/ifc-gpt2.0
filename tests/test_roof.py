"""Tests for building_blocks.primitives.roof."""
from __future__ import annotations

from building_blocks.primitives.roof import create_flat_roof, create_pitched_roof


def test_create_flat_roof(ifc_setup):
    ifc, contexts, storey = ifc_setup
    roof = create_flat_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        thickness=0.25,
        elevation=3.0,
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")

    roofs = ifc.by_type("IfcRoof")
    assert len(roofs) == 1


def test_create_gable_roof(ifc_setup):
    ifc, contexts, storey = ifc_setup
    roof = create_pitched_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        ridge_height=2.0,
        elevation=3.0,
        roof_type="GABLE_ROOF",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")
