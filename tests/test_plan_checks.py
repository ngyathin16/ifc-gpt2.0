"""Tests for validation/plan_checks.py — pre-build plan validation."""
from __future__ import annotations

from validation.plan_checks import (
    check_beam_span_limits,
    check_beam_wider_than_wall,
    check_beam_window_vertical_clash,
    check_building_opening_capacity,
    check_column_wall_overlap,
    check_elevation_double_counting,
    check_elevator_requirement,
    check_minimum_dimensions,
    check_opening_consistency_across_floors,
    check_opening_spacing,
    check_openings_within_walls,
    check_roof_covers_walls,
    check_slab_covers_walls,
    check_storey_refs,
    check_top_storey_redundant_beams,
    check_wall_junctions,
    check_walls_form_closed_loops,
    validate_plan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_plan() -> dict:
    """A valid 4×3 m box house plan that should pass all checks."""
    return {
        "description": "4x3 box house",
        "storeys": [{"storey_ref": "GF", "name": "Ground Floor", "elevation": 0.0}],
        "elements": [
            {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
             "start_point": [0, 0], "end_point": [4, 0], "height": 3.0, "thickness": 0.2, "is_external": True},
            {"element_type": "wall", "wall_ref": "W2", "storey_ref": "GF",
             "start_point": [4, 0], "end_point": [4, 3], "height": 3.0, "thickness": 0.2, "is_external": True},
            {"element_type": "wall", "wall_ref": "W3", "storey_ref": "GF",
             "start_point": [4, 3], "end_point": [0, 3], "height": 3.0, "thickness": 0.2, "is_external": True},
            {"element_type": "wall", "wall_ref": "W4", "storey_ref": "GF",
             "start_point": [0, 3], "end_point": [0, 0], "height": 3.0, "thickness": 0.2, "is_external": True},
            {"element_type": "slab", "storey_ref": "GF",
             "boundary_points": [[0, 0], [4, 0], [4, 3], [0, 3]], "depth": 0.2, "elevation": 0.0, "slab_type": "FLOOR"},
            {"element_type": "door", "storey_ref": "GF", "host_wall_ref": "W1",
             "distance_along_wall": 2.0, "sill_height": 0.0, "width": 0.9, "height": 2.1},
            {"element_type": "window", "storey_ref": "GF", "host_wall_ref": "W2",
             "distance_along_wall": 1.5, "sill_height": 0.9, "width": 1.2, "height": 1.5},
            {"element_type": "roof", "storey_ref": "GF",
             "boundary_points": [[0, 0], [4, 0], [4, 3], [0, 3]], "roof_type": "FLAT", "thickness": 0.25},
        ],
        "wall_junctions": [
            {"wall_ref_1": "W1", "wall_ref_2": "W2"},
            {"wall_ref_1": "W2", "wall_ref_2": "W3"},
            {"wall_ref_1": "W3", "wall_ref_2": "W4"},
            {"wall_ref_1": "W4", "wall_ref_2": "W1"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidatePlan:
    def test_good_plan_passes(self):
        result = validate_plan(_good_plan())
        assert result["valid"] is True
        assert result["error_count"] == 0

    def test_empty_elements_passes(self):
        plan = {"storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0}], "elements": []}
        result = validate_plan(plan)
        assert result["valid"] is True


class TestWallEnclosure:
    def test_closed_loop_passes(self):
        plan = _good_plan()
        issues = check_walls_form_closed_loops(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_single_wall_fails(self):
        plan = {
            "storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0}],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [4, 0], "height": 3.0, "is_external": True},
            ],
        }
        issues = check_walls_form_closed_loops(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "exterior wall" in errors[0]["message"].lower() or "1" in errors[0]["message"]

    def test_open_polygon_fails(self):
        """Three walls that don't close — dangling endpoints."""
        plan = {
            "storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0}],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [4, 0], "height": 3.0, "is_external": True},
                {"element_type": "wall", "wall_ref": "W2", "storey_ref": "GF",
                 "start_point": [4, 0], "end_point": [4, 3], "height": 3.0, "is_external": True},
                {"element_type": "wall", "wall_ref": "W3", "storey_ref": "GF",
                 "start_point": [4, 3], "end_point": [0, 3], "height": 3.0, "is_external": True},
            ],
        }
        issues = check_walls_form_closed_loops(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "dangling" in errors[0]["message"].lower()


class TestSlabCoverage:
    def test_matching_slab_passes(self):
        plan = _good_plan()
        issues = check_slab_covers_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_tiny_slab_fails(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "slab":
                elem["boundary_points"] = [[0, 0], [1, 0], [1, 1], [0, 1]]  # 1m² vs 12m²
        issues = check_slab_covers_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1


class TestRoofCoverage:
    def test_matching_roof_passes(self):
        plan = _good_plan()
        issues = check_roof_covers_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_tiny_roof_fails(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "roof":
                elem["boundary_points"] = [[0, 0], [1, 0], [1, 1], [0, 1]]
        issues = check_roof_covers_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1


class TestOpeningsWithinWalls:
    def test_valid_openings_pass(self):
        plan = _good_plan()
        issues = check_openings_within_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_door_past_wall_end(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["distance_along_wall"] = 3.8  # 3.8 + 0.45 = 4.25 > 4.0
        issues = check_openings_within_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "exceeds" in errors[0]["message"].lower()

    def test_door_before_wall_start(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["distance_along_wall"] = 0.2  # 0.2 - 0.45 = -0.25 < 0
        issues = check_openings_within_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "before wall start" in errors[0]["message"].lower()

    def test_nonexistent_host_wall(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["host_wall_ref"] = "MISSING"
        issues = check_openings_within_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "does not exist" in errors[0]["message"].lower()

    def test_window_exceeds_wall_height(self):
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "window":
                elem["sill_height"] = 2.0
                elem["height"] = 1.5  # 2.0 + 1.5 = 3.5 > 3.0
        issues = check_openings_within_walls(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "exceeds wall height" in errors[0]["message"].lower()


class TestStoreyRefs:
    def test_valid_refs_pass(self):
        plan = _good_plan()
        issues = check_storey_refs(plan)
        assert len(issues) == 0

    def test_invalid_ref_fails(self):
        plan = _good_plan()
        plan["elements"][0]["storey_ref"] = "NONEXISTENT"
        issues = check_storey_refs(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1


class TestWallJunctions:
    def test_valid_junctions_pass(self):
        plan = _good_plan()
        issues = check_wall_junctions(plan)
        assert len(issues) == 0

    def test_bad_junction_ref(self):
        plan = _good_plan()
        plan["wall_junctions"].append({"wall_ref_1": "W1", "wall_ref_2": "MISSING"})
        issues = check_wall_junctions(plan)
        assert len(issues) >= 1


class TestMinimumDimensions:
    def test_valid_dimensions_pass(self):
        plan = _good_plan()
        issues = check_minimum_dimensions(plan)
        assert len(issues) == 0

    def test_zero_length_wall_fails(self):
        plan = _good_plan()
        plan["elements"][0]["end_point"] = [0, 0]  # same as start
        issues = check_minimum_dimensions(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "zero length" in errors[0]["message"].lower() or "near-zero" in errors[0]["message"].lower()


class TestOpeningSpacing:
    """Tests for check_opening_spacing — minimum gap & edge clearance."""

    def test_well_spaced_openings_pass(self):
        """Door and window on same wall but far apart → no errors."""
        plan = _good_plan()
        # Put both openings on W1 (4 m wall), well spaced
        # door@1.2 (w=0.9, edges 0.75–1.65), window@3.2 (w=0.8, edges 2.8–3.6)
        # gap = 2.8 - 1.65 = 1.15 m → OK
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["distance_along_wall"] = 1.2
            if elem.get("element_type") == "window":
                elem["host_wall_ref"] = "W1"
                elem["distance_along_wall"] = 3.2
                elem["width"] = 0.8
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_openings_on_different_walls_pass(self):
        """Default good plan has door on W1, window on W2 → no errors."""
        plan = _good_plan()
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_openings_too_close_on_same_wall(self):
        """Door and window nearly touching on the same wall → error."""
        plan = _good_plan()
        # Door at 1.5 (width 0.9 → right edge 1.95)
        # Window at 2.3 (width 1.2 → left edge 1.70)  → overlapping!
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["distance_along_wall"] = 1.5
            if elem.get("element_type") == "window":
                elem["host_wall_ref"] = "W1"
                elem["distance_along_wall"] = 2.3
                elem["width"] = 1.2
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert any("apart" in e["message"] or "spacing" in e["message"].lower() for e in errors)

    def test_opening_too_close_to_wall_start(self):
        """Opening placed right at the wall start → edge clearance error."""
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                elem["distance_along_wall"] = 0.45  # left edge = 0.0
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert any("wall start" in e["message"] for e in errors)

    def test_opening_too_close_to_wall_end(self):
        """Opening placed right at the wall end → edge clearance error."""
        plan = _good_plan()
        for elem in plan["elements"]:
            if elem.get("element_type") == "door":
                # W1 is 4 m, door width 0.9, right edge = 3.55 + 0.45 = 4.0
                elem["distance_along_wall"] = 3.55
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert any("wall end" in e["message"] for e in errors)

    def test_wall_too_short_for_all_openings(self):
        """Many openings crammed on a short wall → capacity error."""
        plan = _good_plan()
        # W2 is 3 m; put door + 2 windows on it
        plan["elements"].append({
            "element_type": "window", "storey_ref": "GF",
            "host_wall_ref": "W2", "distance_along_wall": 0.7,
            "sill_height": 0.9, "width": 1.0, "height": 1.2,
        })
        plan["elements"].append({
            "element_type": "window", "storey_ref": "GF",
            "host_wall_ref": "W2", "distance_along_wall": 2.3,
            "sill_height": 0.9, "width": 1.0, "height": 1.2,
        })
        # Already has window at 1.5 w=1.2 → total widths = 1.2+1.0+1.0 = 3.2
        # min_required = 3.2 + 2*0.5 + 2*0.3 = 4.8 > 3.0
        issues = check_opening_spacing(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert any("cannot fit" in e["message"] for e in errors)

    def test_single_opening_passes(self):
        """Single well-placed opening → no issues."""
        plan = {
            "storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0}],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [5, 0], "height": 3.0, "thickness": 0.2},
                {"element_type": "door", "storey_ref": "GF", "host_wall_ref": "W1",
                 "distance_along_wall": 2.5, "sill_height": 0.0, "width": 0.9, "height": 2.1},
            ],
        }
        issues = check_opening_spacing(plan)
        assert len(issues) == 0


class TestBuildingOpeningCapacity:
    """Tests for check_building_opening_capacity — perimeter-level check."""

    def test_normal_building_passes(self):
        """Standard box house with 2 openings → well within perimeter budget."""
        plan = _good_plan()
        issues = check_building_opening_capacity(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_tiny_building_with_many_openings_fails(self):
        """Tiny 2×2 m building with many large openings → exceeds perimeter ratio."""
        plan = {
            "storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0}],
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [2, 0], "height": 3.0,
                 "thickness": 0.2, "is_external": True},
                {"element_type": "wall", "wall_ref": "W2", "storey_ref": "GF",
                 "start_point": [2, 0], "end_point": [2, 2], "height": 3.0,
                 "thickness": 0.2, "is_external": True},
                {"element_type": "wall", "wall_ref": "W3", "storey_ref": "GF",
                 "start_point": [2, 2], "end_point": [0, 2], "height": 3.0,
                 "thickness": 0.2, "is_external": True},
                {"element_type": "wall", "wall_ref": "W4", "storey_ref": "GF",
                 "start_point": [0, 2], "end_point": [0, 0], "height": 3.0,
                 "thickness": 0.2, "is_external": True},
            ],
        }
        # Perimeter = 8 m, 60% = 4.8 m
        # Add openings totalling > 4.8 m
        for i in range(6):
            plan["elements"].append({
                "element_type": "window", "storey_ref": "GF",
                "host_wall_ref": f"W{(i % 4) + 1}",
                "distance_along_wall": 1.0, "sill_height": 0.9,
                "width": 1.0, "height": 1.2,
            })
        # total opening width = 6 × 1.0 = 6.0 > 4.8
        issues = check_building_opening_capacity(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert any("too small" in e["message"] or "perimeter" in e["message"] for e in errors)

    def test_no_openings_passes(self):
        """Building with no openings → no issues."""
        plan = _good_plan()
        plan["elements"] = [e for e in plan["elements"]
                            if e.get("element_type") not in ("door", "window")]
        issues = check_building_opening_capacity(plan)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# New checks (Mar 2026)
# ---------------------------------------------------------------------------

class TestElevationDoubleCounting:
    """Tests for check_elevation_double_counting."""

    def test_relative_elevation_passes(self):
        """Column with base_elevation=0 on upper floor → OK."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "column", "column_ref": "C1_F1",
                 "storey_ref": "F1", "position": [1, 1],
                 "base_elevation": 0.0, "height": 3.5},
            ],
        }
        issues = check_elevation_double_counting(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 0

    def test_absolute_elevation_fails(self):
        """Column with base_elevation == storey elevation → double-count error."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "column", "column_ref": "C1_F1",
                 "storey_ref": "F1", "position": [1, 1],
                 "base_elevation": 3.5, "height": 3.5},
            ],
        }
        issues = check_elevation_double_counting(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 1
        assert "double-count" in errors[0]["message"].lower()

    def test_ground_floor_skipped(self):
        """Elements on ground floor (elevation 0) are always skipped."""
        plan = {
            "storeys": [{"storey_ref": "GF", "name": "GF", "elevation": 0.0}],
            "elements": [
                {"element_type": "slab", "storey_ref": "GF",
                 "boundary_points": [[0, 0], [4, 0], [4, 3], [0, 3]],
                 "depth": 0.2, "elevation": 0.0},
            ],
        }
        issues = check_elevation_double_counting(plan)
        assert len(issues) == 0

    def test_beam_double_counting(self):
        """Beam elevation matching storey elevation → error."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "beam", "beam_ref": "B1_F1",
                 "storey_ref": "F1", "start_point": [0, 0],
                 "end_point": [5, 0], "elevation": 3.5},
            ],
        }
        issues = check_elevation_double_counting(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 1


class TestBeamSpanLimits:
    """Tests for check_beam_span_limits."""

    def test_short_beam_passes(self):
        plan = {
            "elements": [
                {"element_type": "beam", "beam_ref": "B1",
                 "storey_ref": "GF", "start_point": [0, 0],
                 "end_point": [10, 0]},
            ],
        }
        issues = check_beam_span_limits(plan)
        assert len(issues) == 0

    def test_long_beam_fails(self):
        plan = {
            "elements": [
                {"element_type": "beam", "beam_ref": "B1",
                 "storey_ref": "GF", "start_point": [0, 0],
                 "end_point": [50, 0]},
            ],
        }
        issues = check_beam_span_limits(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 1
        assert "50.0 m" in errors[0]["message"]


class TestElevatorRequirement:
    """Tests for check_elevator_requirement."""

    def test_low_rise_no_elevator_passes(self):
        plan = {
            "storeys": [{"storey_ref": f"F{i}", "name": f"F{i}", "elevation": i * 3.0}
                        for i in range(3)],
            "elements": [],
        }
        issues = check_elevator_requirement(plan)
        assert len(issues) == 0

    def test_highrise_no_elevator_warns(self):
        plan = {
            "storeys": [{"storey_ref": f"F{i}", "name": f"F{i}", "elevation": i * 3.5}
                        for i in range(10)],
            "elements": [],
        }
        issues = check_elevator_requirement(plan)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) == 1
        assert "elevator" in warnings[0]["message"].lower()

    def test_highrise_with_elevator_passes(self):
        plan = {
            "storeys": [{"storey_ref": f"F{i}", "name": f"F{i}", "elevation": i * 3.5}
                        for i in range(10)],
            "elements": [{"element_type": "elevator", "storey_ref": "F00"}],
        }
        issues = check_elevator_requirement(plan)
        assert len(issues) == 0


class TestColumnWallOverlap:
    """Tests for check_column_wall_overlap."""

    def test_column_away_from_wall_passes(self):
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0]},
                {"element_type": "column", "column_ref": "C1", "storey_ref": "GF",
                 "position": [5, 5]},
            ],
        }
        issues = check_column_wall_overlap(plan)
        assert len(issues) == 0

    def test_column_on_wall_warns(self):
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0]},
                {"element_type": "column", "column_ref": "C1", "storey_ref": "GF",
                 "position": [5, 0]},  # directly on the wall line
            ],
        }
        issues = check_column_wall_overlap(plan)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) >= 1
        assert "overlap" in warnings[0]["message"].lower()

    def test_column_at_wall_corner_warns(self):
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0]},
                {"element_type": "column", "column_ref": "C1", "storey_ref": "GF",
                 "position": [0, 0]},  # at the wall start
            ],
        }
        issues = check_column_wall_overlap(plan)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) >= 1


class TestOpeningConsistency:
    """Tests for check_opening_consistency_across_floors."""

    def test_uniform_windows_passes(self):
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.0},
            ],
            "elements": [
                {"element_type": "window", "storey_ref": "GF",
                 "host_wall_ref": "W1", "distance_along_wall": 2.0,
                 "width": 1.0, "height": 1.2},
                {"element_type": "window", "storey_ref": "F1",
                 "host_wall_ref": "W1_F1", "distance_along_wall": 2.0,
                 "width": 1.0, "height": 1.2},
            ],
        }
        issues = check_opening_consistency_across_floors(plan)
        assert len(issues) == 0

    def test_missing_windows_on_one_floor_warns(self):
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.0},
                {"storey_ref": "F2", "name": "F2", "elevation": 6.0},
            ],
            "elements": [
                {"element_type": "window", "storey_ref": "GF",
                 "host_wall_ref": "W1", "distance_along_wall": 2.0,
                 "width": 1.0, "height": 1.2},
                {"element_type": "window", "storey_ref": "F2",
                 "host_wall_ref": "W1_F2", "distance_along_wall": 2.0,
                 "width": 1.0, "height": 1.2},
                # F1 has no windows
            ],
        }
        issues = check_opening_consistency_across_floors(plan)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert len(warnings) >= 1
        assert "F1" in warnings[0]["message"]


# ---------------------------------------------------------------------------
# Beam-related checks (Mar 2026 – beam protrusion / clash fixes)
# ---------------------------------------------------------------------------

class TestTopStoreyRedundantBeams:
    """Tests for check_top_storey_redundant_beams."""

    def test_no_beams_on_top_storey_passes(self):
        """Plan without beams on the top storey → no errors."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "beam", "beam_ref": "B1_GF",
                 "storey_ref": "GF", "start_point": [0, 0],
                 "end_point": [5, 0], "elevation": 3.5},
                {"element_type": "roof", "storey_ref": "F1",
                 "boundary_points": [[0, 0], [5, 0], [5, 4], [0, 4]],
                 "roof_type": "FLAT", "thickness": 0.25},
            ],
        }
        issues = check_top_storey_redundant_beams(plan)
        assert len(issues) == 0

    def test_beams_on_top_storey_with_roof_fails(self):
        """Beams on the same storey as the roof → error."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "beam", "beam_ref": "B1_F1",
                 "storey_ref": "F1", "start_point": [0, 0],
                 "end_point": [5, 0], "elevation": 3.5},
                {"element_type": "beam", "beam_ref": "B2_F1",
                 "storey_ref": "F1", "start_point": [5, 0],
                 "end_point": [5, 4], "elevation": 3.5},
                {"element_type": "roof", "storey_ref": "F1",
                 "boundary_points": [[0, 0], [5, 0], [5, 4], [0, 4]],
                 "roof_type": "FLAT", "thickness": 0.25},
            ],
        }
        issues = check_top_storey_redundant_beams(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) == 2
        assert all("redundant" in e["message"] for e in errors)

    def test_beams_on_top_storey_without_roof_passes(self):
        """Beams on top storey but NO roof → no issue (might be intentional)."""
        plan = {
            "storeys": [
                {"storey_ref": "GF", "name": "GF", "elevation": 0.0},
                {"storey_ref": "F1", "name": "F1", "elevation": 3.5},
            ],
            "elements": [
                {"element_type": "beam", "beam_ref": "B1_F1",
                 "storey_ref": "F1", "start_point": [0, 0],
                 "end_point": [5, 0], "elevation": 3.5},
            ],
        }
        issues = check_top_storey_redundant_beams(plan)
        assert len(issues) == 0


class TestBeamWiderThanWall:
    """Tests for check_beam_wider_than_wall."""

    def test_beam_fits_in_wall_passes(self):
        """Beam width ≤ wall thickness → no error."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.0, "thickness": 0.25},
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "elevation": 3.0, "width": 0.2, "depth": 0.4},
            ],
        }
        issues = check_beam_wider_than_wall(plan)
        assert len(issues) == 0

    def test_beam_wider_than_wall_fails(self):
        """Beam width > wall thickness → error."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.0, "thickness": 0.25},
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "elevation": 3.0, "width": 0.30, "depth": 0.4},
            ],
        }
        issues = check_beam_wider_than_wall(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "protrude" in errors[0]["message"].lower()

    def test_beam_not_on_wall_line_passes(self):
        """Wide beam that doesn't run along a wall → no error."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.0, "thickness": 0.2},
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 5], "end_point": [10, 5],
                 "elevation": 3.0, "width": 0.5, "depth": 0.4},
            ],
        }
        issues = check_beam_wider_than_wall(plan)
        assert len(issues) == 0


class TestBeamWindowVerticalClash:
    """Tests for check_beam_window_vertical_clash."""

    def test_beam_above_windows_passes(self):
        """Beam at wall top, window well below → no clash."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.5, "thickness": 0.25},
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "elevation": 3.5, "width": 0.2, "depth": 0.4},
                {"element_type": "window", "storey_ref": "GF",
                 "host_wall_ref": "W1", "distance_along_wall": 5.0,
                 "sill_height": 0.9, "width": 1.2, "height": 1.5},
            ],
        }
        issues = check_beam_window_vertical_clash(plan)
        assert len(issues) == 0

    def test_beam_overlaps_window_fails(self):
        """Beam lowered so its range overlaps with window → error."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.5, "thickness": 0.25},
                # Beam centred at 2.0, depth 0.8 → range [1.6, 2.4]
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "elevation": 2.0, "width": 0.2, "depth": 0.8},
                # Window sill=0.9, top=2.1 → overlaps beam [1.6, 2.4]
                {"element_type": "window", "storey_ref": "GF",
                 "host_wall_ref": "W1", "distance_along_wall": 5.0,
                 "sill_height": 0.9, "width": 1.2, "height": 1.2},
            ],
        }
        issues = check_beam_window_vertical_clash(plan)
        errors = [i for i in issues if i["severity"] == "error"]
        assert len(errors) >= 1
        assert "overlaps" in errors[0]["message"].lower()

    def test_beam_on_different_wall_passes(self):
        """Beam on a different wall than the window → no clash."""
        plan = {
            "elements": [
                {"element_type": "wall", "wall_ref": "W1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "height": 3.5, "thickness": 0.25},
                {"element_type": "wall", "wall_ref": "W2", "storey_ref": "GF",
                 "start_point": [10, 0], "end_point": [10, 5],
                 "height": 3.5, "thickness": 0.25},
                # Beam on W1
                {"element_type": "beam", "beam_ref": "B1", "storey_ref": "GF",
                 "start_point": [0, 0], "end_point": [10, 0],
                 "elevation": 2.0, "width": 0.2, "depth": 0.8},
                # Window on W2
                {"element_type": "window", "storey_ref": "GF",
                 "host_wall_ref": "W2", "distance_along_wall": 2.5,
                 "sill_height": 0.9, "width": 1.2, "height": 1.2},
            ],
        }
        issues = check_beam_window_vertical_clash(plan)
        assert len(issues) == 0
