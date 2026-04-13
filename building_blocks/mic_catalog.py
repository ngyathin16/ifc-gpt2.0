"""
MiC (Modular integrated Construction) room dimension catalog.

Derived from geometry analysis of 49 individual MiC IFC modules extracted from
HSK_HSK1A_GVDC_ALL_IFC4x3.ifc — a real Hong Kong MiC housing project.
All dimensions are **measured from IFC bounding boxes** (mm in source, stored
here in metres, rounded to the nearest 5 mm).

Module types encode room functions:
  TYPE 1.x (MB) — Master Bedroom
  TYPE 2.x (BT) — Bathroom / Bathroom-plus (2B prefix = 2-bed combo)
  TYPE 3.x (LK/LD) — Living/Kitchen or Living/Dining
  TYPE 4.x (KT) — Kitchen
  TYPE 5.x (BR) — Bedroom (secondary)
  TYPE 6   (TL) — Toilet
  TYPE 7   (EMR) — E&M Room / Electrical
  TYPE 8   (RMSRR) — Refuse & Service Room
  TYPE 9   (EMR2) — E&M Room variant
  TYPE 10  (WMC) — Water Meter Closet

These dimensions follow Hong Kong Housing Authority MiC standards and
are used by the floor plan pipeline to:
  1. Classify detected rooms by label → standard MiC category
  2. Apply realistic proportions when subdividing units
  3. Validate detected room sizes against expected ranges
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MiCModuleDims:
    """Dimensions of a MiC module in metres, measured from IFC geometry."""
    category: str
    label: str
    mic_type_code: str          # e.g. "1.3_MB1L"
    width_m: float              # shorter horizontal axis (metres)
    depth_m: float              # longer horizontal axis (metres)
    height_m: float             # overall module height (metres)
    has_window: bool
    has_door: bool
    typical_door_count: int
    typical_window_count: int
    materials: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Real measured MiC module dimensions (Hong Kong residential)
# All values from IFC bounding-box extraction (mm → m, rounded to 5 mm)
# ---------------------------------------------------------------------------
MIC_CATALOG: list[MiCModuleDims] = [
    # ── Master Bedrooms — TYPE 1.x ──────────────────────────────────────
    MiCModuleDims("master_bedroom", "Master Bedroom (MB1R)", "1_MB1R",
                  2.385, 4.000, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB1L/R)", "1.3_MB1L",
                  2.385, 3.995, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB2L/R)", "1.2_MB2L",
                  2.385, 4.025, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB2L)", "1.5R_MB2L",
                  2.385, 4.025, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB3R)", "1.1_MB3R",
                  2.385, 4.025, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB3)", "1.2_MB3",
                  2.385, 4.025, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),
    MiCModuleDims("master_bedroom", "Master Bedroom (MB3L)", "1.4R_MB3L",
                  2.390, 3.990, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint", "Porcelain")),

    # ── Bathrooms — TYPE 2.x ────────────────────────────────────────────
    MiCModuleDims("bathroom", "Bathroom (BT3L/R)", "2_BT3L",
                  2.395, 5.750, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),
    MiCModuleDims("bathroom", "Bathroom (BT3R)", "2.2_BT3R",
                  2.390, 5.750, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White")),
    MiCModuleDims("bathroom", "Bathroom (BT4)", "2.1_BT4",
                  2.385, 5.750, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White")),

    # ── 2-Bed Bathroom combos — TYPE 2B-Px ──────────────────────────────
    MiCModuleDims("bathroom", "Bathroom 2B (BT1R)", "2B-P1_BT1R",
                  2.390, 6.685, 3.145, True, True, 2, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),
    MiCModuleDims("bathroom", "Bathroom 2B (BT2R)", "2B-P2_BT2R",
                  2.390, 6.685, 3.145, True, True, 2, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),
    MiCModuleDims("bathroom", "Bathroom 2B (BT1L)", "2B-P3_BT1L",
                  2.390, 6.685, 3.145, True, True, 2, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),
    MiCModuleDims("bathroom", "Bathroom 2B (BT2L)", "2B-P4_BT2L",
                  2.390, 6.685, 3.145, True, True, 2, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),

    # ── Living/Kitchen — TYPE 3.x (LK) ─────────────────────────────────
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK1L)", "3.1_LK1L",
                  2.755, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain")),
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK1L v2)", "3_LK1L",
                  2.758, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain")),
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK1L v3)", "3.4_LK1L",
                  2.756, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain")),
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK2L)", "3.2_LK2L",
                  2.853, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board")),
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK2R)", "3.3_LK2R",
                  2.853, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain")),
    MiCModuleDims("living_kitchen", "Living/Kitchen (LK1R)", "3A1_LK1R",
                  2.755, 7.213, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain", "Steel")),

    # ── Living/Dining — TYPE 3.x (LD) ──────────────────────────────────
    MiCModuleDims("living_dining", "Living/Dining (LD1L)", "3A2_LD1L",
                  2.755, 7.213, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain", "Steel")),
    MiCModuleDims("living_dining", "Living/Dining (LD2R)", "3A3_LD2R",
                  2.755, 7.213, 3.386, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Steel")),
    MiCModuleDims("living_dining", "Living/Dining (LD2L)", "3B1_LD2L",
                  2.756, 7.050, 3.395, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board")),
    MiCModuleDims("living_dining", "Living/Dining (LD1L/LD2R)", "3B2_LD1L",
                  2.755, 7.050, 3.405, True, True, 2, 2,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "Porcelain", "Steel")),

    # ── Kitchen — TYPE 4.x ──────────────────────────────────────────────
    MiCModuleDims("kitchen", "Kitchen (KT)", "4_KTL",
                  1.733, 3.270, 3.090, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board")),
    MiCModuleDims("kitchen", "Kitchen (KT v4.1)", "4.1_KTL",
                  1.733, 3.270, 3.090, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board")),

    # ── Secondary Bedrooms — TYPE 5.x ──────────────────────────────────
    MiCModuleDims("bedroom", "Bedroom (BR1)", "5_BR1",
                  2.390, 4.000, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Gypsum Board", "White Paint")),
    MiCModuleDims("bedroom", "Bedroom (BR2)", "5.1_BR2",
                  2.390, 4.025, 3.145, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "White Paint")),

    # ── Toilet — TYPE 6 ────────────────────────────────────────────────
    MiCModuleDims("toilet", "Toilet (TL)", "6_TL",
                  1.885, 3.075, 3.090, True, True, 1, 1,
                  ("Concrete", "Aluminium", "Glass", "Ceramic White", "Porcelain")),

    # ── E&M Room — TYPE 7 ──────────────────────────────────────────────
    MiCModuleDims("utility", "E&M Room (EMR1)", "7.0_EMR1",
                  2.675, 4.470, 3.000, False, True, 1, 0,
                  ("Concrete", "Plastic")),

    # ── Refuse/Service Room — TYPE 8 ───────────────────────────────────
    MiCModuleDims("utility", "Refuse Room (RMSRR)", "8_RMSRR",
                  2.070, 2.675, 3.120, False, True, 1, 0,
                  ("Concrete",)),

    # ── E&M Room variant — TYPE 9 ──────────────────────────────────────
    MiCModuleDims("utility", "E&M Room (EMR2)", "9_EMR2",
                  2.470, 2.680, 3.090, False, True, 1, 0,
                  ("Concrete", "Plastic")),

    # ── Water Meter Closet — TYPE 10 ───────────────────────────────────
    MiCModuleDims("utility", "Water Meter Closet (WMC)", "10_WMC",
                  1.150, 2.255, 3.000, False, True, 1, 0,
                  ("Concrete",)),
]

# Mapping from common room label strings to MiC categories
ROOM_LABEL_TO_CATEGORY: dict[str, str] = {
    "master bedroom": "master_bedroom",
    "master bed": "master_bedroom",
    "main bedroom": "master_bedroom",
    "bedroom": "bedroom",
    "bed": "bedroom",
    "guest bedroom": "bedroom",
    "bathroom": "bathroom",
    "bath": "bathroom",
    "ensuite": "bathroom",
    "en-suite": "bathroom",
    "shower room": "bathroom",
    "toilet": "toilet",
    "wc": "toilet",
    "lavatory": "toilet",
    "powder room": "toilet",
    "living room": "living_kitchen",
    "living": "living_kitchen",
    "lounge": "living_kitchen",
    "living/kitchen": "living_kitchen",
    "living kitchen": "living_kitchen",
    "living/dining": "living_dining",
    "living dining": "living_dining",
    "dining room": "living_dining",
    "dining": "living_dining",
    "kitchen": "kitchen",
    "kitchenette": "kitchen",
    "utility": "utility",
    "utility room": "utility",
    "store": "utility",
    "storage": "utility",
    "laundry": "utility",
    "study": "bedroom",
    "office": "bedroom",
    "balcony": "balcony",
    "corridor": "corridor",
    "hallway": "corridor",
    "hall": "corridor",
    "lobby": "corridor",
    "stairwell": "stairwell",
    "lift": "lift",
    "elevator": "lift",
    "garage": "garage",
}


def classify_room(label: str) -> str:
    """Map a detected room label to a MiC category.

    Args:
        label: Room label from VLM or OCR detection (case-insensitive).

    Returns:
        MiC category string, or "unknown" if not matched.
    """
    normalized = label.strip().lower()
    # Direct match
    if normalized in ROOM_LABEL_TO_CATEGORY:
        return ROOM_LABEL_TO_CATEGORY[normalized]
    # Substring match
    for key, cat in ROOM_LABEL_TO_CATEGORY.items():
        if key in normalized:
            return cat
    return "unknown"


def get_typical_dims(category: str) -> MiCModuleDims | None:
    """Get the first matching MiC module dimensions for a category.

    Returns None if category not found in catalog.
    """
    for mod in MIC_CATALOG:
        if mod.category == category:
            return mod
    return None


def get_all_dims_for_category(category: str) -> list[MiCModuleDims]:
    """Get all MiC module dimension variants for a category."""
    return [m for m in MIC_CATALOG if m.category == category]


def expected_size_range(category: str) -> tuple[float, float] | None:
    """Return (min_area_m2, max_area_m2) for a room category.

    Used for validation: if a detected room area falls outside this
    range, it may indicate a scale or detection error.
    """
    mods = get_all_dims_for_category(category)
    if not mods:
        return None
    areas = [m.width_m * m.depth_m for m in mods]
    return (min(areas) * 0.7, max(areas) * 1.3)  # 30% tolerance


def get_opening_defaults(category: str) -> dict[str, int]:
    """Return expected door and window counts for a room category.

    Used by plan_builder to place openings when VLM doesn't detect them.
    """
    mod = get_typical_dims(category)
    if mod is None:
        return {"doors": 1, "windows": 0}
    return {
        "doors": mod.typical_door_count,
        "windows": mod.typical_window_count,
    }


def get_by_type_code(code: str) -> MiCModuleDims | None:
    """Look up a MiC module by its type code (e.g. ``"1.3_MB1L"``)."""
    for mod in MIC_CATALOG:
        if mod.mic_type_code == code:
            return mod
    return None


# Reverse map: MiC type code → MiCModuleDims (built once at import time)
MIC_TYPE_CODE_INDEX: dict[str, MiCModuleDims] = {
    m.mic_type_code: m for m in MIC_CATALOG
}
