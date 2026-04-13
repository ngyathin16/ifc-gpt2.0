"""Tests for building_blocks.primitives.column."""
from __future__ import annotations

from building_blocks.primitives.column import create_column


def test_create_rectangular_column(ifc_setup):
    ifc, contexts, storey = ifc_setup
    col = create_column(
        ifc, contexts, storey,
        position=(2.0, 3.0),
        height=3.0,
        profile_type="RECTANGULAR",
        width=0.3, depth=0.3,
        name="Col-A1",
    )
    assert col is not None
    assert col.is_a("IfcColumn")
    assert col.Name == "Col-A1"

    columns = ifc.by_type("IfcColumn")
    assert len(columns) == 1


def test_create_circular_column(ifc_setup):
    ifc, contexts, storey = ifc_setup
    col = create_column(
        ifc, contexts, storey,
        position=(0.0, 0.0),
        height=3.0,
        profile_type="CIRCULAR",
        radius=0.15,
        name="Col-Circ",
    )
    assert col is not None
    assert col.is_a("IfcColumn")


def test_create_i_section_column(ifc_setup):
    """Cover the I_SECTION profile branch (lines 58-69)."""
    ifc, contexts, storey = ifc_setup
    col = create_column(
        ifc, contexts, storey,
        position=(0.0, 0.0),
        height=3.0,
        profile_type="I_SECTION",
        width=0.3, depth=0.3,
        name="Col-I",
    )
    assert col is not None
    assert col.is_a("IfcColumn")


def test_create_column_with_type(ifc_setup):
    """Cover the column_type assignment branch (line 90)."""
    from building_blocks.types.column_types import create_concrete_column_type
    ifc, contexts, storey = ifc_setup
    col_type = create_concrete_column_type(ifc, name="COL-300x300")
    col = create_column(
        ifc, contexts, storey,
        position=(0.0, 0.0),
        height=3.0,
        column_type=col_type,
        name="Col-Typed",
    )
    assert col is not None
    assert col.is_a("IfcColumn")


def test_create_column_invalid_profile(ifc_setup):
    """Cover the ValueError branch for unknown profile_type."""
    import pytest
    ifc, contexts, storey = ifc_setup
    with pytest.raises(ValueError, match="Unknown profile_type"):
        create_column(
            ifc, contexts, storey,
            position=(0.0, 0.0),
            profile_type="TRIANGULAR",
        )
