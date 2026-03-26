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
