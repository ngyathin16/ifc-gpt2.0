"""Tests for building_blocks.primitives.member."""
from __future__ import annotations

from building_blocks.primitives.member import create_member


def test_create_member(ifc_setup):
    ifc, contexts, storey = ifc_setup
    member = create_member(
        ifc, contexts, storey,
        p1=(0.0, 0.0, 0.0),
        p2=(3.0, 0.0, 3.0),
        profile_type="RECTANGULAR",
        width=0.1, depth=0.1,
        name="Brace-1",
    )
    assert member is not None
    assert member.is_a("IfcMember")
    assert member.Name == "Brace-1"

    members = ifc.by_type("IfcMember")
    assert len(members) == 1


def test_create_member_circular(ifc_setup):
    """Cover the CIRCULAR profile branch (lines 63-69)."""
    ifc, contexts, storey = ifc_setup
    member = create_member(
        ifc, contexts, storey,
        p1=(0.0, 0.0, 0.0),
        p2=(0.0, 5.0, 0.0),
        profile_type="CIRCULAR",
        radius=0.08,
        name="Circ-Brace",
    )
    assert member is not None
    assert member.is_a("IfcMember")


def test_create_member_zero_length(ifc_setup):
    """Cover the zero-length fallback branch (line 85)."""
    ifc, contexts, storey = ifc_setup
    member = create_member(
        ifc, contexts, storey,
        p1=(1.0, 1.0, 1.0),
        p2=(1.0, 1.0, 1.0),
        profile_type="RECTANGULAR",
        name="Zero-Length",
    )
    assert member is not None
    assert member.is_a("IfcMember")


def test_create_member_anti_parallel(ifc_setup):
    """Cover the anti-parallel (dot < 0) branch (lines 93-96)."""
    ifc, contexts, storey = ifc_setup
    member = create_member(
        ifc, contexts, storey,
        p1=(0.0, 0.0, 5.0),
        p2=(0.0, 0.0, 0.0),
        profile_type="RECTANGULAR",
        name="Down-Brace",
    )
    assert member is not None
    assert member.is_a("IfcMember")


def test_create_member_invalid_profile(ifc_setup):
    """Cover the ValueError branch for unknown profile_type (line 71)."""
    import pytest
    ifc, contexts, storey = ifc_setup
    with pytest.raises(ValueError, match="Unknown profile_type"):
        create_member(
            ifc, contexts, storey,
            p1=(0.0, 0.0, 0.0),
            p2=(1.0, 0.0, 0.0),
            profile_type="HEXAGONAL",
        )
