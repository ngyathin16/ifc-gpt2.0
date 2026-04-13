"""
Pre-build validation of the BuildingPlan.

Catches geometric and logical errors BEFORE IFC generation, so the repair
node can fix the plan JSON rather than patching a broken IFC file.
"""
from __future__ import annotations

import math
from typing import Any


def _wall_length(w: dict) -> float:
    """Euclidean length of a wall from start_point to end_point."""
    sp = w["start_point"]
    ep = w["end_point"]
    return math.hypot(ep[0] - sp[0], ep[1] - sp[1])


def _point_eq(a: list[float], b: list[float], tol: float = 0.01) -> bool:
    """Check if two 2D points are approximately equal."""
    return math.hypot(a[0] - b[0], a[1] - b[1]) < tol


def _bounding_box(points: list[list[float]]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) for a list of 2D points."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _bb_area(bb: tuple[float, float, float, float]) -> float:
    return (bb[2] - bb[0]) * (bb[3] - bb[1])


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_walls_form_closed_loops(plan: dict) -> list[dict[str, Any]]:
    """Verify that exterior walls on each storey form at least one closed loop.

    The most common LLM error is generating 1-2 walls instead of a full
    enclosure.  This check groups walls by storey, then tries to walk the
    endpoint graph looking for a cycle.
    """
    issues: list[dict[str, Any]] = []
    walls_by_storey: dict[str, list[dict]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            ref = elem.get("storey_ref", "")
            walls_by_storey.setdefault(ref, []).append(elem)

    for storey_ref, walls in walls_by_storey.items():
        ext_walls = [w for w in walls if w.get("is_external", True)]
        if len(ext_walls) < 3:
            issues.append({
                "severity": "error",
                "check": "wall_enclosure",
                "storey_ref": storey_ref,
                "message": (
                    f"Storey '{storey_ref}' has only {len(ext_walls)} exterior wall(s). "
                    "At least 3 walls are required to form a closed room."
                ),
            })
            continue

        # Build adjacency: endpoint → list of wall_refs whose start or end is there
        endpoint_map: dict[tuple[float, float], list[str]] = {}
        for w in ext_walls:
            sp = tuple(round(c, 3) for c in w["start_point"][:2])
            ep = tuple(round(c, 3) for c in w["end_point"][:2])
            endpoint_map.setdefault(sp, []).append(w["wall_ref"])
            endpoint_map.setdefault(ep, []).append(w["wall_ref"])

        # Check that every endpoint is shared by exactly 2 walls (forms a loop)
        dangling = [pt for pt, refs in endpoint_map.items() if len(refs) < 2]
        if dangling:
            issues.append({
                "severity": "error",
                "check": "wall_enclosure",
                "storey_ref": storey_ref,
                "message": (
                    f"Storey '{storey_ref}': {len(dangling)} dangling wall endpoint(s) — "
                    f"walls do not form a closed loop. Dangling points: "
                    f"{[list(p) for p in dangling[:4]]}"
                ),
            })

    return issues


def check_slab_covers_walls(plan: dict) -> list[dict[str, Any]]:
    """Check that each storey's floor slab boundary approximately matches wall extents."""
    issues: list[dict[str, Any]] = []

    wall_bb_by_storey: dict[str, tuple] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            ref = elem["storey_ref"]
            pts = [elem["start_point"][:2], elem["end_point"][:2]]
            if ref not in wall_bb_by_storey:
                wall_bb_by_storey[ref] = _bounding_box(pts)
            else:
                bb = wall_bb_by_storey[ref]
                new_bb = _bounding_box(pts)
                wall_bb_by_storey[ref] = (
                    min(bb[0], new_bb[0]), min(bb[1], new_bb[1]),
                    max(bb[2], new_bb[2]), max(bb[3], new_bb[3]),
                )

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "slab" or elem.get("slab_type") == "LANDING":
            continue
        ref = elem["storey_ref"]
        wall_bb = wall_bb_by_storey.get(ref)
        if wall_bb is None:
            continue

        slab_bb = _bounding_box(elem["boundary_points"])
        wall_area = _bb_area(wall_bb)
        slab_area = _bb_area(slab_bb)

        if wall_area < 0.01:
            continue

        ratio = slab_area / wall_area if wall_area > 0 else 0
        if ratio < 0.5:
            issues.append({
                "severity": "error",
                "check": "slab_coverage",
                "storey_ref": ref,
                "message": (
                    f"Storey '{ref}': floor slab area ({slab_area:.1f} m²) covers only "
                    f"{ratio:.0%} of wall bounding box ({wall_area:.1f} m²). "
                    "Slab boundary_points should match the wall footprint."
                ),
            })
        elif ratio > 2.0:
            issues.append({
                "severity": "warning",
                "check": "slab_coverage",
                "storey_ref": ref,
                "message": (
                    f"Storey '{ref}': slab is {ratio:.1f}× larger than wall bounding box. "
                    "Check slab boundary_points."
                ),
            })

    return issues


def check_roof_covers_walls(plan: dict) -> list[dict[str, Any]]:
    """Check that roof boundary approximately matches the building footprint."""
    issues: list[dict[str, Any]] = []

    # Collect all wall endpoints across all storeys to get building footprint
    all_wall_pts: list[list[float]] = []
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            all_wall_pts.append(elem["start_point"][:2])
            all_wall_pts.append(elem["end_point"][:2])

    if not all_wall_pts:
        return issues

    wall_bb = _bounding_box(all_wall_pts)
    wall_area = _bb_area(wall_bb)
    if wall_area < 0.01:
        return issues

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "roof":
            continue
        roof_bb = _bounding_box(elem["boundary_points"])
        roof_area = _bb_area(roof_bb)
        ratio = roof_area / wall_area if wall_area > 0 else 0

        if ratio < 0.5:
            issues.append({
                "severity": "error",
                "check": "roof_coverage",
                "storey_ref": elem.get("storey_ref", ""),
                "message": (
                    f"Roof area ({roof_area:.1f} m²) covers only {ratio:.0%} of "
                    f"building footprint ({wall_area:.1f} m²). "
                    "Roof boundary_points should cover the full building footprint."
                ),
            })

    return issues


def check_openings_within_walls(plan: dict) -> list[dict[str, Any]]:
    """Check that doors/windows fit within their host wall dimensions."""
    issues: list[dict[str, Any]] = []

    wall_lengths: dict[str, float] = {}
    wall_heights: dict[str, float] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            ref = elem["wall_ref"]
            wall_lengths[ref] = _wall_length(elem)
            wall_heights[ref] = elem.get("height", 3.0)

    for elem in plan.get("elements", []):
        if elem.get("element_type") not in ("door", "window"):
            continue

        host = elem.get("host_wall_ref", "")
        wlen = wall_lengths.get(host)
        wheight = wall_heights.get(host)

        if wlen is None:
            issues.append({
                "severity": "error",
                "check": "opening_host",
                "message": (
                    f"Opening references wall '{host}' which does not exist."
                ),
            })
            continue

        dist = elem.get("distance_along_wall", 0)
        width = elem.get("width", 0.9)
        height = elem.get("height", 2.1)
        sill = elem.get("sill_height", 0)

        # Check horizontal fit: door/window center ± half-width must be within wall
        left_edge = dist - width / 2.0
        right_edge = dist + width / 2.0
        if left_edge < -0.05:
            issues.append({
                "severity": "error",
                "check": "opening_bounds",
                "message": (
                    f"{elem['element_type'].title()} on wall '{host}': "
                    f"left edge at {left_edge:.2f} m extends before wall start. "
                    f"Increase distance_along_wall (currently {dist:.2f} m)."
                ),
            })
        if right_edge > wlen + 0.05:
            issues.append({
                "severity": "error",
                "check": "opening_bounds",
                "message": (
                    f"{elem['element_type'].title()} on wall '{host}': "
                    f"right edge at {right_edge:.2f} m exceeds wall length {wlen:.2f} m. "
                    f"Reduce distance_along_wall or width."
                ),
            })

        # Check vertical fit
        if wheight is not None and (sill + height) > wheight + 0.05:
            issues.append({
                "severity": "error",
                "check": "opening_bounds",
                "message": (
                    f"{elem['element_type'].title()} on wall '{host}': "
                    f"top at {sill + height:.2f} m exceeds wall height {wheight:.2f} m."
                ),
            })

    return issues


def check_storey_refs(plan: dict) -> list[dict[str, Any]]:
    """Check that all element storey_refs reference valid storeys."""
    issues: list[dict[str, Any]] = []
    valid_refs = {s["storey_ref"] for s in plan.get("storeys", [])}

    for elem in plan.get("elements", []):
        ref = elem.get("storey_ref", "")
        if ref not in valid_refs:
            issues.append({
                "severity": "error",
                "check": "storey_ref",
                "message": (
                    f"Element with type '{elem.get('element_type')}' references "
                    f"storey '{ref}' which is not defined. "
                    f"Valid storeys: {sorted(valid_refs)}"
                ),
            })

    return issues


def check_wall_junctions(plan: dict) -> list[dict[str, Any]]:
    """Check that wall_junctions reference existing walls."""
    issues: list[dict[str, Any]] = []
    wall_refs = {
        elem["wall_ref"]
        for elem in plan.get("elements", [])
        if elem.get("element_type") == "wall"
    }

    for junc in plan.get("wall_junctions", []):
        for key in ("wall_ref_1", "wall_ref_2"):
            ref = junc.get(key, "")
            if ref and ref not in wall_refs:
                issues.append({
                    "severity": "warning",
                    "check": "wall_junction_ref",
                    "message": (
                        f"Wall junction references '{ref}' which is not a defined wall."
                    ),
                })

    return issues


def check_opening_spacing(plan: dict) -> list[dict[str, Any]]:
    """Check that openings on the same wall have sufficient spacing.

    Uses Shapely interval geometry to detect:
      - Openings too close together (< MIN_OPENING_GAP edge-to-edge)
      - Openings too close to wall corners (< MIN_EDGE_CLEARANCE)
      - Walls too short to fit all their openings with proper spacing
    """
    from shapely.geometry import box as shapely_box

    MIN_OPENING_GAP = 0.5       # metres between opening edges
    MIN_EDGE_CLEARANCE = 0.3    # metres from opening edge to wall corner

    issues: list[dict[str, Any]] = []

    # Build wall length lookup
    wall_lengths: dict[str, float] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            wall_lengths[elem["wall_ref"]] = _wall_length(elem)

    # Group openings by host wall
    openings_by_wall: dict[str, list[dict]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") in ("door", "window"):
            host = elem.get("host_wall_ref", "")
            openings_by_wall.setdefault(host, []).append(elem)

    for wall_ref, openings in openings_by_wall.items():
        wlen = wall_lengths.get(wall_ref)
        if wlen is None or not openings:
            continue

        # Build sorted intervals: (left_edge, right_edge, element_dict)
        intervals: list[tuple[float, float, dict]] = []
        for op in openings:
            dist = op.get("distance_along_wall", 0.0)
            w = op.get("width", 0.9)
            intervals.append((dist - w / 2.0, dist + w / 2.0, op))
        intervals.sort(key=lambda t: t[0])

        n = len(intervals)

        # --- Capacity check: can wall fit all openings with gaps? ---
        total_width = sum(r - left for left, r, _ in intervals)
        min_required = (
            total_width
            + max(n - 1, 0) * MIN_OPENING_GAP
            + 2 * MIN_EDGE_CLEARANCE
        )
        if min_required > wlen + 0.01:
            issues.append({
                "severity": "error",
                "check": "opening_spacing",
                "message": (
                    f"Wall '{wall_ref}' (length {wlen:.1f} m) cannot fit "
                    f"{n} opening(s) with required spacing. "
                    f"Minimum wall length needed: {min_required:.1f} m. "
                    f"Consider a longer wall, fewer openings, or narrower openings."
                ),
            })
            continue  # skip detailed checks — capacity is the root issue

        # --- Edge clearance ---
        first_left = intervals[0][0]
        last_right = intervals[-1][1]
        if first_left < MIN_EDGE_CLEARANCE - 0.01:
            op = intervals[0][2]
            issues.append({
                "severity": "error",
                "check": "opening_spacing",
                "message": (
                    f"Wall '{wall_ref}': {op['element_type']} is only "
                    f"{first_left:.2f} m from the wall start (minimum "
                    f"{MIN_EDGE_CLEARANCE} m required for structural integrity)."
                ),
            })
        if (wlen - last_right) < MIN_EDGE_CLEARANCE - 0.01:
            op = intervals[-1][2]
            issues.append({
                "severity": "error",
                "check": "opening_spacing",
                "message": (
                    f"Wall '{wall_ref}': {op['element_type']} is only "
                    f"{wlen - last_right:.2f} m from the wall end (minimum "
                    f"{MIN_EDGE_CLEARANCE} m required for structural integrity)."
                ),
            })

        # --- Pairwise spacing via Shapely buffered intervals ---
        if n >= 2:
            half_gap = MIN_OPENING_GAP / 2.0
            shapely_intervals = []
            for left, right, op in intervals:
                shapely_intervals.append(
                    (shapely_box(left, 0, right, 1).buffer(half_gap), op)
                )
            for i in range(len(shapely_intervals) - 1):
                geom_i, op_i = shapely_intervals[i]
                geom_j, op_j = shapely_intervals[i + 1]
                if geom_i.intersects(geom_j):
                    _, right_i, _ = intervals[i]
                    left_j, _, _ = intervals[i + 1]
                    gap = left_j - right_i
                    issues.append({
                        "severity": "error",
                        "check": "opening_spacing",
                        "message": (
                            f"Wall '{wall_ref}': {op_i['element_type']} and "
                            f"{op_j['element_type']} are only {gap:.2f} m apart "
                            f"(minimum {MIN_OPENING_GAP} m required). "
                            f"Increase distance_along_wall values to space them "
                            f"further apart, or move one to a different wall."
                        ),
                    })

    return issues


def check_building_opening_capacity(plan: dict) -> list[dict[str, Any]]:
    """Check that each storey has enough wall perimeter for all openings.

    Uses Shapely to compute the building footprint perimeter from exterior
    wall endpoints, then verifies that the total opening width does not
    exceed a safe fraction of available perimeter.
    """
    from shapely.geometry import MultiPoint

    MAX_OPENING_RATIO = 0.60  # openings may occupy at most 60% of perimeter

    issues: list[dict[str, Any]] = []

    # Collect exterior wall endpoints per storey
    wall_pts_by_storey: dict[str, list[tuple[float, float]]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall" and elem.get("is_external", True):
            ref = elem.get("storey_ref", "")
            wall_pts_by_storey.setdefault(ref, []).extend([
                tuple(elem["start_point"][:2]),
                tuple(elem["end_point"][:2]),
            ])

    # Collect openings per storey
    openings_by_storey: dict[str, list[dict]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") in ("door", "window"):
            ref = elem.get("storey_ref", "")
            openings_by_storey.setdefault(ref, []).append(elem)

    for storey_ref, pts in wall_pts_by_storey.items():
        openings = openings_by_storey.get(storey_ref, [])
        if not openings or len(pts) < 3:
            continue

        try:
            hull = MultiPoint(pts).convex_hull
            perimeter = hull.length if hasattr(hull, "length") else 0.0
        except Exception:
            continue

        if perimeter < 1.0:
            continue

        total_opening_width = sum(op.get("width", 0.9) for op in openings)
        ratio = total_opening_width / perimeter

        if ratio > MAX_OPENING_RATIO:
            issues.append({
                "severity": "error",
                "check": "building_opening_capacity",
                "message": (
                    f"Storey '{storey_ref}': total opening width "
                    f"({total_opening_width:.1f} m) is {ratio:.0%} of the "
                    f"building perimeter ({perimeter:.1f} m), exceeding the "
                    f"{MAX_OPENING_RATIO:.0%} maximum. The building is too small "
                    f"for this many/large openings. Consider enlarging the "
                    f"building or reducing the number/size of openings."
                ),
            })

    return issues


def check_minimum_dimensions(plan: dict) -> list[dict[str, Any]]:
    """Check elements have realistic minimum dimensions."""
    issues: list[dict[str, Any]] = []

    for elem in plan.get("elements", []):
        etype = elem.get("element_type")

        if etype == "wall":
            length = _wall_length(elem)
            if length < 0.1:
                issues.append({
                    "severity": "error",
                    "check": "min_dimensions",
                    "message": (
                        f"Wall '{elem.get('wall_ref')}' has near-zero length ({length:.3f} m)."
                    ),
                })
            height = elem.get("height", 3.0)
            if height < 0.5:
                issues.append({
                    "severity": "error",
                    "check": "min_dimensions",
                    "message": (
                        f"Wall '{elem.get('wall_ref')}' height {height:.2f} m is unrealistically small."
                    ),
                })

        elif etype == "slab":
            depth = elem.get("depth", 0.2)
            if depth <= 0:
                issues.append({
                    "severity": "error",
                    "check": "min_dimensions",
                    "message": "Slab has zero or negative depth.",
                })

    return issues


def check_elevation_double_counting(plan: dict) -> list[dict[str, Any]]:
    """Detect likely elevation double-counting in element coordinates.

    If a column/beam/slab's elevation equals its storey elevation, the
    element will end up at 2× the intended height because the storey
    ObjectPlacement already applies the offset.
    """
    issues: list[dict[str, Any]] = []
    storey_elevations: dict[str, float] = {}
    storey_heights: dict[str, float] = {}
    for s in plan.get("storeys", []):
        storey_elevations[s["storey_ref"]] = s.get("elevation", 0.0)
        storey_heights[s["storey_ref"]] = s.get("floor_to_floor_height", 3.0)

    for elem in plan.get("elements", []):
        etype = elem.get("element_type")
        ref = elem.get("storey_ref", "")
        storey_elev = storey_elevations.get(ref, 0.0)
        if storey_elev == 0.0:
            continue  # ground floor — no risk of double-counting

        ftf = storey_heights.get(ref, 3.0)

        elem_elev: float | None = None
        label = ""

        if etype == "column":
            elem_elev = elem.get("base_elevation")
            label = f"Column '{elem.get('column_ref', '?')}'"
        elif etype == "beam":
            elem_elev = elem.get("elevation")
            label = f"Beam '{elem.get('beam_ref', '?')}'"
        elif etype == "slab":
            elem_elev = elem.get("elevation")
            label = f"Slab on storey '{ref}'"

        if elem_elev is None:
            continue
        # A storey-relative value should be in [0, floor_to_floor_height].
        # Only flag when it matches the storey elevation AND exceeds the
        # floor-to-floor height — that strongly suggests an absolute world
        # coordinate that will be double-counted by storey placement.
        if abs(elem_elev - storey_elev) < 0.01 and elem_elev > ftf + 0.01:
            issues.append({
                "severity": "error",
                "check": "elevation_double_count",
                "storey_ref": ref,
                "message": (
                    f"{label}: elevation {elem_elev:.2f} m equals storey "
                    f"elevation {storey_elev:.2f} m — this will double-count "
                    f"because the storey placement already applies the offset. "
                    f"Use a storey-relative value (e.g. 0.0) instead."
                ),
            })

    return issues


def check_beam_span_limits(plan: dict) -> list[dict[str, Any]]:
    """Error if any beam spans more than 15 m without intermediate support."""
    MAX_SPAN = 15.0  # metres
    issues: list[dict[str, Any]] = []

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "beam":
            continue
        sp = elem.get("start_point", [0, 0])
        ep = elem.get("end_point", [0, 0])
        span = math.hypot(ep[0] - sp[0], ep[1] - sp[1])
        if span > MAX_SPAN:
            issues.append({
                "severity": "error",
                "check": "beam_span",
                "storey_ref": elem.get("storey_ref", ""),
                "message": (
                    f"Beam '{elem.get('beam_ref', '?')}' spans {span:.1f} m, "
                    f"exceeding the {MAX_SPAN:.0f} m maximum. Add intermediate "
                    f"columns or break the beam into shorter segments."
                ),
            })

    return issues


def check_elevator_requirement(plan: dict) -> list[dict[str, Any]]:
    """Warn if building has >4 storeys but no elevator element."""
    issues: list[dict[str, Any]] = []
    num_storeys = len(plan.get("storeys", []))
    if num_storeys <= 4:
        return issues

    has_elevator = any(
        elem.get("element_type") == "elevator"
        for elem in plan.get("elements", [])
    )
    if not has_elevator:
        issues.append({
            "severity": "warning",
            "check": "elevator_required",
            "message": (
                f"Building has {num_storeys} storeys but no elevator. "
                f"Buildings above 4 storeys typically require elevator access."
            ),
        })

    return issues


def check_column_wall_overlap(plan: dict) -> list[dict[str, Any]]:
    """Warn when a column centre sits directly on a wall line."""
    issues: list[dict[str, Any]] = []

    # Build per-storey wall segments
    wall_segments_by_storey: dict[str, list[tuple[str, list, list]]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            ref = elem.get("storey_ref", "")
            wall_segments_by_storey.setdefault(ref, []).append(
                (elem.get("wall_ref", ""), elem["start_point"][:2], elem["end_point"][:2])
            )

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "column":
            continue
        ref = elem.get("storey_ref", "")
        pos = elem.get("position", [0, 0])[:2]
        thickness = 0.25  # half-column-width tolerance

        for wall_ref, sp, ep in wall_segments_by_storey.get(ref, []):
            # Distance from point to line segment
            dx, dy = ep[0] - sp[0], ep[1] - sp[1]
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq < 1e-6:
                continue
            t = max(0, min(1, ((pos[0] - sp[0]) * dx + (pos[1] - sp[1]) * dy) / seg_len_sq))
            closest_x = sp[0] + t * dx
            closest_y = sp[1] + t * dy
            dist = math.hypot(pos[0] - closest_x, pos[1] - closest_y)

            if dist < thickness:
                issues.append({
                    "severity": "warning",
                    "check": "column_wall_overlap",
                    "storey_ref": ref,
                    "message": (
                        f"Column '{elem.get('column_ref', '?')}' at "
                        f"({pos[0]:.1f}, {pos[1]:.1f}) is only {dist:.2f} m "
                        f"from wall '{wall_ref}' — geometry will overlap."
                    ),
                })
                break  # one warning per column is enough

    return issues


def _points_on_same_line(
    p1: list[float], p2: list[float],
    q1: list[float], q2: list[float],
    tol: float = 0.1,
) -> bool:
    """Check if two line segments are approximately collinear."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < 1e-6:
        return False
    # Perpendicular distance from q1 and q2 to line p1→p2
    dist_q1 = abs((q1[0] - p1[0]) * dy - (q1[1] - p1[1]) * dx) / seg_len
    dist_q2 = abs((q2[0] - p1[0]) * dy - (q2[1] - p1[1]) * dx) / seg_len
    return dist_q1 < tol and dist_q2 < tol


def check_top_storey_redundant_beams(plan: dict) -> list[dict[str, Any]]:
    """Flag beams on the topmost storey when a roof already exists.

    Perimeter beams at the roof level are structurally redundant (the roof
    slab already spans the top) and their profile depth causes them to
    visually protrude above the roof plane.
    """
    issues: list[dict[str, Any]] = []
    storeys = plan.get("storeys", [])
    if not storeys:
        return issues

    top_storey_ref = max(storeys, key=lambda s: s.get("elevation", 0))["storey_ref"]

    has_roof = any(
        e.get("element_type") == "roof" and e.get("storey_ref") == top_storey_ref
        for e in plan.get("elements", [])
    )
    if not has_roof:
        return issues

    for elem in plan.get("elements", []):
        if elem.get("element_type") == "beam" and elem.get("storey_ref") == top_storey_ref:
            issues.append({
                "severity": "error",
                "check": "top_storey_beam",
                "storey_ref": top_storey_ref,
                "message": (
                    f"Beam '{elem.get('beam_ref', '?')}' on top storey "
                    f"'{top_storey_ref}' is redundant — the roof slab already "
                    f"provides structural spanning at this level. Remove all "
                    f"beams from the top storey to avoid visual protrusion "
                    f"above the roof."
                ),
            })

    return issues


def check_beam_wider_than_wall(plan: dict) -> list[dict[str, Any]]:
    """Flag beams whose width exceeds the co-linear wall's thickness.

    In real construction, perimeter beams are hidden within the wall
    thickness.  When beam width > wall thickness the beam protrudes
    beyond the wall face, appearing exposed on the exterior facade.
    """
    issues: list[dict[str, Any]] = []

    walls: dict[str, dict] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            walls[elem["wall_ref"]] = elem

    seen_messages: set[str] = set()  # deduplicate per-storey

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "beam":
            continue

        beam_sp = elem.get("start_point", [0, 0])[:2]
        beam_ep = elem.get("end_point", [0, 0])[:2]
        beam_width = elem.get("width", 0.2)
        storey_ref = elem.get("storey_ref", "")

        for wall_ref, wall in walls.items():
            if wall.get("storey_ref") != storey_ref:
                continue

            wall_sp = wall["start_point"][:2]
            wall_ep = wall["end_point"][:2]
            wall_thickness = wall.get("thickness", 0.2)

            if not _points_on_same_line(beam_sp, beam_ep, wall_sp, wall_ep):
                continue

            if beam_width > wall_thickness + 0.01:
                key = f"{storey_ref}_{wall_ref}"
                if key in seen_messages:
                    break
                seen_messages.add(key)
                issues.append({
                    "severity": "error",
                    "check": "beam_wider_than_wall",
                    "storey_ref": storey_ref,
                    "message": (
                        f"Beam '{elem.get('beam_ref', '?')}' (width "
                        f"{beam_width:.2f} m) runs along wall '{wall_ref}' "
                        f"(thickness {wall_thickness:.2f} m) but is wider "
                        f"than the wall. The beam will protrude beyond the "
                        f"exterior wall face. Reduce beam width to ≤ "
                        f"{wall_thickness:.2f} m so the beam is hidden "
                        f"within the wall."
                    ),
                })
            break

    return issues


def check_beam_window_vertical_clash(plan: dict) -> list[dict[str, Any]]:
    """Flag beams whose vertical range overlaps with windows on the same wall.

    A beam centred at `elevation` with profile depth `d` occupies
    [elevation − d/2, elevation + d/2].  If that range intersects a window's
    [sill_height, sill_height + height] on the same wall, the beam geometry
    will visually clash with the window opening.
    """
    issues: list[dict[str, Any]] = []

    walls: dict[str, dict] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "wall":
            walls[elem["wall_ref"]] = elem

    windows_by_wall: dict[str, list[dict]] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "window":
            host = elem.get("host_wall_ref", "")
            windows_by_wall.setdefault(host, []).append(elem)

    for elem in plan.get("elements", []):
        if elem.get("element_type") != "beam":
            continue

        beam_sp = elem.get("start_point", [0, 0])[:2]
        beam_ep = elem.get("end_point", [0, 0])[:2]
        beam_elev = elem.get("elevation", 3.0)
        beam_depth = elem.get("depth", 0.4)
        storey_ref = elem.get("storey_ref", "")

        beam_bottom = beam_elev - beam_depth / 2
        beam_top = beam_elev + beam_depth / 2

        for wall_ref, wall in walls.items():
            if wall.get("storey_ref") != storey_ref:
                continue

            wall_sp = wall["start_point"][:2]
            wall_ep = wall["end_point"][:2]

            if not _points_on_same_line(beam_sp, beam_ep, wall_sp, wall_ep):
                continue

            for win in windows_by_wall.get(wall_ref, []):
                win_sill = win.get("sill_height", 0.0)
                win_top = win_sill + win.get("height", 1.5)

                if beam_bottom < win_top and beam_top > win_sill:
                    issues.append({
                        "severity": "error",
                        "check": "beam_window_clash",
                        "storey_ref": storey_ref,
                        "message": (
                            f"Beam '{elem.get('beam_ref', '?')}' vertical "
                            f"range [{beam_bottom:.2f}, {beam_top:.2f}] m "
                            f"overlaps with window (sill {win_sill:.2f}, "
                            f"top {win_top:.2f}) on wall '{wall_ref}'. "
                            f"Move the beam above the window or adjust "
                            f"the window position."
                        ),
                    })
                    break
            break

    return issues


def check_opening_consistency_across_floors(plan: dict) -> list[dict[str, Any]]:
    """Warn if some storeys have windows but similar storeys do not."""
    issues: list[dict[str, Any]] = []

    windows_per_storey: dict[str, int] = {}
    for elem in plan.get("elements", []):
        if elem.get("element_type") == "window":
            ref = elem.get("storey_ref", "")
            windows_per_storey[ref] = windows_per_storey.get(ref, 0) + 1

    storey_refs = [s["storey_ref"] for s in plan.get("storeys", [])]
    if len(storey_refs) < 2:
        return issues

    counts = [windows_per_storey.get(r, 0) for r in storey_refs]
    median_count = sorted(counts)[len(counts) // 2]

    if median_count == 0:
        return issues

    for ref, count in zip(storey_refs, counts):
        if count == 0 and median_count > 0:
            issues.append({
                "severity": "warning",
                "check": "opening_consistency",
                "storey_ref": ref,
                "message": (
                    f"Storey '{ref}' has no windows while most storeys have "
                    f"~{median_count}. This may be intentional (plant room) "
                    f"or an omission."
                ),
            })

    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_plan(plan_dict: dict) -> dict[str, Any]:
    """Run all plan-level checks.

    Returns:
        {
            "valid": bool,
            "error_count": int,
            "warning_count": int,
            "issues": [{"severity", "check", "message", ...}]
        }
    """
    all_issues: list[dict[str, Any]] = []
    all_issues.extend(check_storey_refs(plan_dict))
    all_issues.extend(check_walls_form_closed_loops(plan_dict))
    all_issues.extend(check_slab_covers_walls(plan_dict))
    all_issues.extend(check_roof_covers_walls(plan_dict))
    all_issues.extend(check_openings_within_walls(plan_dict))
    all_issues.extend(check_opening_spacing(plan_dict))
    all_issues.extend(check_building_opening_capacity(plan_dict))
    all_issues.extend(check_wall_junctions(plan_dict))
    all_issues.extend(check_minimum_dimensions(plan_dict))
    all_issues.extend(check_elevation_double_counting(plan_dict))
    all_issues.extend(check_beam_span_limits(plan_dict))
    all_issues.extend(check_elevator_requirement(plan_dict))
    all_issues.extend(check_column_wall_overlap(plan_dict))
    all_issues.extend(check_opening_consistency_across_floors(plan_dict))
    all_issues.extend(check_top_storey_redundant_beams(plan_dict))
    all_issues.extend(check_beam_wider_than_wall(plan_dict))
    all_issues.extend(check_beam_window_vertical_clash(plan_dict))

    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": all_issues,
    }
