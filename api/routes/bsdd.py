"""bSDD API routes — expose buildingSMART Data Dictionary search and properties."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from building_blocks.bsdd import (
    COMMON_PSET_MAP,
    get_pset_properties_for_element,
    get_valid_pset_property_names,
    search_classes,
)

router = APIRouter(tags=["bsdd"])


@router.get("/bsdd/search")
async def bsdd_search(q: str = Query(..., min_length=1, description="Search text")) -> list[dict[str, Any]]:
    """Search bSDD for IFC classes matching a text query."""
    try:
        return await search_classes(q)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"bSDD API error: {e}") from e


@router.get("/bsdd/properties/{ifc_class}")
async def bsdd_properties(ifc_class: str) -> dict[str, Any]:
    """Return standard properties for an IFC class (e.g. IfcWall)."""
    try:
        props = await get_pset_properties_for_element(ifc_class)
        return {"ifc_class": ifc_class, "properties": props, "count": len(props)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"bSDD API error: {e}") from e


@router.get("/bsdd/pset/{pset_name}")
async def bsdd_pset(pset_name: str) -> dict[str, Any]:
    """Return valid property names for a standard Pset (e.g. Pset_WallCommon)."""
    names = get_valid_pset_property_names(pset_name)
    if names is None:
        raise HTTPException(status_code=404, detail=f"Unknown property set: {pset_name}")
    return {"pset_name": pset_name, "property_names": names, "count": len(names)}


@router.get("/bsdd/pset-map")
async def bsdd_pset_map() -> dict[str, str]:
    """Return the IFC class → standard Pset_*Common mapping."""
    return COMMON_PSET_MAP
