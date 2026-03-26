"""
Roof assembly: creates a complete roof system with the roof element,
optional parapet walls around the perimeter, and an optional roof slab.
"""
from __future__ import annotations

import ifcopenshell

from building_blocks.primitives.roof import create_flat_roof, create_pitched_roof
from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.railing import create_railing


def create_roof_assembly(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    boundary_points: list[tuple[float, float]],
    elevation: float = 3.0,
    roof_type: str = "FLAT",
    ridge_height: float = 1.5,
    thickness: float = 0.25,
    include_parapet: bool = False,
    parapet_height: float = 1.0,
    parapet_thickness: float = 0.15,
    include_railing: bool = False,
    railing_height: float = 1.1,
    name_prefix: str = "Roof",
) -> dict:
    """
    Create a complete roof assembly with optional parapets or railings.

    For flat roofs, optionally adds parapet walls or railings around the
    perimeter. For pitched roofs, creates gable or hip geometry.

    Args:
        boundary_points: List of (x, y) tuples defining the roof outline.
        elevation: Z elevation of the roof base.
        roof_type: "FLAT", "GABLE", or "HIP".
        ridge_height: Height of ridge above eave (pitched roofs only).
        thickness: Roof slab thickness.
        include_parapet: Add parapet walls around flat roof perimeter.
        parapet_height: Height of parapet walls.
        parapet_thickness: Thickness of parapet walls.
        include_railing: Add safety railings around perimeter.
        railing_height: Height of railings.

    Returns:
        {"roof": ..., "parapets": [...], "railings": [...]}
    """
    # Create the roof element
    if roof_type == "FLAT":
        roof = create_flat_roof(
            ifc, contexts, storey,
            boundary_points=boundary_points,
            thickness=thickness,
            elevation=elevation,
            name=f"{name_prefix}_Flat",
        )
    else:
        pitched_type = "GABLE_ROOF" if roof_type == "GABLE" else "HIP_ROOF"
        roof = create_pitched_roof(
            ifc, contexts, storey,
            boundary_points=boundary_points,
            ridge_height=ridge_height,
            elevation=elevation,
            name=f"{name_prefix}_Pitched",
            roof_type=pitched_type,
        )

    parapets = []
    railings = []
    n = len(boundary_points)

    if roof_type == "FLAT" and include_parapet:
        for i in range(n):
            p1 = boundary_points[i]
            p2 = boundary_points[(i + 1) % n]
            parapet = create_wall(
                ifc, contexts, storey,
                p1=p1, p2=p2,
                elevation=elevation + thickness,
                height=parapet_height,
                thickness=parapet_thickness,
                name=f"{name_prefix}_Parapet_{i}",
                is_external=True,
            )
            parapets.append(parapet)

    if roof_type == "FLAT" and include_railing and not include_parapet:
        rail_z = elevation + thickness
        path_3d = [
            (pt[0], pt[1], rail_z) for pt in boundary_points
        ]
        # Close the loop
        path_3d.append(path_3d[0])
        rail = create_railing(
            ifc, contexts, storey,
            path_points=path_3d,
            height=railing_height,
            name=f"{name_prefix}_Railing",
            predefined_type="GUARDRAIL",
        )
        railings.append(rail)

    return {
        "roof": roof,
        "parapets": parapets,
        "railings": railings,
    }
