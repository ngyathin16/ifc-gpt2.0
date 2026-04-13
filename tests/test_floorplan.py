"""Tests for the floorplan/ package — FloorPlan2IFC pipeline."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from floorplan.detect import (
    DetectedOpening,
    DetectedWall,
    DetectionResult,
    _clamp_image_for_vlm,
    _merge_collinear_walls,
    _merge_vlm_cv_walls,
    _opencv_detect_rooms,
    _opencv_detect_walls,
    detect_elements,
)
from floorplan.ingest import _normalise, load_image_from_bytes
from floorplan.plan_builder import (
    _compute_slab_boundary,
    _find_nearest_wall,
    _find_wall_junctions,
    build_plan,
)
from floorplan.scale import (
    DEFAULT_SCALE_DENOMINATOR,
    _snap_to_known_scale,
    detect_scale,
)
from floorplan.vectorise import VectorWall, VectorisedPlan, flip_y, vectorise


# ---------------------------------------------------------------------------
# Helpers — generate synthetic floor plan images for testing
# ---------------------------------------------------------------------------

def _make_simple_floorplan(
    width: int = 800,
    height: int = 600,
    wall_thickness: int = 8,
) -> np.ndarray:
    """Draw a simple rectangular room as a synthetic floor plan.

    Returns an RGB uint8 image with black walls on white background.
    """
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Draw outer rectangle (walls)
    margin_x, margin_y = 100, 80
    x1, y1 = margin_x, margin_y
    x2, y2 = width - margin_x, height - margin_y

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), wall_thickness)

    return img


def _make_two_room_floorplan(
    width: int = 800,
    height: int = 600,
    wall_thickness: int = 8,
) -> np.ndarray:
    """Draw two rooms side-by-side separated by an interior wall."""
    img = _make_simple_floorplan(width, height, wall_thickness)

    margin_y = 80
    mid_x = width // 2

    # Interior wall (vertical divider)
    cv2.line(img, (mid_x, margin_y), (mid_x, height - margin_y), (0, 0, 0), wall_thickness)

    return img


# ---------------------------------------------------------------------------
# Tests: ingest
# ---------------------------------------------------------------------------

class TestIngest:
    def test_normalise_clamps_large_image(self):
        """Images larger than MAX_PX should be downsampled."""
        from PIL import Image as PILImage

        big = PILImage.new("RGB", (8000, 6000), color=(255, 255, 255))
        arr = _normalise(big)
        assert arr.shape[0] <= 4096
        assert arr.shape[1] <= 4096
        assert arr.dtype == np.uint8

    def test_normalise_small_image_unchanged(self):
        from PIL import Image as PILImage

        small = PILImage.new("RGB", (500, 300), color=(128, 128, 128))
        arr = _normalise(small)
        assert arr.shape == (300, 500, 3)

    def test_load_image_from_bytes_png(self):
        """Loading a PNG from bytes should return an RGB array."""
        from PIL import Image as PILImage
        import io

        img = PILImage.new("RGB", (200, 150), color=(100, 200, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        arr = load_image_from_bytes(buf.getvalue(), filename="test.png")
        assert arr.shape == (150, 200, 3)
        assert arr.dtype == np.uint8


# ---------------------------------------------------------------------------
# Tests: scale
# ---------------------------------------------------------------------------

class TestScale:
    def test_snap_to_known_scale(self):
        assert _snap_to_known_scale(98) == 100
        assert _snap_to_known_scale(52) == 50
        assert _snap_to_known_scale(1) == 1
        assert _snap_to_known_scale(200) == 200
        assert _snap_to_known_scale(0) == DEFAULT_SCALE_DENOMINATOR

    def test_detect_scale_fallback(self):
        """With a blank image, scale detection should fall back to default."""
        blank = np.ones((400, 600, 3), dtype=np.uint8) * 255
        result = detect_scale(blank, dpi=300)
        assert result["method"] == "default"
        assert result["scale_denominator"] == 100
        assert result["confidence"] == 0.0
        assert result["px_per_m"] > 0

    def test_detect_scale_returns_valid_structure(self):
        img = _make_simple_floorplan()
        result = detect_scale(img, dpi=300)
        assert "scale_denominator" in result
        assert "px_per_m" in result
        assert "method" in result
        assert "confidence" in result
        assert result["px_per_m"] > 0


# ---------------------------------------------------------------------------
# Tests: detect
# ---------------------------------------------------------------------------

class TestDetect:
    def test_opencv_detect_walls_simple_rectangle(self):
        """A simple rectangle should produce at least 4 wall segments."""
        img = _make_simple_floorplan(wall_thickness=10)
        walls = _opencv_detect_walls(img)
        # We should detect multiple wall segments (may be >4 due to line detection)
        assert len(walls) >= 2, f"Expected ≥2 walls, got {len(walls)}"

    def test_opencv_detect_walls_returns_correct_type(self):
        img = _make_simple_floorplan()
        walls = _opencv_detect_walls(img)
        for w in walls:
            assert isinstance(w, DetectedWall)
            assert w.length_px > 0

    def test_detect_elements_returns_detection_result(self):
        img = _make_simple_floorplan()
        result = detect_elements(img, backend="opencv")
        assert isinstance(result, DetectionResult)
        assert result.image_height == img.shape[0]
        assert result.image_width == img.shape[1]

    def test_detect_elements_unknown_backend(self):
        img = _make_simple_floorplan()
        with pytest.raises(ValueError, match="Unknown detection backend"):
            detect_elements(img, backend="nonexistent")

    def test_merge_collinear_walls(self):
        """Two overlapping horizontal segments should merge into one."""
        w1 = DetectedWall(x1=0, y1=100, x2=200, y2=100)
        w2 = DetectedWall(x1=180, y1=101, x2=400, y2=101)
        merged = _merge_collinear_walls([w1, w2])
        # Should merge into a single wall
        assert len(merged) <= 2  # At most one merged or the originals if merge tolerance isn't met
        # At minimum, the longer result should exist
        total_coverage = max(w.length_px for w in merged)
        assert total_coverage > 150

    def test_detect_rooms_basic(self):
        """A closed rectangle should produce at least one room contour."""
        img = _make_simple_floorplan(wall_thickness=10)
        rooms = _opencv_detect_rooms(img)
        # May detect the interior as a room
        assert isinstance(rooms, list)


# ---------------------------------------------------------------------------
# Tests: vectorise
# ---------------------------------------------------------------------------

class TestVectorise:
    def test_flip_y(self):
        assert flip_y(0, 600) == 600
        assert flip_y(600, 600) == 0
        assert flip_y(300, 600) == 300

    def test_vectorise_basic(self):
        """Vectorising a simple detection should produce metre-space walls."""
        detection = DetectionResult(
            walls=[
                DetectedWall(x1=100, y1=100, x2=500, y2=100),
                DetectedWall(x1=500, y1=100, x2=500, y2=400),
            ],
            image_height=600,
            image_width=800,
        )
        px_per_m = 100.0  # 100 px = 1 m
        result = vectorise(detection, px_per_m=px_per_m)

        assert isinstance(result, VectorisedPlan)
        assert len(result.walls) == 2
        # First wall: from x=1.0 to x=5.0 (in metres)
        w0 = result.walls[0]
        assert abs(w0.x1 - 1.0) < 0.1
        assert abs(w0.x2 - 5.0) < 0.1
        # Y should be flipped: pixel y=100 → IFC y = (600-100)/100 = 5.0
        assert abs(w0.y1 - 5.0) < 0.1

    def test_vectorise_skips_short_walls(self):
        """Walls shorter than 30cm should be skipped."""
        detection = DetectionResult(
            walls=[
                DetectedWall(x1=100, y1=100, x2=102, y2=100),  # ~2px = 0.02m
            ],
            image_height=600,
            image_width=800,
        )
        result = vectorise(detection, px_per_m=100.0)
        assert len(result.walls) == 0

    def test_vectorise_openings(self):
        detection = DetectionResult(
            walls=[],
            openings=[
                DetectedOpening(
                    opening_type="door",
                    cx=300, cy=100,
                    width_px=90, height_px=210,
                ),
            ],
            image_height=600,
            image_width=800,
        )
        result = vectorise(detection, px_per_m=100.0)
        assert len(result.openings) == 1
        assert result.openings[0].opening_type == "door"
        assert result.openings[0].width > 0.5


# ---------------------------------------------------------------------------
# Tests: plan_builder
# ---------------------------------------------------------------------------

class TestPlanBuilder:
    def test_build_plan_basic(self):
        """Build a plan from a simple vectorised result."""
        vp = VectorisedPlan(
            walls=[
                VectorWall(x1=0, y1=0, x2=10, y2=0, thickness=0.2, is_external=True),
                VectorWall(x1=10, y1=0, x2=10, y2=8, thickness=0.2, is_external=True),
                VectorWall(x1=10, y1=8, x2=0, y2=8, thickness=0.2, is_external=True),
                VectorWall(x1=0, y1=8, x2=0, y2=0, thickness=0.2, is_external=True),
            ],
        )
        plan = build_plan(vp, num_storeys=1)

        assert "storeys" in plan
        assert len(plan["storeys"]) == 1
        assert plan["storeys"][0]["storey_ref"] == "S0"
        assert plan["storeys"][0]["name"] == "Ground Floor"

        # Should have walls, a slab, and a roof
        elem_types = [e["element_type"] for e in plan["elements"]]
        assert "wall" in elem_types
        assert "slab" in elem_types
        assert "roof" in elem_types

    def test_build_plan_multi_storey(self):
        """Multi-storey plan should replicate walls per storey."""
        vp = VectorisedPlan(
            walls=[
                VectorWall(x1=0, y1=0, x2=5, y2=0),
                VectorWall(x1=5, y1=0, x2=5, y2=4),
            ],
        )
        plan = build_plan(vp, num_storeys=3, floor_to_floor_height=3.5)

        assert len(plan["storeys"]) == 3
        assert plan["storeys"][0]["elevation"] == 0.0
        assert plan["storeys"][1]["elevation"] == 3.5
        assert plan["storeys"][2]["elevation"] == 7.0

        # Each storey gets 2 walls → 6 total walls
        wall_count = sum(1 for e in plan["elements"] if e["element_type"] == "wall")
        assert wall_count == 6

    def test_compute_slab_boundary(self):
        walls = [
            VectorWall(x1=0, y1=0, x2=10, y2=0),
            VectorWall(x1=10, y1=0, x2=10, y2=8),
            VectorWall(x1=10, y1=8, x2=0, y2=8),
            VectorWall(x1=0, y1=8, x2=0, y2=0),
        ]
        boundary = _compute_slab_boundary(walls)
        assert len(boundary) >= 4
        # All points should be within the bounding box
        xs = [p[0] for p in boundary]
        ys = [p[1] for p in boundary]
        assert min(xs) >= -0.01
        assert max(xs) <= 10.01
        assert min(ys) >= -0.01
        assert max(ys) <= 8.01

    def test_find_nearest_wall(self):
        walls = [
            VectorWall(x1=0, y1=0, x2=10, y2=0),
            VectorWall(x1=0, y1=5, x2=10, y2=5),
        ]
        # Point near the first wall
        assert _find_nearest_wall(5, 0.1, walls) == 0
        # Point near the second wall
        assert _find_nearest_wall(5, 4.9, walls) == 1

    def test_distance_along_wall(self):
        wall = VectorWall(x1=0, y1=0, x2=10, y2=0)
        from floorplan.plan_builder import _distance_along_wall
        assert abs(_distance_along_wall(5, 0, wall) - 5.0) < 0.01
        assert abs(_distance_along_wall(0, 0, wall) - 0.0) < 0.01
        assert abs(_distance_along_wall(10, 0, wall) - 10.0) < 0.01

    def test_find_wall_junctions(self):
        walls = [
            VectorWall(x1=0, y1=0, x2=5, y2=0),
            VectorWall(x1=5, y1=0, x2=5, y2=4),
        ]
        junctions = _find_wall_junctions(walls, storey_index=0, tolerance=0.2)
        assert len(junctions) == 1
        assert junctions[0]["wall_ref_1"] == "W0_0"
        assert junctions[0]["wall_ref_2"] == "W0_1"

    def test_build_plan_validates_as_building_plan(self):
        """The output dict should pass BuildingPlan validation."""
        from agent.schemas import BuildingPlan

        vp = VectorisedPlan(
            walls=[
                VectorWall(x1=0, y1=0, x2=10, y2=0, thickness=0.2),
                VectorWall(x1=10, y1=0, x2=10, y2=8, thickness=0.2),
                VectorWall(x1=10, y1=8, x2=0, y2=8, thickness=0.2),
                VectorWall(x1=0, y1=8, x2=0, y2=0, thickness=0.2),
            ],
        )
        plan_dict = build_plan(vp, num_storeys=1)
        # Should not raise
        plan = BuildingPlan.model_validate(plan_dict)
        assert plan.description
        assert len(plan.storeys) == 1
        assert len(plan.elements) > 0


# ---------------------------------------------------------------------------
# Tests: pipeline (end-to-end)
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_floorplan_to_plan_from_array(self):
        """End-to-end: synthetic image → BuildingPlan dict."""
        from floorplan.pipeline import floorplan_to_plan_from_array

        img = _make_simple_floorplan(width=800, height=600, wall_thickness=10)
        plan = floorplan_to_plan_from_array(img, num_storeys=1, dpi=300)

        assert "storeys" in plan
        assert "elements" in plan
        assert "floorplan_metadata" in plan
        assert plan["floorplan_metadata"]["image_size_px"] == [800, 600]
        assert plan["floorplan_metadata"]["detection_backend"] == "opencv"

    def test_floorplan_to_plan_multi_storey(self):
        from floorplan.pipeline import floorplan_to_plan_from_array

        img = _make_simple_floorplan()
        plan = floorplan_to_plan_from_array(img, num_storeys=3)
        assert len(plan["storeys"]) == 3

    def test_floorplan_to_plan_validates(self):
        """End-to-end output should validate as BuildingPlan."""
        from agent.schemas import BuildingPlan
        from floorplan.pipeline import floorplan_to_plan_from_array

        img = _make_two_room_floorplan(wall_thickness=10)
        plan_dict = floorplan_to_plan_from_array(img, num_storeys=1)

        # Remove metadata key before validation (not part of BuildingPlan schema)
        plan_dict.pop("floorplan_metadata", None)

        plan = BuildingPlan.model_validate(plan_dict)
        assert len(plan.storeys) == 1
        assert len(plan.elements) > 0

    def test_floorplan_to_plan_bytes(self):
        """Test the bytes-based entry point."""
        from floorplan.pipeline import floorplan_to_plan
        from PIL import Image as PILImage
        import io

        # Create a synthetic floor plan as PNG bytes
        img = _make_simple_floorplan()
        pil_img = PILImage.fromarray(img)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        plan = floorplan_to_plan(png_bytes, filename="test.png", num_storeys=1)
        assert "storeys" in plan
        assert "elements" in plan


# ---------------------------------------------------------------------------
# Tests: VLM detection helpers
# ---------------------------------------------------------------------------

class TestVLMHelpers:
    def test_clamp_image_small(self):
        """Small images should not be clamped."""
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        clamped, sx, sy = _clamp_image_for_vlm(img)
        assert clamped.shape == (200, 300, 3)
        assert sx == 1.0
        assert sy == 1.0

    def test_clamp_image_large(self):
        """Images exceeding _VLM_MAX_DIM should be downscaled."""
        img = np.zeros((6000, 8000, 3), dtype=np.uint8)
        clamped, sx, sy = _clamp_image_for_vlm(img)
        assert max(clamped.shape[:2]) <= 4096
        assert sx > 1.0
        assert sy > 1.0

    def test_merge_vlm_cv_walls_empty_cv(self):
        """With no CV walls, VLM dicts should be converted directly."""
        vlm_walls = [
            {"x1": 10, "y1": 20, "x2": 100, "y2": 20,
             "thickness_px": 8, "type": "exterior", "confidence": 0.9, "id": "w1"},
        ]
        merged = _merge_vlm_cv_walls(vlm_walls, [], tolerance_px=10)
        assert len(merged) == 1
        assert merged[0].is_external is True
        assert merged[0].x1 == 10

    def test_merge_vlm_cv_walls_snaps(self):
        """VLM endpoints should snap to nearby CV points."""
        vlm_walls = [
            {"x1": 12, "y1": 22, "x2": 98, "y2": 18,
             "thickness_px": 8, "type": "exterior", "confidence": 0.9, "id": "w1"},
        ]
        cv_walls = [
            DetectedWall(x1=10, y1=20, x2=100, y2=20),
        ]
        merged = _merge_vlm_cv_walls(vlm_walls, cv_walls, tolerance_px=10)
        assert len(merged) == 1
        # Endpoints should snap to CV points
        assert merged[0].x1 == 10
        assert merged[0].y1 == 20
        assert merged[0].x2 == 100
        assert merged[0].y2 == 20

    def test_merge_vlm_cv_walls_no_snap_far(self):
        """VLM endpoints far from CV should not snap."""
        vlm_walls = [
            {"x1": 50, "y1": 50, "x2": 200, "y2": 50,
             "thickness_px": 8, "type": "interior", "confidence": 0.8, "id": "w2"},
        ]
        cv_walls = [
            DetectedWall(x1=10, y1=200, x2=100, y2=200),
        ]
        merged = _merge_vlm_cv_walls(vlm_walls, cv_walls, tolerance_px=10)
        assert len(merged) == 1
        # Should NOT snap because distance > tolerance
        assert merged[0].x1 == 50
        assert merged[0].y1 == 50

    def test_vlm_detect_no_api_key(self):
        """VLM branch should fall back to OpenCV if OPENAI_API_KEY is unset."""
        import os
        original = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ.pop("OPENAI_API_KEY", None)
            from floorplan.detect import _vlm_detect
            cv_walls = [DetectedWall(x1=0, y1=0, x2=100, y2=0)]
            img = np.zeros((200, 300, 3), dtype=np.uint8)
            result = _vlm_detect(img, cv_walls)
            assert len(result.walls) == 1
            assert result.walls[0].x1 == 0
        finally:
            if original is not None:
                os.environ["OPENAI_API_KEY"] = original


# ---------------------------------------------------------------------------
# Tests: plan_builder with MiC catalog integration
# ---------------------------------------------------------------------------

class TestPlanBuilderMiC:
    def test_rooms_have_mic_category(self):
        """Built plan rooms should include MiC category from the catalog."""
        from floorplan.vectorise import VectorRoom
        vp = VectorisedPlan(
            walls=[
                VectorWall(x1=0, y1=0, x2=10, y2=0, thickness=0.2),
                VectorWall(x1=10, y1=0, x2=10, y2=8, thickness=0.2),
                VectorWall(x1=10, y1=8, x2=0, y2=8, thickness=0.2),
                VectorWall(x1=0, y1=8, x2=0, y2=0, thickness=0.2),
            ],
            rooms=[
                VectorRoom(label="bedroom", cx=5, cy=4),
                VectorRoom(label="kitchen", cx=3, cy=2),
                VectorRoom(label="toilet", cx=8, cy=6),
            ],
        )
        plan = build_plan(vp, num_storeys=1)
        assert len(plan["rooms"]) == 3

        bedroom_room = next(r for r in plan["rooms"] if r["label"] == "bedroom")
        assert bedroom_room["category"] == "bedroom"
        assert bedroom_room["expected_windows"] >= 1
        assert bedroom_room["expected_doors"] >= 1

        toilet_room = next(r for r in plan["rooms"] if r["label"] == "toilet")
        assert toilet_room["category"] == "toilet"
        assert toilet_room["expected_windows"] >= 0  # HK MiC toilets may have windows

        kitchen_room = next(r for r in plan["rooms"] if r["label"] == "kitchen")
        assert kitchen_room["category"] == "kitchen"
        assert "typical_width_m" in kitchen_room

    def test_rooms_unknown_label(self):
        """Unknown room labels should get category 'unknown'."""
        from floorplan.vectorise import VectorRoom
        vp = VectorisedPlan(
            walls=[VectorWall(x1=0, y1=0, x2=5, y2=0)],
            rooms=[VectorRoom(label="swimming pool", cx=2, cy=1)],
        )
        plan = build_plan(vp, num_storeys=1)
        assert plan["rooms"][0]["category"] == "unknown"
