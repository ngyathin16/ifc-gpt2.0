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
    """Gable roof with length >= width (ridge along Y)."""
    ifc, contexts, storey = ifc_setup
    # width=8, length=10 → length >= width → ridge along Y axis (lines 107-115)
    roof = create_pitched_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (8.0, 0.0), (8.0, 10.0), (0.0, 10.0)],
        ridge_height=2.0,
        elevation=3.0,
        roof_type="GABLE_ROOF",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")


def test_create_gable_roof_width_gt_length(ifc_setup):
    """Cover gable branch where width > length (lines 107-115 / 121-136)."""
    ifc, contexts, storey = ifc_setup
    # width (12) > length (6)  → ridge along X axis
    roof = create_pitched_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (12.0, 0.0), (12.0, 6.0), (0.0, 6.0)],
        ridge_height=2.0,
        elevation=3.0,
        roof_type="GABLE_ROOF",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")


def test_create_hip_roof(ifc_setup):
    """Cover the HIP_ROOF branch with length >= width."""
    ifc, contexts, storey = ifc_setup
    roof = create_pitched_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (8.0, 0.0), (8.0, 12.0), (0.0, 12.0)],
        ridge_height=2.0,
        elevation=3.0,
        roof_type="HIP_ROOF",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")


def test_create_hip_roof_width_gt_length(ifc_setup):
    """Cover HIP_ROOF branch where width > length (lines 149-157)."""
    ifc, contexts, storey = ifc_setup
    roof = create_pitched_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (12.0, 0.0), (12.0, 6.0), (0.0, 6.0)],
        ridge_height=2.0,
        elevation=3.0,
        roof_type="HIP_ROOF",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")


def test_create_pitched_roof_unsupported_type(ifc_setup):
    """Cover the ValueError branch for unsupported roof_type (line 165)."""
    import pytest
    ifc, contexts, storey = ifc_setup
    with pytest.raises(ValueError, match="Unsupported roof_type"):
        create_pitched_roof(
            ifc, contexts, storey,
            boundary_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
            roof_type="MANSARD_ROOF",
        )


def test_create_flat_roof_with_fire_rating(ifc_setup):
    """Cover fire_rating optional param path."""
    ifc, contexts, storey = ifc_setup
    roof = create_flat_roof(
        ifc, contexts, storey,
        boundary_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)],
        fire_rating="1HR",
    )
    assert roof is not None
    assert roof.is_a("IfcRoof")
