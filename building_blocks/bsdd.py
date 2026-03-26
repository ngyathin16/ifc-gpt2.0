"""
Client for the buildingSMART Data Dictionary (bSDD) REST API.

Provides both async (for FastAPI routes) and sync (for LangGraph nodes)
interfaces with an in-memory TTL cache to minimise repeated API calls.

All sync helpers are best-effort: they return sensible hardcoded fallbacks
when the bSDD API is unreachable, so the pipeline never blocks or fails
due to an external service outage.

Reference: https://technical.buildingsmart.org/services/bsdd/using-the-bsdd-api/
Base URL:  https://api.bsdd.buildingsmart.org
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BSDD_BASE = "https://api.bsdd.buildingsmart.org"
IFC_DICT_URI = "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3"
_HEADERS = {"User-Agent": "ifc-gpt-v2/2.0"}
_TIMEOUT = 8.0  # seconds — keep short so pipeline doesn't stall

# ---------------------------------------------------------------------------
# Hardcoded fallback — used when the bSDD API is unreachable
# ---------------------------------------------------------------------------

COMMON_PSET_MAP: dict[str, str] = {
    "IfcWall": "Pset_WallCommon",
    "IfcDoor": "Pset_DoorCommon",
    "IfcWindow": "Pset_WindowCommon",
    "IfcColumn": "Pset_ColumnCommon",
    "IfcBeam": "Pset_BeamCommon",
    "IfcSlab": "Pset_SlabCommon",
    "IfcRoof": "Pset_RoofCommon",
    "IfcStairFlight": "Pset_StairFlightCommon",
    "IfcStair": "Pset_StairCommon",
    "IfcSpace": "Pset_SpaceCommon",
    "IfcRailing": "Pset_RailingCommon",
    "IfcCurtainWall": "Pset_CurtainWallCommon",
}

FALLBACK_PSET_PROPERTIES: dict[str, list[str]] = {
    "Pset_WallCommon": [
        "IsExternal", "FireRating", "AcousticRating", "ThermalTransmittance",
        "Combustible", "Compartmentation", "LoadBearing", "ExtendToStructure",
        "SurfaceSpreadOfFlame", "Reference", "Status",
    ],
    "Pset_DoorCommon": [
        "IsExternal", "FireRating", "SecurityRating", "Infiltration",
        "AcousticRating", "ThermalTransmittance", "GlazingAreaFraction",
        "HandicapAccessible", "FireExit", "SelfClosing", "SmokeStop",
        "Reference", "Status",
    ],
    "Pset_WindowCommon": [
        "IsExternal", "FireRating", "AcousticRating", "ThermalTransmittance",
        "GlazingAreaFraction", "Infiltration", "SmokeStop",
        "Reference", "Status",
    ],
    "Pset_ColumnCommon": [
        "IsExternal", "FireRating", "LoadBearing", "Reference", "Status",
    ],
    "Pset_BeamCommon": [
        "IsExternal", "FireRating", "LoadBearing", "Reference", "Status",
        "Slope",
    ],
    "Pset_SlabCommon": [
        "IsExternal", "FireRating", "LoadBearing", "Compartmentation",
        "AcousticRating", "ThermalTransmittance", "Reference", "Status",
    ],
    "Pset_RoofCommon": [
        "IsExternal", "FireRating", "Reference", "Status",
        "ProjectedArea", "TotalArea",
    ],
    "Pset_StairCommon": [
        "IsExternal", "FireRating", "NumberOfRiser", "NumberOfTreads",
        "RiserHeight", "TreadLength", "Reference", "Status",
        "HandicapAccessible", "FireExit", "HasNonSkidSurface", "RequiredHeadroom",
    ],
    "Pset_StairFlightCommon": [
        "NumberOfRiser", "NumberOfTreads", "RiserHeight", "TreadLength",
        "Headroom", "WalkingLineOffset", "TreadLengthAtOffset",
        "TreadLengthAtInnerSide", "WaistThickness", "Reference", "Status",
    ],
    "Pset_SpaceCommon": [
        "Reference", "Category", "IsExternal", "GrossPlannedArea",
        "NetPlannedArea", "PubliclyAccessible", "HandicapAccessible",
    ],
    "Pset_RailingCommon": [
        "IsExternal", "Height", "Reference", "Status", "Diameter",
    ],
    "Pset_CurtainWallCommon": [
        "IsExternal", "FireRating", "AcousticRating", "ThermalTransmittance",
        "Reference", "Status",
    ],
}

# ---------------------------------------------------------------------------
# TTL cache
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 3600  # 1 hour


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = (time.time(), value)


def clear_cache() -> None:
    """Clear the in-memory bSDD cache."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Async API (for FastAPI routes)
# ---------------------------------------------------------------------------

async def search_classes(query: str, dictionary_uri: str = IFC_DICT_URI) -> list[dict]:
    """Search bSDD for classes matching a text query."""
    cache_key = f"search:{dictionary_uri}:{query}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            f"{BSDD_BASE}/api/SearchList/v1",
            params={
                "SearchText": query,
                "DictionaryUri": dictionary_uri,
                "languageCode": "en-GB",
            },
            headers=_HEADERS,
        )
        r.raise_for_status()
        result = r.json().get("Classes", [])
        _set_cached(cache_key, result)
        return result


async def get_class_properties(
    class_uri: str,
    include_child_class_properties: bool = False,
) -> dict:
    """Retrieve full class details and its standard properties from bSDD."""
    cache_key = f"class:{class_uri}:{include_child_class_properties}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            f"{BSDD_BASE}/api/Class/v1",
            params={
                "uri": class_uri,
                "includeChildClassProperties": include_child_class_properties,
                "languageCode": "en-GB",
            },
            headers=_HEADERS,
        )
        r.raise_for_status()
        result = r.json()
        _set_cached(cache_key, result)
        return result


async def get_pset_properties_for_element(ifc_class_name: str) -> list[dict]:
    """Given an IFC class name like 'IfcWall', return standard properties."""
    uri = f"{IFC_DICT_URI}/class/{ifc_class_name}"
    data = await get_class_properties(uri)
    return data.get("classProperties", []) or data.get("ClassProperties", [])


# ---------------------------------------------------------------------------
# Sync API (for LangGraph nodes) — best-effort with hardcoded fallbacks
# ---------------------------------------------------------------------------

def search_classes_sync(query: str, dictionary_uri: str = IFC_DICT_URI) -> list[dict]:
    """Sync version of search_classes. Returns ``[]`` on failure."""
    cache_key = f"search:{dictionary_uri}:{query}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{BSDD_BASE}/api/SearchList/v1",
                params={
                    "SearchText": query,
                    "DictionaryUri": dictionary_uri,
                    "languageCode": "en-GB",
                },
                headers=_HEADERS,
            )
            r.raise_for_status()
            result = r.json().get("Classes", [])
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning("bSDD search_classes failed for %r: %s", query, e)
        return []


def get_class_properties_sync(
    class_uri: str,
    include_child_class_properties: bool = False,
) -> dict:
    """Sync version of get_class_properties. Returns ``{}`` on failure."""
    cache_key = f"class:{class_uri}:{include_child_class_properties}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(
                f"{BSDD_BASE}/api/Class/v1",
                params={
                    "uri": class_uri,
                    "includeChildClassProperties": include_child_class_properties,
                    "languageCode": "en-GB",
                },
                headers=_HEADERS,
            )
            r.raise_for_status()
            result = r.json()
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        logger.warning("bSDD get_class_properties failed for %r: %s", class_uri, e)
        return {}


def get_pset_properties_for_element_sync(ifc_class_name: str) -> list[dict]:
    """Sync version: given an IFC class name, return standard properties."""
    uri = f"{IFC_DICT_URI}/class/{ifc_class_name}"
    data = get_class_properties_sync(uri)
    return data.get("classProperties", []) or data.get("ClassProperties", [])


def get_standard_psets_sync(ifc_class_name: str) -> dict[str, list[str]]:
    """Return ``{pset_name: [property_name, ...]}`` for an IFC class.

    Tries the bSDD API first, falls back to ``FALLBACK_PSET_PROPERTIES``.
    """
    cache_key = f"psets:{ifc_class_name}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Try bSDD
    props = get_pset_properties_for_element_sync(ifc_class_name)
    psets: dict[str, list[str]] = {}
    for p in props:
        pset_name = p.get("propertySet") or p.get("PropertySet") or ""
        prop_name = p.get("name") or p.get("Name") or ""
        if pset_name and prop_name:
            psets.setdefault(pset_name, []).append(prop_name)

    # Fallback to hardcoded if bSDD returned nothing useful
    if not psets:
        pset_name = COMMON_PSET_MAP.get(ifc_class_name)
        if pset_name and pset_name in FALLBACK_PSET_PROPERTIES:
            psets = {pset_name: list(FALLBACK_PSET_PROPERTIES[pset_name])}

    _set_cached(cache_key, psets)
    return psets


def get_valid_pset_property_names(pset_name: str) -> list[str] | None:
    """Return valid property names for a standard ``Pset_*`` set.

    Tries bSDD first (class URI for the Pset), then hardcoded fallback.
    Returns ``None`` for unknown / custom property sets.
    """
    cache_key = f"pset_props:{pset_name}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # Try bSDD — each standard Pset is a class in bSDD
    uri = f"{IFC_DICT_URI}/class/{pset_name}"
    data = get_class_properties_sync(uri)
    class_props = data.get("classProperties", []) or data.get("ClassProperties", [])
    if class_props:
        names = [
            p.get("name") or p.get("Name") or ""
            for p in class_props
        ]
        names = [n for n in names if n]
        if names:
            _set_cached(cache_key, names)
            return names

    # Hardcoded fallback
    fallback = FALLBACK_PSET_PROPERTIES.get(pset_name)
    if fallback:
        _set_cached(cache_key, fallback)
        return fallback

    return None  # unknown / custom pset


# ---------------------------------------------------------------------------
# Enrichment helpers (for pipeline nodes)
# ---------------------------------------------------------------------------

_FEATURE_TO_IFC_CLASSES: dict[str, list[str]] = {
    "exterior_walls": ["IfcWall"],
    "core_walls": ["IfcWall"],
    "interior_partitions": ["IfcWall"],
    "columns": ["IfcColumn"],
    "beams": ["IfcBeam"],
    "floor_slabs": ["IfcSlab"],
    "flat_roof": ["IfcRoof"],
    "pitched_roof": ["IfcRoof"],
    "stairs": ["IfcStair"],
    "railings": ["IfcRailing"],
    "entrance_doors": ["IfcDoor"],
    "elevators": [],
    "lobby": ["IfcSpace"],
    "curtain_wall": ["IfcCurtainWall"],
    "open_plan": [],
}


def get_pset_summary_for_features(selected_features: list[str]) -> str:
    """Build a text summary of standard Pset properties for selected features.

    Used by the clarify node to enrich the description for the plan LLM.
    Returns an empty string if no relevant psets are found.
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
        psets = get_standard_psets_sync(cls)
        for pset_name, prop_names in psets.items():
            if pset_name in seen_psets:
                continue
            seen_psets.add(pset_name)
            props_str = ", ".join(prop_names[:12])
            if len(prop_names) > 12:
                props_str += f", … (+{len(prop_names) - 12} more)"
            lines.append(f"  - {pset_name} ({cls}): {props_str}")

    if not lines:
        return ""

    return (
        "\nSTANDARD PROPERTY SETS (from bSDD / IFC4):\n"
        + "\n".join(lines)
        + "\n  Use these exact property names when applying Pset_*Common property sets.\n"
    )
