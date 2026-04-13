"""
Clarify node: expands an ambiguous prompt into a feature-enriched description.

Supports an optional ``selected_features`` list in the pipeline state so the
frontend can present a feature menu and pass the user's choices to the plan
node.  When no features are explicitly selected, the node infers sensible
defaults based on building type and storey count extracted from the prompt.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from building_blocks.bsdd import (
    COMMON_PSET_MAP,
    FALLBACK_PSET_PROPERTIES,
    _FEATURE_TO_IFC_CLASSES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature catalogue — the frontend reads this via GET /api/features
# ---------------------------------------------------------------------------

BUILDING_FEATURES: list[dict[str, Any]] = [
    # ── Structure ──
    {
        "id": "columns",
        "category": "Structure",
        "label": "Structural columns",
        "description": "Reinforced concrete or steel columns on a regular grid.",
        "default_for": ["commercial", "highrise", "mixed-use"],
    },
    {
        "id": "beams",
        "category": "Structure",
        "label": "Perimeter & transfer beams",
        "description": "Beams connecting columns along the building perimeter and at transfer levels.",
        "default_for": ["commercial", "highrise"],
    },
    {
        "id": "core_walls",
        "category": "Structure",
        "label": "Structural core walls",
        "description": "Shear-wall core around stairs/elevators for lateral stability.",
        "default_for": ["highrise"],
    },
    # ── Facade ──
    {
        "id": "exterior_walls",
        "category": "Facade",
        "label": "Exterior walls with windows",
        "description": "Perimeter walls with punched window openings on every floor.",
        "default_for": ["residential", "commercial", "mixed-use", "highrise"],
        "conflicts_with": ["curtain_wall"],
    },
    {
        "id": "curtain_wall",
        "category": "Facade",
        "label": "Curtain wall glazing",
        "description": "Full-height glazed facade panels (replaces punched windows).",
        "default_for": [],
        "conflicts_with": ["exterior_walls"],
    },
    # ── Vertical circulation ──
    {
        "id": "stairs",
        "category": "Vertical Circulation",
        "label": "Staircases",
        "description": "Fire-rated stair cores with landings.",
        "default_for": ["residential", "commercial", "mixed-use", "highrise"],
    },
    {
        "id": "elevators",
        "category": "Vertical Circulation",
        "label": "Elevator shafts",
        "description": "Elevator shafts within the building core.",
        "default_for": ["commercial", "highrise", "mixed-use"],
    },
    {
        "id": "railings",
        "category": "Vertical Circulation",
        "label": "Stair railings",
        "description": "Handrails along staircases.",
        "default_for": ["residential", "commercial", "mixed-use", "highrise"],
    },
    # ── Roof ──
    {
        "id": "flat_roof",
        "category": "Roof",
        "label": "Flat roof",
        "description": "Flat concrete roof slab.",
        "default_for": ["commercial", "highrise", "mixed-use"],
        "conflicts_with": ["pitched_roof"],
    },
    {
        "id": "pitched_roof",
        "category": "Roof",
        "label": "Pitched / gable roof",
        "description": "Sloped roof with ridge line.",
        "default_for": ["residential"],
        "conflicts_with": ["flat_roof"],
    },
    # ── Interior ──
    {
        "id": "interior_partitions",
        "category": "Interior",
        "label": "Interior partition walls",
        "description": "Internal walls dividing the floor plate into rooms/zones.",
        "default_for": ["residential"],
        "conflicts_with": ["open_plan"],
    },
    {
        "id": "open_plan",
        "category": "Interior",
        "label": "Open-plan floors",
        "description": "No interior partitions — open office / retail layout.",
        "default_for": ["commercial", "highrise"],
        "conflicts_with": ["interior_partitions"],
    },
    # ── Ground floor ──
    {
        "id": "entrance_doors",
        "category": "Ground Floor",
        "label": "Entrance doors",
        "description": "Main entrance doors on the ground floor.",
        "default_for": ["residential", "commercial", "mixed-use", "highrise"],
    },
    {
        "id": "lobby",
        "category": "Ground Floor",
        "label": "Lobby / reception area",
        "description": "Dedicated lobby space with double-height entrance.",
        "default_for": ["commercial", "highrise"],
    },
    # ── Slabs ──
    {
        "id": "floor_slabs",
        "category": "Structure",
        "label": "Floor slabs",
        "description": "Concrete floor slabs on every storey.",
        "default_for": ["residential", "commercial", "mixed-use", "highrise"],
    },
    {
        "id": "footings",
        "category": "Structure",
        "label": "Foundation footings",
        "description": "Concrete pad footings under each column at ground level.",
        "default_for": ["highrise"],
    },
    # ── Facade extras ──
    {
        "id": "balconies",
        "category": "Facade",
        "label": "Balconies",
        "description": "Cantilevered concrete slab balconies with safety railings on every residential floor.",
        "default_for": ["residential", "highrise"],
    },
    {
        "id": "parapets",
        "category": "Roof",
        "label": "Roof parapets",
        "description": "Low perimeter walls around the roof edge for safety and weather protection.",
        "default_for": ["commercial", "highrise", "mixed-use"],
    },
    # ── Finishes (derived from MiC material analysis) ──
    {
        "id": "suspended_ceilings",
        "category": "Finishes",
        "label": "Suspended ceilings",
        "description": "Aluminium tile suspended ceilings in bathrooms and wet areas (from MiC bathroom modules).",
        "default_for": [],
    },
    {
        "id": "floor_finishes",
        "category": "Finishes",
        "label": "Floor finishes",
        "description": "Homogeneous tile floor finishes in habitable rooms (from MiC module specifications).",
        "default_for": [],
    },
    # ── Accessibility ──
    {
        "id": "accessibility_ramps",
        "category": "Ground Floor",
        "label": "Accessibility ramps",
        "description": "Wheelchair-accessible ramps at building entrances (1:12 gradient).",
        "default_for": ["commercial", "highrise", "mixed-use"],
    },
    # ── MiC / Prefabrication ──
    {
        "id": "bathroom_pods",
        "category": "Interior",
        "label": "Bathroom pods",
        "description": "Pre-fabricated MiC bathroom modules (~2.4 m × 5.8 m) with walls, door, ceiling, and floor finishes.",
        "default_for": ["residential", "highrise"],
        "conflicts_with": ["open_plan"],
    },
    {
        "id": "service_rooms",
        "category": "Interior",
        "label": "Service / utility rooms",
        "description": "Dedicated E&M, refuse, and water-meter rooms per floor (from MiC TYPE 7–10 modules).",
        "default_for": [],
        "conflicts_with": ["open_plan"],
    },
]


# Lookup: feature id → feature dict
_FEATURE_MAP: dict[str, dict[str, Any]] = {f["id"]: f for f in BUILDING_FEATURES}


def _resolve_conflicts(
    selected: list[str],
    user_chosen: list[str],
) -> list[str]:
    """Remove default features that conflict with explicit user choices.

    When a user explicitly picks a feature, any mutually-exclusive feature
    that was only present as a default is dropped.  User choices always win.
    """
    user_set = set(user_chosen)
    # Collect every feature id that conflicts with a user-chosen feature
    blocked: set[str] = set()
    for fid in user_set:
        feat = _FEATURE_MAP.get(fid)
        if feat:
            for cid in feat.get("conflicts_with", []):
                # Only block if the conflicting feature was NOT also
                # explicitly chosen by the user (user picks both = keep both)
                if cid not in user_set:
                    blocked.add(cid)
    return [fid for fid in selected if fid not in blocked]


# ---------------------------------------------------------------------------
# Heuristic extractors
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "residential": ["house", "home", "residential", "apartment", "flat", "dwelling", "villa"],
    "commercial": ["office", "commercial", "workplace", "co-working"],
    "highrise": ["highrise", "high-rise", "tower", "skyscraper", "tall building"],
    "mixed-use": ["mixed-use", "mixed use", "retail and office", "podium"],
}


def _infer_building_type(message: str) -> str:
    lower = message.lower()
    for btype, keywords in _TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return btype
    return "residential"


def _infer_storeys(message: str) -> int:
    m = re.search(r"(\d+)[- ]*(?:stor(?:e?y|ies)|floors?|levels?)", message, re.IGNORECASE)
    if m:
        return max(1, int(m.group(1)))
    return 1


def _defaults_for_type(building_type: str) -> list[str]:
    """Return feature IDs that are defaults for the given building type."""
    return [f["id"] for f in BUILDING_FEATURES if building_type in f.get("default_for", [])]


def _infer_defaults(message: str) -> dict[str, Any]:
    """Extract building type, storey count, and default features from the prompt."""
    building_type = _infer_building_type(message)
    num_storeys = _infer_storeys(message)

    # Override type if many storeys
    if num_storeys > 6 and building_type not in ("highrise",):
        building_type = "highrise"

    default_features = _defaults_for_type(building_type)

    # Height heuristics
    ftf = 3.5 if building_type in ("commercial", "highrise") else 3.0

    return {
        "building_type": building_type,
        "num_storeys": num_storeys,
        "floor_to_floor_height": ftf,
        "default_features": default_features,
    }


# ---------------------------------------------------------------------------
# Local pset enrichment (no HTTP — uses hardcoded fallbacks)
# ---------------------------------------------------------------------------

def _get_pset_summary_local(selected_features: list[str]) -> str:
    """Build a text summary of standard Pset properties using local data only.

    Zero-latency alternative to ``get_pset_summary_for_features`` which
    attempts HTTP calls to the bSDD API.
    """
    ifc_classes: set[str] = set()
    for fid in selected_features:
        for cls in _FEATURE_TO_IFC_CLASSES.get(fid, []):
            ifc_classes.add(cls)

    if not ifc_classes:
        return ""

    lines: list[str] = []
    seen_psets: set[str] = set()
    for cls in sorted(ifc_classes):
        pset_name = COMMON_PSET_MAP.get(cls)
        if not pset_name or pset_name in seen_psets:
            continue
        seen_psets.add(pset_name)
        prop_names = FALLBACK_PSET_PROPERTIES.get(pset_name, [])
        if not prop_names:
            continue
        props_str = ", ".join(prop_names[:12])
        if len(prop_names) > 12:
            props_str += f", … (+{len(prop_names) - 12} more)"
        lines.append(f"  - {pset_name} ({cls}): {props_str}")

    if not lines:
        return ""

    return (
        "\nSTANDARD PROPERTY SETS (IFC4):\n"
        + "\n".join(lines)
        + "\n  Use these exact property names when applying Pset_*Common property sets.\n"
    )


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def clarify(state: dict[str, Any]) -> dict[str, Any]:
    """
    Expand the user message into a detailed description for the plan node.

    Uses ``selected_features`` from state if provided (frontend feature menu),
    otherwise infers sensible defaults from the prompt text.

    Expected state keys:
        - user_message: str
        - needs_clarification: bool
        - selected_features: list[str] (optional — feature IDs from the frontend)

    Produces:
        - detailed_description: str — feature-enriched description for the plan node
        - inferred_defaults: dict — extracted building parameters (for frontend display)
    """
    message = state.get("user_message", "")
    defaults = _infer_defaults(message)

    # Override floor-to-floor height if explicitly provided by the user
    user_ftf: float | None = state.get("floor_to_floor_height")
    if user_ftf is not None:
        defaults["floor_to_floor_height"] = user_ftf

    # Use explicitly selected features if provided, otherwise use inferred defaults
    user_selected: list[str] | None = state.get("selected_features")
    if user_selected:
        # Merge: start with defaults, add user picks, then resolve conflicts
        merged = list(dict.fromkeys(defaults["default_features"] + user_selected))
        selected = _resolve_conflicts(merged, user_selected)
    else:
        selected = defaults["default_features"]

    # Build feature description text
    feature_lines: list[str] = []
    for fid in selected:
        feat = _FEATURE_MAP.get(fid)
        if feat:
            feature_lines.append(f"- {feat['label']}: {feat['description']}")

    feature_text = "\n".join(feature_lines) if feature_lines else "- Basic exterior walls, floor slabs, and a flat roof."

    # Build the enriched description
    ftf = defaults["floor_to_floor_height"]
    detailed = (
        f"{message}\n\n"
        f"Building type: {defaults['building_type']}.\n"
        f"Number of storeys: {defaults['num_storeys']}.\n"
        f"Floor-to-floor height: {ftf} m.\n"
        f"\nIncluded features:\n{feature_text}\n"
        f"\nCONSTRUCTION RULES (mandatory for every building):\n"
        f"- Elevations are STOREY-RELATIVE, not absolute world Z. "
        f"Column base_elevation=0.0, slab elevation=0.0, "
        f"beam elevation={ftf} − beam_depth/2.\n"
        f"- Beam span ≤ 12.5 m; segment longer edges at column positions.\n"
        f"- Beam width ≤ co-linear wall thickness (hidden within wall).\n"
        f"- No beams on the top storey when a roof exists.\n"
        f"- Perimeter columns at wall corners + every ≤ 12.5 m.\n"
        f"- Windows must not overlap column positions.\n"
        f"- Opening spacing ≥ 0.5 m edge-to-edge; ≥ 0.3 m from wall corners.\n"
        f"- Every storey needs a floor slab matching the wall footprint.\n"
        f"- Multi-storey: stairs on every floor except top.\n"
        f"- >4 storeys: elevators required.\n"
        f"- Interior partitions: is_external=false, thickness 0.1–0.15 m."
    )

    # Enrich with standard property set names (local fallback — no HTTP)
    try:
        pset_summary = _get_pset_summary_local(selected)
        if pset_summary:
            detailed += "\n" + pset_summary
    except Exception as e:
        logger.warning("Pset enrichment failed (non-fatal): %s", e)

    return {
        **state,
        "detailed_description": detailed,
        "inferred_defaults": defaults,
    }
