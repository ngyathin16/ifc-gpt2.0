"""
Roof authors: flat roofs (IfcSlab-based) and pitched roofs (mesh-based).
"""
from __future__ import annotations

import numpy as np

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
from building_blocks.psets import apply_roof_common_pset


def create_flat_roof(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    boundary_points: list[tuple[float, float]],
    thickness: float = 0.25,
    elevation: float = 3.0,
    name: str = "Flat Roof",
    fire_rating: str | None = None,
) -> object:
    """
    Create a flat IfcRoof using slab representation for the body.

    Args:
        boundary_points: List of (x, y) tuples defining the roof outline.
        thickness: Roof thickness in metres.
        elevation: Z elevation of the roof bottom.

    Returns:
        The newly created IfcRoof entity.
    """
    roof = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcRoof", name=name, predefined_type="FLAT_ROOF",
    )

    # Use slab representation for flat roof geometry
    body_rep = ifcopenshell.api.geometry.add_slab_representation(
        ifc,
        context=contexts["body"],
        depth=thickness,
        polyline=boundary_points,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=roof, representation=body_rep)

    # Placement
    matrix = np.eye(4)
    matrix[2][3] = elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=roof, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[roof], relating_structure=storey)

    apply_roof_common_pset(ifc, roof, fire_rating=fire_rating)

    return roof


def create_pitched_roof(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    boundary_points: list[tuple[float, float]],
    ridge_height: float = 1.5,
    elevation: float = 3.0,
    name: str = "Pitched Roof",
    roof_type: str = "GABLE_ROOF",
    fire_rating: str | None = None,
) -> object:
    """
    Create a pitched IfcRoof using mesh representation for ridge geometry.

    For a GABLE roof, the ridge runs along the longer axis of the bounding box.
    For a HIP roof, all edges slope inward to a ridge.

    Args:
        boundary_points: List of (x, y) tuples defining the roof footprint.
        ridge_height: Height of the ridge above the eave level.
        elevation: Z elevation of the eave line.
        roof_type: "GABLE_ROOF" or "HIP_ROOF".

    Returns:
        The newly created IfcRoof entity.
    """
    roof = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcRoof", name=name, predefined_type=roof_type,
    )

    # Calculate bounding box for ridge placement
    xs = [p[0] for p in boundary_points]
    ys = [p[1] for p in boundary_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0
    width = max_x - min_x
    length = max_y - min_y

    # Build mesh vertices and faces depending on roof type
    if roof_type == "GABLE_ROOF":
        # Ridge runs along the longer axis
        if length >= width:
            # Ridge along Y axis
            vertices = [
                (min_x, min_y, 0.0),  # 0: bottom-left eave
                (max_x, min_y, 0.0),  # 1: bottom-right eave
                (max_x, max_y, 0.0),  # 2: top-right eave
                (min_x, max_y, 0.0),  # 3: top-left eave
                (mid_x, min_y, ridge_height),  # 4: ridge front
                (mid_x, max_y, ridge_height),  # 5: ridge back
            ]
            faces = [
                (0, 1, 4),      # front gable
                (2, 3, 5),      # back gable
                (0, 4, 5, 3),   # left slope
                (1, 2, 5, 4),   # right slope
            ]
        else:
            # Ridge along X axis
            vertices = [
                (min_x, min_y, 0.0),
                (max_x, min_y, 0.0),
                (max_x, max_y, 0.0),
                (min_x, max_y, 0.0),
                (min_x, mid_y, ridge_height),
                (max_x, mid_y, ridge_height),
            ]
            faces = [
                (0, 3, 4),      # left gable
                (1, 5, 2),      # right gable
                (0, 1, 5, 4),   # front slope
                (3, 2, 5, 4),   # back slope - note: reordered for CCW
            ]
    elif roof_type == "HIP_ROOF":
        # All four edges slope to a central ridge
        ridge_len = max(length, width) * 0.3
        if length >= width:
            vertices = [
                (min_x, min_y, 0.0),
                (max_x, min_y, 0.0),
                (max_x, max_y, 0.0),
                (min_x, max_y, 0.0),
                (mid_x, min_y + (length - ridge_len) / 2.0, ridge_height),
                (mid_x, max_y - (length - ridge_len) / 2.0, ridge_height),
            ]
        else:
            vertices = [
                (min_x, min_y, 0.0),
                (max_x, min_y, 0.0),
                (max_x, max_y, 0.0),
                (min_x, max_y, 0.0),
                (min_x + (width - ridge_len) / 2.0, mid_y, ridge_height),
                (max_x - (width - ridge_len) / 2.0, mid_y, ridge_height),
            ]
        faces = [
            (0, 1, 4),      # front hip
            (1, 2, 5, 4),   # right slope
            (2, 3, 5),      # back hip
            (3, 0, 4, 5),   # left slope
        ]
    else:
        raise ValueError(f"Unsupported roof_type for pitched roof: {roof_type}")

    # Create mesh representation
    body_rep = ifcopenshell.api.geometry.add_mesh_representation(
        ifc,
        context=contexts["body"],
        vertices=[[list(v) for v in vertices]],
        faces=[[list(f) for f in faces]],
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=roof, representation=body_rep)

    # Placement
    matrix = np.eye(4)
    matrix[2][3] = elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=roof, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[roof], relating_structure=storey)

    apply_roof_common_pset(ifc, roof, fire_rating=fire_rating)

    return roof
