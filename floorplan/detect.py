"""
Element detection from floor plan images.

Two-branch architecture:
  Branch A (VLM): Semantic understanding — room types, element classification
  Branch B (OpenCV): Geometric precision — wall lines, contours

The detect module exposes a pluggable backend so a future YOLO model can
replace the VLM branch without changing the downstream pipeline.
"""
from __future__ import annotations

import base64
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# VLM configuration
_PROMPTS_DIR = Path(__file__).parent / "prompts"
_VLM_MAX_DIM = 4096  # GUARDRAIL G-15: clamp image before VLM


# ---------------------------------------------------------------------------
# Detection result data classes (pixel-space)
# ---------------------------------------------------------------------------

@dataclass
class DetectedWall:
    """A wall segment in pixel coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float
    thickness_px: float = 8.0
    is_external: bool = True

    @property
    def length_px(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)


@dataclass
class DetectedOpening:
    """A door or window detected along a wall."""
    opening_type: Literal["door", "window"]
    cx: float  # centre x in pixels
    cy: float  # centre y in pixels
    width_px: float
    height_px: float  # for windows: sill-to-head; for doors: full height


@dataclass
class DetectedRoom:
    """A labelled room region."""
    label: str  # e.g. "Living Room", "Kitchen"
    cx: float
    cy: float
    contour_px: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class DetectedColumn:
    """A structural column."""
    cx: float
    cy: float
    size_px: float = 6.0


@dataclass
class DetectionResult:
    """Aggregated detection output (all in pixel space)."""
    walls: list[DetectedWall] = field(default_factory=list)
    openings: list[DetectedOpening] = field(default_factory=list)
    rooms: list[DetectedRoom] = field(default_factory=list)
    columns: list[DetectedColumn] = field(default_factory=list)
    image_height: int = 0
    image_width: int = 0


# ---------------------------------------------------------------------------
# Branch B: OpenCV geometric detection
# ---------------------------------------------------------------------------

def _opencv_detect_walls(
    image: np.ndarray,
    min_line_length: int | None = None,
    max_line_gap: int = 10,
    canny_low: int = 50,
    canny_high: int = 150,
    hough_threshold: int = 60,
) -> list[DetectedWall]:
    """Detect wall line segments using Canny + HoughLinesP.

    Args:
        image: RGB uint8 array.

    Returns:
        List of DetectedWall in pixel coordinates.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    if min_line_length is None:
        min_line_length = max(30, int(min(h, w) * 0.04))

    # Adaptive threshold for cleaner binary
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_low, canny_high)

    # Dilate edges slightly to bridge small gaps
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=hough_threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    if lines is None:
        return []

    walls: list[DetectedWall] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Only keep near-horizontal or near-vertical lines (walls)
        angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
        is_horizontal = angle < 15 or angle > 165
        is_vertical = 75 < angle < 105
        if is_horizontal or is_vertical:
            walls.append(DetectedWall(
                x1=float(x1), y1=float(y1),
                x2=float(x2), y2=float(y2),
            ))

    # Merge collinear overlapping segments
    walls = _merge_collinear_walls(walls)

    return walls


def _merge_collinear_walls(
    walls: list[DetectedWall],
    angle_tol: float = 10.0,
    dist_tol: float = 15.0,
    overlap_tol: float = 20.0,
) -> list[DetectedWall]:
    """Merge wall segments that are approximately collinear and overlapping."""
    if not walls:
        return walls

    merged: list[DetectedWall] = []
    used = [False] * len(walls)

    for i in range(len(walls)):
        if used[i]:
            continue
        seg = walls[i]
        x1, y1, x2, y2 = seg.x1, seg.y1, seg.x2, seg.y2

        for j in range(i + 1, len(walls)):
            if used[j]:
                continue
            other = walls[j]
            # Check if collinear
            ang_i = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
            ang_j = math.degrees(math.atan2(other.y2 - other.y1, other.x2 - other.x1)) % 180
            if abs(ang_i - ang_j) > angle_tol and abs(ang_i - ang_j - 180) > angle_tol:
                continue

            # Check perpendicular distance
            mid_x = (other.x1 + other.x2) / 2
            mid_y = (other.y1 + other.y2) / 2
            line_len = math.hypot(x2 - x1, y2 - y1)
            if line_len < 1:
                continue
            perp_dist = abs((y2 - y1) * mid_x - (x2 - x1) * mid_y + x2 * y1 - y2 * x1) / line_len
            if perp_dist > dist_tol:
                continue

            # Check overlap along the line direction
            # Project all 4 endpoints onto the line direction
            dx, dy = (x2 - x1) / line_len, (y2 - y1) / line_len
            projs = sorted([
                dx * (x1 - x1) + dy * (y1 - y1),
                dx * (x2 - x1) + dy * (y2 - y1),
                dx * (other.x1 - x1) + dy * (other.y1 - y1),
                dx * (other.x2 - x1) + dy * (other.y2 - y1),
            ])
            # Gap between the two inner projections vs the two outer
            if projs[2] - projs[1] > overlap_tol:
                continue

            # Merge: extend to cover both segments
            all_pts = [(x1, y1), (x2, y2), (other.x1, other.y1), (other.x2, other.y2)]
            proj_vals = [dx * (px - x1) + dy * (py - y1) for px, py in all_pts]
            min_idx = proj_vals.index(min(proj_vals))
            max_idx = proj_vals.index(max(proj_vals))
            x1, y1 = all_pts[min_idx]
            x2, y2 = all_pts[max_idx]
            used[j] = True

        merged.append(DetectedWall(x1=x1, y1=y1, x2=x2, y2=y2))
        used[i] = True

    return merged


def _opencv_detect_rooms(image: np.ndarray) -> list[DetectedRoom]:
    """Detect room contours from the floor plan.

    Uses adaptive thresholding and contour detection to find enclosed
    regions that likely represent rooms.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # Threshold to get walls as black regions
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Invert so walls are white, background is black
    inv = cv2.bitwise_not(binary)

    # Close small gaps in walls
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(inv, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours of enclosed regions (rooms)
    contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    rooms: list[DetectedRoom] = []
    min_area = h * w * 0.002  # Minimum 0.2% of image area
    max_area = h * w * 0.5    # Maximum 50% of image area

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        # Approximate contour to reduce points
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        contour_pts = [(float(p[0][0]), float(p[0][1])) for p in approx]

        rooms.append(DetectedRoom(
            label="Room",
            cx=cx,
            cy=cy,
            contour_px=contour_pts,
        ))

    return rooms


# ---------------------------------------------------------------------------
# VLM JSON schema for structured output
# ---------------------------------------------------------------------------

VLM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "walls": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "x1": {"type": "number"}, "y1": {"type": "number"},
                "x2": {"type": "number"}, "y2": {"type": "number"},
                "thickness_px": {"type": "number"},
                "type": {"type": "string", "enum": ["exterior", "interior"]},
                "confidence": {"type": "number"},
            },
            "required": ["id", "x1", "y1", "x2", "y2", "thickness_px", "confidence"],
            "additionalProperties": False,
        }},
        "openings": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["door", "window"]},
                "wall_id": {"type": "string"},
                "x": {"type": "number"}, "y": {"type": "number"},
                "width_px": {"type": "number"},
                "confidence": {"type": "number"},
            },
            "required": ["type", "wall_id", "x", "y", "width_px", "confidence"],
            "additionalProperties": False,
        }},
        "rooms": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "centroid_x": {"type": "number"},
                "centroid_y": {"type": "number"},
                "confidence": {"type": "number"},
            },
            "required": ["label", "centroid_x", "centroid_y", "confidence"],
            "additionalProperties": False,
        }},
        "columns": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "cx": {"type": "number"}, "cy": {"type": "number"},
                "width_px": {"type": "number"}, "depth_px": {"type": "number"},
                "confidence": {"type": "number"},
            },
            "required": ["cx", "cy", "confidence"],
            "additionalProperties": False,
        }},
    },
    "required": ["walls", "openings", "rooms", "columns"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Branch A: VLM semantic detection
# ---------------------------------------------------------------------------

def _clamp_image_for_vlm(img: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Clamp image to _VLM_MAX_DIM and return (clamped, scale_x, scale_y)."""
    h, w = img.shape[:2]
    if max(h, w) <= _VLM_MAX_DIM:
        return img, 1.0, 1.0
    scale = _VLM_MAX_DIM / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, w / new_w, h / new_h


def _call_vlm(b64_png: str, img_w: int, img_h: int) -> dict:
    """Call the VLM API with exponential backoff (GUARDRAIL G-17)."""
    from openai import OpenAI

    system_prompt = ""
    user_prompt_tmpl = ""
    sys_path = _PROMPTS_DIR / "detect_system.txt"
    usr_path = _PROMPTS_DIR / "detect_user.txt"
    if sys_path.exists():
        system_prompt = sys_path.read_text()
    if usr_path.exists():
        user_prompt_tmpl = usr_path.read_text()

    user_text = (
        user_prompt_tmpl
        .replace("{{W}}", str(img_w))
        .replace("{{H}}", str(img_h))
    )

    client = OpenAI()
    delays = [2, 4, 8]
    last_err: Exception | None = None

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="gpt-5.4-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{b64_png}",
                            "detail": "high",
                        }},
                    ]},
                ],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "FloorPlanDetection",
                    "schema": VLM_SCHEMA,
                    "strict": True,
                }},
                max_tokens=8192,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            last_err = e
            logger.warning("VLM call attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(delays[attempt])

    logger.error("VLM detection failed after 3 retries: %s", last_err)
    return {"walls": [], "openings": [], "rooms": [], "columns": []}


def _merge_vlm_cv_walls(
    vlm_walls: list[dict],
    cv_walls: list[DetectedWall],
    tolerance_px: float = 10.0,
) -> list[DetectedWall]:
    """Snap VLM wall endpoints to nearest OpenCV line within tolerance."""
    if not cv_walls:
        # Convert VLM dicts to DetectedWall
        return [
            DetectedWall(
                x1=w["x1"], y1=w["y1"], x2=w["x2"], y2=w["y2"],
                thickness_px=w.get("thickness_px", 8.0),
                is_external=w.get("type", "interior") == "exterior",
            )
            for w in vlm_walls
        ]

    cv_pts = [(w.x1, w.y1) for w in cv_walls] + [(w.x2, w.y2) for w in cv_walls]

    merged: list[DetectedWall] = []
    for wall in vlm_walls:
        x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]

        # Snap each endpoint to nearest CV point
        for px_attr, py_attr in [("x1", "y1"), ("x2", "y2")]:
            px, py = wall[px_attr], wall[py_attr]
            dists = [math.hypot(px - cx, py - cy) for cx, cy in cv_pts]
            min_dist = min(dists)
            if min_dist <= tolerance_px:
                idx = dists.index(min_dist)
                if px_attr == "x1":
                    x1, y1 = cv_pts[idx]
                else:
                    x2, y2 = cv_pts[idx]

        merged.append(DetectedWall(
            x1=x1, y1=y1, x2=x2, y2=y2,
            thickness_px=wall.get("thickness_px", 8.0),
            is_external=wall.get("type", "interior") == "exterior",
        ))

    return merged


def _vlm_detect(
    image: np.ndarray,
    opencv_walls: list[DetectedWall],
) -> DetectionResult:
    """VLM-based semantic detection merged with OpenCV geometry.

    Calls gpt-5.4-pro vision API to detect walls, openings, rooms, and columns.
    VLM wall endpoints are snapped to nearest OpenCV-detected lines.
    Falls back to pure OpenCV results if VLM is unavailable.
    """
    h, w = image.shape[:2]

    # Check if VLM is available (needs OPENAI_API_KEY)
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set; VLM detection unavailable, using OpenCV only")
        return DetectionResult(walls=opencv_walls)

    # Clamp image for VLM (GUARDRAIL G-15)
    vlm_img, scale_x, scale_y = _clamp_image_for_vlm(image)
    vlm_h, vlm_w = vlm_img.shape[:2]

    # Encode to PNG base64
    _, buf = cv2.imencode(".png", cv2.cvtColor(vlm_img, cv2.COLOR_RGB2BGR))
    b64 = base64.b64encode(buf.tobytes()).decode()

    # Call VLM
    vlm_result = _call_vlm(b64, vlm_w, vlm_h)

    # Scale VLM coordinates back to original image space
    for vw in vlm_result.get("walls", []):
        vw["x1"] *= scale_x
        vw["y1"] *= scale_y
        vw["x2"] *= scale_x
        vw["y2"] *= scale_y
        vw["thickness_px"] *= (scale_x + scale_y) / 2
    for o in vlm_result.get("openings", []):
        o["x"] *= scale_x
        o["y"] *= scale_y
        o["width_px"] *= scale_x
    for r in vlm_result.get("rooms", []):
        r["centroid_x"] *= scale_x
        r["centroid_y"] *= scale_y
    for c in vlm_result.get("columns", []):
        c["cx"] *= scale_x
        c["cy"] *= scale_y

    # Merge VLM walls with OpenCV walls
    merged_walls = _merge_vlm_cv_walls(
        vlm_result.get("walls", []), opencv_walls,
    )

    # Convert VLM openings
    openings: list[DetectedOpening] = []
    for o in vlm_result.get("openings", []):
        default_h = 210 if o["type"] == "door" else 120
        openings.append(DetectedOpening(
            opening_type=o["type"],
            cx=o["x"],
            cy=o["y"],
            width_px=o["width_px"],
            height_px=o.get("height_px", default_h),
        ))

    # Convert VLM rooms
    rooms: list[DetectedRoom] = []
    for r in vlm_result.get("rooms", []):
        rooms.append(DetectedRoom(
            label=r["label"],
            cx=r["centroid_x"],
            cy=r["centroid_y"],
        ))

    # Convert VLM columns
    columns: list[DetectedColumn] = []
    for c in vlm_result.get("columns", []):
        columns.append(DetectedColumn(
            cx=c["cx"],
            cy=c["cy"],
            size_px=c.get("width_px", 6.0),
        ))

    return DetectionResult(
        walls=merged_walls if merged_walls else opencv_walls,
        openings=openings,
        rooms=rooms,
        columns=columns,
        image_height=h,
        image_width=w,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_elements(
    image: np.ndarray,
    backend: Literal["opencv", "vlm", "yolo"] = "opencv",
) -> DetectionResult:
    """Detect architectural elements in a floor plan image.

    Args:
        image: RGB uint8 numpy array (H, W, 3).
        backend: Detection backend to use.
            - "opencv": Pure OpenCV (HoughLinesP + contours). Default.
            - "vlm": VLM semantic + OpenCV geometric merge (v2).
            - "yolo": Fine-tuned YOLO model (v2 upgrade).

    Returns:
        DetectionResult with all detected elements in pixel coordinates.
    """
    h, w = image.shape[:2]

    # Branch B: OpenCV geometric detection (always runs)
    opencv_walls = _opencv_detect_walls(image)
    opencv_rooms = _opencv_detect_rooms(image)

    if backend == "opencv":
        result = DetectionResult(
            walls=opencv_walls,
            rooms=opencv_rooms,
            image_height=h,
            image_width=w,
        )
    elif backend == "vlm":
        result = _vlm_detect(image, opencv_walls)
        # Use VLM rooms if available (they have proper labels); fall back to CV rooms
        if not result.rooms:
            result.rooms = opencv_rooms
        result.image_height = h
        result.image_width = w
    elif backend == "yolo":
        # Future: call fine-tuned YOLO model
        logger.warning("YOLO backend not yet implemented; falling back to OpenCV")
        result = DetectionResult(
            walls=opencv_walls,
            rooms=opencv_rooms,
            image_height=h,
            image_width=w,
        )
    else:
        raise ValueError(f"Unknown detection backend: {backend}")

    logger.info(
        "Detected: %d walls, %d rooms, %d openings, %d columns",
        len(result.walls), len(result.rooms),
        len(result.openings), len(result.columns),
    )
    return result
