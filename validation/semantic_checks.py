"""
Semantic geometry validation checks for generated IFC files.

Custom spatial and geometry rules that go beyond schema validation,
checking for common modelling errors in LLM-generated IFC files.
"""
from __future__ import annotations

from typing import Any

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement


def check_spatial_containment(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Check all building elements are contained in spatial structure."""
    issues: list[dict[str, Any]] = []
    building_elements = ifc_file.by_type("IfcBuildingElement")

    for elem in building_elements:
        container = ifcopenshell.util.element.get_container(elem)
        if not container:
            issues.append({
                "severity": "error",
                "check": "spatial_containment",
                "element": elem.GlobalId,
                "element_type": elem.is_a(),
                "message": (
                    f"{elem.Name or elem.GlobalId} ({elem.is_a()}) "
                    "has no spatial container"
                ),
            })
    return issues


def check_floating_openings(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Check doors/windows are hosted in walls via IfcRelFillsElement.

    A floating opening renders incorrectly: the wall geometry is not cut
    and the door/window mesh floats in mid-air.
    """
    issues: list[dict[str, Any]] = []
    for entity_type in ("IfcDoor", "IfcWindow"):
        for elem in ifc_file.by_type(entity_type):
            fills = getattr(elem, "FillsVoids", [])
            if not fills:
                issues.append({
                    "severity": "error",
                    "check": "floating_opening",
                    "element": elem.GlobalId,
                    "element_type": entity_type,
                    "message": (
                        f"{elem.Name or elem.GlobalId} has no IfcRelFillsElement — "
                        "it is not hosted in any wall opening"
                    ),
                })
    return issues


def check_element_geometry(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Check that all IfcBuildingElement instances have at least one representation.

    Elements without geometry will be invisible in all viewers.
    """
    issues: list[dict[str, Any]] = []
    for elem in ifc_file.by_type("IfcBuildingElement"):
        if not elem.Representation or not elem.Representation.Representations:
            issues.append({
                "severity": "error",
                "check": "missing_geometry",
                "element": elem.GlobalId,
                "element_type": elem.is_a(),
                "message": (
                    f"{elem.Name or elem.GlobalId} ({elem.is_a()}) "
                    "has no geometric representation"
                ),
            })
    return issues


def check_disconnected_storeys(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Check building storeys are aggregated under a building."""
    issues: list[dict[str, Any]] = []
    for storey in ifc_file.by_type("IfcBuildingStorey"):
        decomposes = getattr(storey, "Decomposes", [])
        if not decomposes:
            issues.append({
                "severity": "error",
                "check": "disconnected_storey",
                "element": storey.GlobalId,
                "element_type": "IfcBuildingStorey",
                "message": (
                    f"Storey '{storey.Name or storey.GlobalId}' is not aggregated "
                    "under any IfcBuilding"
                ),
            })
    return issues


def check_wall_count(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Warn if fewer than 3 walls exist (cannot form a room)."""
    issues: list[dict[str, Any]] = []
    walls = ifc_file.by_type("IfcWall")
    if 0 < len(walls) < 3:
        issues.append({
            "severity": "error",
            "check": "wall_count",
            "element_type": "IfcWall",
            "message": (
                f"Only {len(walls)} wall(s) in the model — at least 3 are needed "
                "to form a closed room."
            ),
        })
    return issues


def check_roof_exists(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Warn if walls exist but no roof is present."""
    issues: list[dict[str, Any]] = []
    walls = ifc_file.by_type("IfcWall")
    roofs = ifc_file.by_type("IfcRoof")
    if walls and not roofs:
        issues.append({
            "severity": "warning",
            "check": "roof_missing",
            "element_type": "IfcRoof",
            "message": "Walls exist but no roof element was created.",
        })
    return issues


def check_slab_exists(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Warn if walls exist but no floor slab is present."""
    issues: list[dict[str, Any]] = []
    walls = ifc_file.by_type("IfcWall")
    slabs = ifc_file.by_type("IfcSlab")
    if walls and not slabs:
        issues.append({
            "severity": "warning",
            "check": "slab_missing",
            "element_type": "IfcSlab",
            "message": "Walls exist but no floor slab was created.",
        })
    return issues


def check_bounding_box_sanity(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Detect elements whose placement is far outside the building footprint.

    Computes the convex bounding box from all IfcWall placements, then flags
    any IfcBuildingElement whose origin is more than 10 m beyond that box.
    This catches orphaned doors/windows placed in world-space rather than
    relative to their host wall.
    """
    issues: list[dict[str, Any]] = []
    TOLERANCE = 10.0  # metres beyond envelope

    # Collect wall placement origins to estimate building footprint
    wall_xs: list[float] = []
    wall_ys: list[float] = []
    for wall in ifc_file.by_type("IfcWall"):
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                wall.ObjectPlacement
            )
            wall_xs.append(float(mat[0][3]))
            wall_ys.append(float(mat[1][3]))
        except Exception:
            continue

    if len(wall_xs) < 2:
        return issues

    min_x, max_x = min(wall_xs) - TOLERANCE, max(wall_xs) + TOLERANCE
    min_y, max_y = min(wall_ys) - TOLERANCE, max(wall_ys) + TOLERANCE

    for elem in ifc_file.by_type("IfcBuildingElement"):
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                elem.ObjectPlacement
            )
            ex, ey = float(mat[0][3]), float(mat[1][3])
        except Exception:
            continue

        if ex < min_x or ex > max_x or ey < min_y or ey > max_y:
            issues.append({
                "severity": "error",
                "check": "bounding_box_sanity",
                "element": elem.GlobalId,
                "element_type": elem.is_a(),
                "message": (
                    f"{elem.Name or elem.GlobalId} ({elem.is_a()}) at "
                    f"({ex:.1f}, {ey:.1f}) is outside the building footprint "
                    f"envelope. Likely a misplaced opening/door/window."
                ),
            })

    return issues


def check_double_elevation(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Detect elements whose Z placement equals ~2× their storey elevation.

    This is the post-build counterpart of the plan-level elevation
    double-counting check.  If an element on a storey at Z=35 has its own
    placement at Z≈70, it was likely double-counted.

    Elements within [storey_z, storey_z + floor_to_floor] are valid — e.g.
    beams at the top of walls.  Only flag when the element is genuinely
    above the next storey level.
    """
    issues: list[dict[str, Any]] = []

    storey_elevations: dict[int, float] = {}
    for storey in ifc_file.by_type("IfcBuildingStorey"):
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                storey.ObjectPlacement
            )
            storey_elevations[storey.id()] = float(mat[2][3])
        except Exception:
            continue

    # Compute max floor-to-floor height from consecutive storeys
    sorted_elevs = sorted(set(storey_elevations.values()))
    if len(sorted_elevs) >= 2:
        max_ftf = max(
            sorted_elevs[i + 1] - sorted_elevs[i]
            for i in range(len(sorted_elevs) - 1)
        )
    else:
        max_ftf = 4.0  # fallback

    for elem in ifc_file.by_type("IfcBuildingElement"):
        container = ifcopenshell.util.element.get_container(elem)
        if not container or container.id() not in storey_elevations:
            continue
        storey_z = storey_elevations[container.id()]
        if storey_z < 1.0:
            continue  # ground floor — skip

        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                elem.ObjectPlacement
            )
            elem_z = float(mat[2][3])
        except Exception:
            continue

        # Elements within [storey_z, storey_z + ftf] are valid placements
        if elem_z <= storey_z + max_ftf + 0.5:
            continue

        expected_double = storey_z * 2
        if abs(elem_z - expected_double) < 0.5:
            issues.append({
                "severity": "error",
                "check": "double_elevation",
                "element": elem.GlobalId,
                "element_type": elem.is_a(),
                "message": (
                    f"{elem.Name or elem.GlobalId} ({elem.is_a()}) at Z={elem_z:.1f} m "
                    f"appears to be double-elevated (storey Z={storey_z:.1f} m, "
                    f"expected element Z near storey level, not {expected_double:.1f} m)."
                ),
            })

    return issues


def check_vertical_column_alignment(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Warn if columns on consecutive storeys do not align vertically.

    Groups columns by their (x, y) position rounded to 0.5 m grid, then
    checks that each position appears on consecutive storeys.
    """
    issues: list[dict[str, Any]] = []

    # Collect storey elevations in order
    storeys = sorted(
        ifc_file.by_type("IfcBuildingStorey"),
        key=lambda s: getattr(s, "Elevation", 0) or 0,
    )
    storey_ids = [s.id() for s in storeys]
    if len(storey_ids) < 2:
        return issues

    # Map storey_id → set of column XY grid positions
    GRID = 0.5  # rounding grid
    col_positions_by_storey: dict[int, set[tuple[float, float]]] = {
        sid: set() for sid in storey_ids
    }

    for col in ifc_file.by_type("IfcColumn"):
        container = ifcopenshell.util.element.get_container(col)
        if not container or container.id() not in col_positions_by_storey:
            continue
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                col.ObjectPlacement
            )
            gx = round(float(mat[0][3]) / GRID) * GRID
            gy = round(float(mat[1][3]) / GRID) * GRID
            col_positions_by_storey[container.id()].add((gx, gy))
        except Exception:
            continue

    # Check consecutive storey pairs
    for i in range(len(storey_ids) - 1):
        lower = col_positions_by_storey.get(storey_ids[i], set())
        upper = col_positions_by_storey.get(storey_ids[i + 1], set())
        if not lower or not upper:
            continue
        missing_above = lower - upper
        if missing_above and len(missing_above) > len(lower) * 0.3:
            issues.append({
                "severity": "warning",
                "check": "column_alignment",
                "message": (
                    f"{len(missing_above)} column position(s) on "
                    f"'{storeys[i].Name or storeys[i].GlobalId}' have no "
                    f"matching column on the storey above. Columns should "
                    f"generally align vertically for structural continuity."
                ),
            })

    return issues


def check_beam_above_roof_level(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Detect beams placed at or above the roof elevation.

    On the topmost storey, beams at the roof level are structurally
    redundant and their profile depth causes them to visually protrude
    above the roof plane.  This is the post-build counterpart of the
    plan-level ``check_top_storey_redundant_beams``.
    """
    issues: list[dict[str, Any]] = []

    roofs = ifc_file.by_type("IfcRoof")
    if not roofs:
        return issues

    # Determine the maximum roof Z placement
    max_roof_z: float | None = None
    for roof in roofs:
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                roof.ObjectPlacement
            )
            rz = float(mat[2][3])
            if max_roof_z is None or rz > max_roof_z:
                max_roof_z = rz
        except Exception:
            continue

    if max_roof_z is None:
        return issues

    for beam in ifc_file.by_type("IfcBeam"):
        try:
            mat = ifcopenshell.util.placement.get_local_placement(
                beam.ObjectPlacement
            )
            beam_z = float(mat[2][3])
        except Exception:
            continue

        if beam_z >= max_roof_z - 0.1:
            issues.append({
                "severity": "error",
                "check": "beam_above_roof",
                "element": beam.GlobalId,
                "element_type": "IfcBeam",
                "message": (
                    f"Beam '{beam.Name or beam.GlobalId}' at Z={beam_z:.1f} m "
                    f"is at or above the roof level ({max_roof_z:.1f} m). "
                    f"Beams at the roof line protrude above the building — "
                    f"remove them from the top storey."
                ),
            })

    return issues


def check_pset_property_names(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    """Validate that standard Pset_*Common property sets use correct property names.

    For each element that has a property set whose name starts with ``Pset_``
    and ends with ``Common``, cross-check its property names against the bSDD
    standard.  Unknown properties in standard psets are flagged as warnings
    (they won't break the file, but they deviate from the IFC4 standard).
    """
    from building_blocks.bsdd import get_valid_pset_property_names

    issues: list[dict[str, Any]] = []

    for elem in ifc_file.by_type("IfcBuildingElement"):
        try:
            psets = ifcopenshell.util.element.get_psets(elem)
        except Exception:
            continue

        for pset_name, props in psets.items():
            # Only validate standard Pset_*Common sets
            if not (pset_name.startswith("Pset_") and pset_name.endswith("Common")):
                continue

            valid_names = get_valid_pset_property_names(pset_name)
            if valid_names is None:
                continue  # unknown pset — skip

            valid_set = {n.lower() for n in valid_names}
            for prop_name in props:
                if prop_name == "id":
                    continue  # ifcopenshell internal key
                if prop_name.lower() not in valid_set:
                    issues.append({
                        "severity": "warning",
                        "check": "pset_property_name",
                        "element": elem.GlobalId,
                        "element_type": elem.is_a(),
                        "message": (
                            f"{elem.Name or elem.GlobalId} ({elem.is_a()}): "
                            f"property '{prop_name}' in {pset_name} is not a "
                            f"standard bSDD/IFC4 property name. "
                            f"Valid: {', '.join(valid_names[:8])}"
                        ),
                    })

    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_all_checks(
    ifc_path: str,
    ifc_file: ifcopenshell.file | None = None,
) -> dict[str, Any]:
    """Run all semantic checks and return combined results.

    Args:
        ifc_path: Path to IFC file (used only if ifc_file is None).
        ifc_file: Pre-opened IFC file object to avoid redundant I/O.
    """
    if ifc_file is None:
        ifc_file = ifcopenshell.open(ifc_path)
    all_issues: list[dict[str, Any]] = []
    all_issues.extend(check_spatial_containment(ifc_file))
    all_issues.extend(check_floating_openings(ifc_file))
    all_issues.extend(check_element_geometry(ifc_file))
    all_issues.extend(check_disconnected_storeys(ifc_file))
    all_issues.extend(check_wall_count(ifc_file))
    all_issues.extend(check_roof_exists(ifc_file))
    all_issues.extend(check_slab_exists(ifc_file))
    all_issues.extend(check_bounding_box_sanity(ifc_file))
    all_issues.extend(check_double_elevation(ifc_file))
    all_issues.extend(check_vertical_column_alignment(ifc_file))
    all_issues.extend(check_beam_above_roof_level(ifc_file))
    all_issues.extend(check_pset_property_names(ifc_file))

    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": all_issues,
    }
