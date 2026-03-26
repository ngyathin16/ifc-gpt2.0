"""
Two-point wall author. Supports:
  - Exterior walls (IfcWall + exterior type)
  - Interior partitions (IfcWall + interior type)
  - Material layer sets
  - Wall-to-wall connectivity via connect_wall
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
from building_blocks.psets import apply_wall_common_pset


def create_wall(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float],
    p2: tuple[float, float],
    elevation: float = 0.0,
    height: float = 3.0,
    thickness: float = 0.2,
    name: str = "Wall",
    wall_type=None,
    fire_rating: str | None = None,
    is_external: bool = True,
) -> object:
    """
    Create an IfcWall between two 2D points at a given storey.

    Args:
        p1, p2: (x, y) in metres. The wall runs from p1 to p2.
        elevation: Z elevation of the wall base in metres.
        height: Wall height in metres.
        thickness: Wall thickness in metres.
        wall_type: Optional IfcWallType to assign.
        fire_rating: Optional "1HR", "2HR" etc for Pset_WallCommon.
        is_external: Stored in Pset_WallCommon.IsExternal.

    Returns:
        The newly created IfcWall entity.
    """
    wall = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWall", name=name)

    # Geometry — create_2pt_wall returns an IfcShapeRepresentation but does NOT
    # assign it to the wall.  We must call assign_representation ourselves.
    body_rep = ifcopenshell.api.geometry.create_2pt_wall(
        ifc,
        element=wall,
        context=contexts["body"],
        p1=p1,
        p2=p2,
        elevation=elevation,
        height=height,
        thickness=thickness,
        is_si=True,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=wall, representation=body_rep)

    # Spatial containment
    ifcopenshell.api.spatial.assign_container(ifc, products=[wall], relating_structure=storey)

    # Type assignment
    if wall_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[wall], relating_type=wall_type)

    # Standard Pset
    apply_wall_common_pset(
        ifc, wall,
        is_external=is_external,
        fire_rating=fire_rating,
    )

    return wall
