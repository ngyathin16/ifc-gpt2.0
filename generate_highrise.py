"""
Generate a comprehensive 20-storey highrise BuildingPlan and build the IFC file.

Building: 50 m × 100 m, 20 storeys, 3.5 m floor-to-floor
Features exercised: walls, columns, beams, slabs, doors, windows, stairs,
                    railings, roof, wall junctions, type definitions.

Usage:
    uv run python generate_highrise.py
"""
from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Building parameters
# ---------------------------------------------------------------------------
BUILDING_WIDTH = 50.0       # X-axis (South/North walls)
BUILDING_LENGTH = 100.0     # Y-axis (East/West walls)
NUM_STOREYS = 20
FLOOR_HEIGHT = 3.5
WALL_THICKNESS = 0.25
WALL_HEIGHT = FLOOR_HEIGHT

# Openings
WIN_WIDTH = 1.5
WIN_HEIGHT = 1.5
WIN_SILL = 0.9
WIN_SPACING = 6.0           # centre-to-centre along wall

DOOR_WIDTH = 1.0
DOOR_HEIGHT = 2.1
ENTRANCE_DOOR_WIDTH = 1.5

# Spacing constraints (must match validation/plan_checks.py)
MIN_GAP = 0.5
MIN_EDGE = 0.3

# Columns
COL_WIDTH = 0.5
COL_DEPTH = 0.5

# Beams
BEAM_WIDTH = 0.2       # must be ≤ WALL_THICKNESS so beam hides within wall
BEAM_DEPTH = 0.5

# Stairs
STAIR_WIDTH = 1.5
NUM_RISERS = 20             # 3.5 / 0.175 = 20
RISER_HEIGHT = 0.175
TREAD_DEPTH = 0.25
STAIR_LENGTH = NUM_RISERS * TREAD_DEPTH  # 5.0 m

# Column / beam spacing (must keep beam spans ≤ 15 m)
COL_SPACING = 12.5

# Railing
RAILING_HEIGHT = 1.0
RAILING_DIAM = 0.05

# Elevators
ELEVATOR_WIDTH = 2.0
ELEVATOR_DEPTH = 2.0

# Corners of the floor plate (counter-clockwise)
CORNERS: list[list[float]] = [
    [0.0, 0.0],
    [BUILDING_WIDTH, 0.0],
    [BUILDING_WIDTH, BUILDING_LENGTH],
    [0.0, BUILDING_LENGTH],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wall_support_points(start: list[float], end: list[float]) -> list[list[float]]:
    """Evenly-spaced support points along a wall edge (inclusive of endpoints)."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    n = max(1, math.ceil(length / COL_SPACING))
    return [
        [round(start[0] + j / n * dx, 2), round(start[1] + j / n * dy, 2)]
        for j in range(n + 1)
    ]


def _inward_offset_points(
    pts: list[list[float]],
    start: list[float],
    end: list[float],
    offset: float,
) -> list[list[float]]:
    """Shift *pts* inward by *offset* along the wall's inward normal.

    ``create_2pt_wall`` extends wall thickness to the LEFT of the
    p1→p2 direction (= inward for a CCW-wound perimeter).  Beams must
    be centred within the wall, so we shift by ``WALL_THICKNESS / 2``.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    # Inward normal = left of direction for CCW polygon
    nx = -dy / length * offset
    ny = dx / length * offset
    return [[round(p[0] + nx, 3), round(p[1] + ny, 3)] for p in pts]


def _window_positions(
    wall_length: float,
    doors: list[tuple[float, float]],
    column_distances: list[float] | None = None,
) -> list[float]:
    """Return a list of window centre positions along a wall, skipping conflicts.

    *column_distances* are distances along the wall where perimeter columns
    sit.  Windows that would overlap a column are omitted.
    """
    col_dists = column_distances or []
    positions: list[float] = []
    pos = 3.0  # first window centre
    while pos + WIN_WIDTH / 2 + MIN_EDGE <= wall_length:
        conflict = False
        # Door clash
        for dc, dw in doors:
            gap = abs(pos - dc) - (WIN_WIDTH / 2 + dw / 2)
            if gap < MIN_GAP + 0.1:
                conflict = True
                break
        # Column clash — column width protrudes through the opening
        if not conflict:
            for cd in col_dists:
                gap = abs(pos - cd) - (WIN_WIDTH / 2 + COL_WIDTH / 2)
                if gap < MIN_GAP:
                    conflict = True
                    break
        if not conflict:
            positions.append(round(pos, 2))
        pos += WIN_SPACING
    return positions


# ---------------------------------------------------------------------------
# Plan generator
# ---------------------------------------------------------------------------

def _column_distances_along_wall(
    start: list[float], end: list[float],
) -> list[float]:
    """Return distances along the wall line where perimeter columns sit."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    n = max(1, math.ceil(length / COL_SPACING))
    return [round(j / n * length, 2) for j in range(n + 1)]


# Curtain-wall window parameters (floor-to-ceiling glazing)
CW_WIN_SILL = 0.1
CW_WIN_HEIGHT = 2.8       # nearly full height, leaving room for beam zone
CW_WIN_WIDTH = 2.5
CW_WIN_SPACING = 3.0      # tighter spacing for curtain wall

# Interior partition grid
PARTITION_SPACING_X = 10.0
PARTITION_SPACING_Y = 20.0


def generate_plan(features: list[str] | None = None) -> dict:
    feats = set(features or [])
    storeys: list[dict] = []
    elements: list[dict] = []
    wall_junctions: list[dict] = []

    has_columns = "columns" in feats
    has_beams = "beams" in feats
    has_ext_walls = "exterior_walls" in feats
    has_curtain = "curtain_wall" in feats
    has_slabs = "floor_slabs" in feats
    has_stairs = "stairs" in feats
    has_elevators = "elevators" in feats
    has_railings = "railings" in feats
    has_flat_roof = "flat_roof" in feats
    has_pitched_roof = "pitched_roof" in feats
    has_entrance = "entrance_doors" in feats
    has_partitions = "interior_partitions" in feats

    # --- Storey definitions ---
    for i in range(NUM_STOREYS):
        ref = f"F{i:02d}"
        storeys.append({
            "storey_ref": ref,
            "name": "Ground Floor" if i == 0 else f"Floor {i}",
            "elevation": round(i * FLOOR_HEIGHT, 2),
            "floor_to_floor_height": FLOOR_HEIGHT,
        })

    # --- Type definitions ---
    types = [
        {"type_ref": "ext_wall_250", "ifc_class": "IfcWallType",
         "preset": "exterior_wall_250"},
        {"type_ref": "rc_col_500", "ifc_class": "IfcColumnType",
         "preset": "concrete_column_500x500"},
        {"type_ref": "steel_beam", "ifc_class": "IfcBeamType",
         "preset": "steel_beam_300x500"},
    ]

    # Pre-compute column distances along each wall for window clash filter
    wall_col_dists: dict[int, list[float]] = {}
    if has_columns:
        for wi in range(4):
            wall_col_dists[wi] = _column_distances_along_wall(
                CORNERS[wi], CORNERS[(wi + 1) % 4],
            )

    # --- Per-storey elements ---
    for i in range(NUM_STOREYS):
        ref = f"F{i:02d}"
        is_ground = i == 0
        is_top = i == NUM_STOREYS - 1

        # ── Exterior walls (always present — needed for the building envelope) ──
        wall_refs: list[str] = []
        if has_ext_walls or has_curtain:
            for wi in range(4):
                wref = f"W{wi + 1}_{ref}"
                wall_refs.append(wref)
                elements.append({
                    "element_type": "wall",
                    "wall_ref": wref,
                    "component_id": "exterior_wall",
                    "storey_ref": ref,
                    "start_point": CORNERS[wi],
                    "end_point": CORNERS[(wi + 1) % 4],
                    "height": WALL_HEIGHT,
                    "thickness": WALL_THICKNESS,
                    "is_external": True,
                    "wall_type_ref": "ext_wall_250",
                })

            # Wall junctions (corner connectivity)
            for wi in range(4):
                wall_junctions.append({
                    "wall_ref_1": wall_refs[wi],
                    "wall_ref_2": wall_refs[(wi + 1) % 4],
                })

        # ── Interior partitions ──
        if has_partitions and wall_refs:
            # Simple grid of interior walls dividing the floor plate
            # X-direction partitions (parallel to Y-axis)
            px = PARTITION_SPACING_X
            while px < BUILDING_WIDTH - 1.0:
                wref = f"PX{int(px)}_{ref}"
                elements.append({
                    "element_type": "wall",
                    "wall_ref": wref,
                    "component_id": "interior_partition",
                    "storey_ref": ref,
                    "start_point": [px, WALL_THICKNESS],
                    "end_point": [px, BUILDING_LENGTH - WALL_THICKNESS],
                    "height": WALL_HEIGHT,
                    "thickness": 0.15,
                    "is_external": False,
                })
                px += PARTITION_SPACING_X
            # Y-direction partitions (parallel to X-axis)
            py = PARTITION_SPACING_Y
            while py < BUILDING_LENGTH - 1.0:
                wref = f"PY{int(py)}_{ref}"
                elements.append({
                    "element_type": "wall",
                    "wall_ref": wref,
                    "component_id": "interior_partition",
                    "storey_ref": ref,
                    "start_point": [WALL_THICKNESS, py],
                    "end_point": [BUILDING_WIDTH - WALL_THICKNESS, py],
                    "height": WALL_HEIGHT,
                    "thickness": 0.15,
                    "is_external": False,
                })
                py += PARTITION_SPACING_Y

        # ── Floor slab ──
        if has_slabs:
            elements.append({
                "element_type": "slab",
                "storey_ref": ref,
                "boundary_points": CORNERS,
                "depth": 0.25,
                "elevation": 0.0,
                "slab_type": "FLOOR",
            })

        # ── Columns (perimeter at COL_SPACING + interior core) ──
        if has_columns:
            seen_cols: set[tuple[float, float]] = set()
            col_positions: list[list[float]] = []
            for wi in range(4):
                for pt in _wall_support_points(CORNERS[wi], CORNERS[(wi + 1) % 4]):
                    key = (pt[0], pt[1])
                    if key not in seen_cols:
                        seen_cols.add(key)
                        col_positions.append(pt)
            for pt in [
                [BUILDING_WIDTH / 4, BUILDING_LENGTH / 4],
                [3 * BUILDING_WIDTH / 4, BUILDING_LENGTH / 4],
                [BUILDING_WIDTH / 4, 3 * BUILDING_LENGTH / 4],
                [3 * BUILDING_WIDTH / 4, 3 * BUILDING_LENGTH / 4],
            ]:
                key = (pt[0], pt[1])
                if key not in seen_cols:
                    seen_cols.add(key)
                    col_positions.append(pt)
            for ci, pos in enumerate(col_positions):
                elements.append({
                    "element_type": "column",
                    "column_ref": f"C{ci + 1}_{ref}",
                    "storey_ref": ref,
                    "position": [round(p, 2) for p in pos],
                    "base_elevation": 0.0,
                    "height": FLOOR_HEIGHT,
                    "profile_type": "RECTANGULAR",
                    "width": COL_WIDTH,
                    "depth": COL_DEPTH,
                    "radius": 0.15,
                    "column_type_ref": "rc_col_500",
                })

        # ── Beams ──
        if has_beams and not is_top:
            beam_elev_rel = round(WALL_HEIGHT - BEAM_DEPTH / 2, 2)
            beam_idx = 0
            for wi in range(4):
                w_start = CORNERS[wi]
                w_end = CORNERS[(wi + 1) % 4]
                pts = _wall_support_points(w_start, w_end)
                pts = _inward_offset_points(pts, w_start, w_end, WALL_THICKNESS / 2)
                for si in range(len(pts) - 1):
                    beam_idx += 1
                    elements.append({
                        "element_type": "beam",
                        "beam_ref": f"B{beam_idx}_{ref}",
                        "storey_ref": ref,
                        "start_point": pts[si],
                        "end_point": pts[si + 1],
                        "elevation": beam_elev_rel,
                        "profile_type": "I_SECTION",
                        "width": BEAM_WIDTH,
                        "depth": BEAM_DEPTH,
                        "beam_type_ref": "steel_beam",
                    })

        # ── Doors ──
        door_map: dict[str, list[tuple[float, float]]] = {}
        if wall_refs:
            # Stair-access doors
            if has_stairs:
                door_map.setdefault(f"W1_{ref}", []).append((5.0, DOOR_WIDTH))
                door_map.setdefault(f"W3_{ref}", []).append((5.0, DOOR_WIDTH))
            # Ground floor entrance doors
            if is_ground and has_entrance:
                door_map.setdefault(f"W1_{ref}", []).extend([
                    (15.0, ENTRANCE_DOOR_WIDTH),
                    (35.0, ENTRANCE_DOOR_WIDTH),
                ])

            for wall_ref, doors in door_map.items():
                for dc, dw in doors:
                    elements.append({
                        "element_type": "door",
                        "storey_ref": ref,
                        "host_wall_ref": wall_ref,
                        "distance_along_wall": dc,
                        "sill_height": 0.0,
                        "width": dw,
                        "height": DOOR_HEIGHT,
                        "operation_type": "SINGLE_SWING_LEFT",
                    })

        # ── Windows / curtain-wall glazing ──
        if wall_refs and (has_ext_walls or has_curtain):
            wall_lengths = [BUILDING_WIDTH, BUILDING_LENGTH,
                            BUILDING_WIDTH, BUILDING_LENGTH]
            for wi in range(4):
                wall_ref = f"W{wi + 1}_{ref}"
                wall_len = wall_lengths[wi]
                doors = door_map.get(wall_ref, [])
                col_dists = wall_col_dists.get(wi, [])

                if has_curtain:
                    # Curtain wall — floor-to-ceiling glazing panels
                    cw_pos = CW_WIN_WIDTH / 2 + MIN_EDGE
                    while cw_pos + CW_WIN_WIDTH / 2 + MIN_EDGE <= wall_len:
                        conflict = False
                        for dc, dw in doors:
                            if abs(cw_pos - dc) - (CW_WIN_WIDTH / 2 + dw / 2) < MIN_GAP + 0.1:
                                conflict = True
                                break
                        if not conflict:
                            for cd in col_dists:
                                if abs(cw_pos - cd) - (CW_WIN_WIDTH / 2 + COL_WIDTH / 2) < MIN_GAP:
                                    conflict = True
                                    break
                        if not conflict:
                            elements.append({
                                "element_type": "window",
                                "storey_ref": ref,
                                "host_wall_ref": wall_ref,
                                "distance_along_wall": round(cw_pos, 2),
                                "sill_height": CW_WIN_SILL,
                                "width": CW_WIN_WIDTH,
                                "height": CW_WIN_HEIGHT,
                                "partition_type": "SINGLE_PANEL",
                            })
                        cw_pos += CW_WIN_SPACING
                else:
                    # Standard punched windows
                    for wp in _window_positions(wall_len, doors, col_dists):
                        elements.append({
                            "element_type": "window",
                            "storey_ref": ref,
                            "host_wall_ref": wall_ref,
                            "distance_along_wall": wp,
                            "sill_height": WIN_SILL,
                            "width": WIN_WIDTH,
                            "height": WIN_HEIGHT,
                            "partition_type": "SINGLE_PANEL",
                        })

        # ── Elevators ──
        if has_elevators:
            elements.append({
                "element_type": "elevator",
                "storey_ref": ref,
                "position": [7.0, 3.0],
                "width": ELEVATOR_WIDTH,
                "depth": ELEVATOR_DEPTH,
                "name": f"Elevator_A_{ref}",
            })
            elements.append({
                "element_type": "elevator",
                "storey_ref": ref,
                "position": [43.0, 97.0],
                "width": ELEVATOR_WIDTH,
                "depth": ELEVATOR_DEPTH,
                "name": f"Elevator_B_{ref}",
            })

        # ── Stairs (except top floor) ──
        if has_stairs and not is_top:
            elements.append({
                "element_type": "stair",
                "storey_ref": ref,
                "start_point": [3.0, 3.0],
                "direction": [0.0, 1.0],
                "width": STAIR_WIDTH,
                "num_risers": NUM_RISERS,
                "riser_height": RISER_HEIGHT,
                "tread_depth": TREAD_DEPTH,
            })
            elements.append({
                "element_type": "stair",
                "storey_ref": ref,
                "start_point": [47.0, 95.0],
                "direction": [0.0, -1.0],
                "width": STAIR_WIDTH,
                "num_risers": NUM_RISERS,
                "riser_height": RISER_HEIGHT,
                "tread_depth": TREAD_DEPTH,
            })

            # ── Railings along stairs ──
            if has_railings:
                elements.append({
                    "element_type": "railing",
                    "storey_ref": ref,
                    "path_points": [
                        [3.0, 3.0, 0.0],
                        [3.0, 3.0 + STAIR_LENGTH, FLOOR_HEIGHT],
                    ],
                    "height": RAILING_HEIGHT,
                    "railing_diameter": RAILING_DIAM,
                })
                elements.append({
                    "element_type": "railing",
                    "storey_ref": ref,
                    "path_points": [
                        [47.0, 95.0, 0.0],
                        [47.0, 95.0 - STAIR_LENGTH, FLOOR_HEIGHT],
                    ],
                    "height": RAILING_HEIGHT,
                    "railing_diameter": RAILING_DIAM,
                })

    # ── Roof ──
    top_ref = f"F{NUM_STOREYS - 1:02d}"
    if has_pitched_roof:
        elements.append({
            "element_type": "roof",
            "storey_ref": top_ref,
            "boundary_points": CORNERS,
            "roof_type": "GABLE",
            "thickness": 0.30,
            "ridge_height": 3.0,
        })
    elif has_flat_roof:
        elements.append({
            "element_type": "roof",
            "storey_ref": top_ref,
            "boundary_points": CORNERS,
            "roof_type": "FLAT",
            "thickness": 0.30,
            "ridge_height": 0.0,
        })

    # Build feature description
    feat_desc = ", ".join(sorted(feats)) if feats else "basic"

    # ── Assemble plan ──
    return {
        "description": (
            f"{NUM_STOREYS}-storey commercial highrise, "
            f"{BUILDING_WIDTH:.0f} m × {BUILDING_LENGTH:.0f} m footprint, "
            f"features: {feat_desc}"
        ),
        "site": {"name": "Central Business District"},
        "building": {"name": "Tower One", "building_type": "Commercial"},
        "storeys": storeys,
        "types": types,
        "elements": elements,
        "wall_junctions": wall_junctions,
        "rooms": [],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _interactive_feature_selection() -> list[str]:
    """Show building features and let the user confirm or modify the selection."""
    from agent.nodes.clarify import BUILDING_FEATURES, _infer_defaults, _FEATURE_MAP, _resolve_conflicts

    prompt = (
        f"{NUM_STOREYS}-storey commercial highrise, "
        f"{BUILDING_WIDTH:.0f} m × {BUILDING_LENGTH:.0f} m footprint"
    )
    defaults = _infer_defaults(prompt)

    print("=" * 64)
    print(f"  Building type : {defaults['building_type']}")
    print(f"  Storeys       : {defaults['num_storeys']}")
    print(f"  Floor-to-floor: {defaults['floor_to_floor_height']} m")
    print("=" * 64)
    print("\n  Available features (toggle by typing the ID shown in brackets):\n")

    selected = set(defaults["default_features"])
    by_category: dict[str, list[dict]] = {}
    for f in BUILDING_FEATURES:
        by_category.setdefault(f["category"], []).append(f)

    idx = 0
    for cat, feats in by_category.items():
        print(f"  ── {cat} ──")
        for f in feats:
            idx += 1
            marker = "x" if f["id"] in selected else " "
            print(f"    [{marker}]  ID: {f['id']}")
            print(f"          {f['label']} — {f['description']}")
        print()

    print("  To toggle features, type their IDs separated by commas.")
    print("  Example: elevators,curtain_wall,core_walls")
    print("  Press Enter to accept the current selection.\n")
    user_input = input("  > ").strip()
    if user_input:
        user_toggled: list[str] = []
        for fid in [x.strip() for x in user_input.split(",")]:
            if fid in {f["id"] for f in BUILDING_FEATURES}:
                if fid in selected:
                    selected.discard(fid)
                    print(f"    - Removed: {fid}")
                else:
                    selected.add(fid)
                    user_toggled.append(fid)
                    print(f"    + Added: {fid}")
            elif fid:
                print(f"    ? Unknown feature: {fid}")

        # Resolve conflicts: user-toggled features override conflicting defaults
        if user_toggled:
            resolved = _resolve_conflicts(list(selected), user_toggled)
            removed = selected - set(resolved)
            for rid in removed:
                print(f"    ↳ Auto-removed conflicting default: {rid}")
            selected = set(resolved)

    print(f"\n  Final features: {sorted(selected)}\n")
    return sorted(selected)


def main() -> None:
    selected_features = _interactive_feature_selection()
    plan = generate_plan(features=selected_features)

    # ── Summary ──
    n_elem = len(plan["elements"])
    n_junc = len(plan["wall_junctions"])
    counts = Counter(e["element_type"] for e in plan["elements"])
    print(f"Generated plan: {n_elem} elements, {n_junc} wall junctions")
    for etype, count in sorted(counts.items()):
        print(f"  {etype:10s}: {count}")

    # ── Plan validation ──
    from validation.plan_checks import validate_plan

    result = validate_plan(plan)
    print(
        f"\nPlan validation: valid={result['valid']}, "
        f"errors={result['error_count']}, warnings={result['warning_count']}"
    )
    for issue in result["issues"]:
        print(f"  [{issue['severity']}] {issue['message']}")

    if not result["valid"]:
        print("\n✗ Plan has errors — saving JSON for inspection.")
        Path("workspace").mkdir(exist_ok=True)
        with open("workspace/highrise_plan.json", "w") as f:
            json.dump(plan, f, indent=2)
        print("  → workspace/highrise_plan.json")
        return

    # ── Build IFC ──
    print(f"\n✓ Plan valid — building IFC ({n_elem} elements) …")
    from agent.graph import run_pipeline_from_plan

    t0 = time.time()
    state = run_pipeline_from_plan(plan)
    elapsed = time.time() - t0

    ifc_path = state.get("final_ifc_path", "N/A")
    passed = state.get("validation_passed", "?")
    print(f"\nBuild complete in {elapsed:.1f} s")
    print(f"  IFC file       : {ifc_path}")
    print(f"  Validation pass: {passed}")

    # Save plan JSON alongside for reference
    Path("workspace").mkdir(exist_ok=True)
    with open("workspace/highrise_plan.json", "w") as f:
        json.dump(plan, f, indent=2)
    print("  Plan JSON      : workspace/highrise_plan.json")


if __name__ == "__main__":
    main()
