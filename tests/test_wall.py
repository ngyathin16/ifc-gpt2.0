"""Tests for building_blocks.primitives.wall."""
from __future__ import annotations

from building_blocks.primitives.wall import create_wall


def test_create_wall(ifc_setup):
    ifc, contexts, storey = ifc_setup
    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(5.0, 0.0),
        height=3.0, thickness=0.2,
        name="Test Wall",
        is_external=True,
    )
    assert wall is not None
    assert wall.is_a("IfcWall")
    assert wall.Name == "Test Wall"

    # Verify spatial containment
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1

    # Verify pset
    psets = [
        r.RelatingPropertyDefinition
        for r in ifc.by_type("IfcRelDefinesByProperties")
        if wall in r.RelatedObjects
    ]
    pset_names = [p.Name for p in psets if hasattr(p, "Name")]
    assert "Pset_WallCommon" in pset_names


def test_create_wall_with_type(ifc_setup):
    """Cover the wall_type assignment branch (line 70)."""
    from building_blocks.types.wall_types import create_exterior_wall_type
    ifc, contexts, storey = ifc_setup
    wt = create_exterior_wall_type(ifc, name="EXT-200")
    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(5.0, 0.0),
        wall_type=wt,
        fire_rating="2HR",
        name="Typed Wall",
    )
    assert wall is not None
    assert wall.is_a("IfcWall")
