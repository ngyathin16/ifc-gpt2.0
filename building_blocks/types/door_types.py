"""
Pre-defined IfcDoorType definitions.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root


def create_single_swing_door_type(
    ifc: ifcopenshell.file,
    name: str = "DR-SINGLE-900x2100",
    width: float = 0.9,
    height: float = 2.1,
) -> object:
    """
    Creates an IfcDoorType for single-swing doors.
    """
    door_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcDoorType", name=name,
        predefined_type="DOOR",
    )

    mat = ifcopenshell.api.material.add_material(ifc, name="Timber", category="wood")
    ifcopenshell.api.material.assign_material(ifc, products=[door_type], material=mat)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=door_type, name="Pset_DoorCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={
            "IsExternal": False,
            "FireRating": "NONE",
            "OverallWidth": width,
            "OverallHeight": height,
        },
    )

    return door_type


def create_fire_door_type(
    ifc: ifcopenshell.file,
    name: str = "DR-FIRE-900x2100",
    width: float = 0.9,
    height: float = 2.1,
    fire_rating: str = "1HR",
) -> object:
    """
    Creates an IfcDoorType for fire-rated doors.
    """
    door_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcDoorType", name=name,
        predefined_type="DOOR",
    )

    mat = ifcopenshell.api.material.add_material(ifc, name="Steel", category="steel")
    ifcopenshell.api.material.assign_material(ifc, products=[door_type], material=mat)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=door_type, name="Pset_DoorCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={
            "IsExternal": False,
            "FireRating": fire_rating,
            "OverallWidth": width,
            "OverallHeight": height,
        },
    )

    return door_type
