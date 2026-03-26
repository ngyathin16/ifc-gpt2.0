"""
Convenience wrappers for the most commonly needed standard property sets.
All pset names and property names follow buildingSMART convention.
Consult bSDD for the full catalogue.
"""
from __future__ import annotations

import ifcopenshell.api
import ifcopenshell.api.pset


def apply_wall_common_pset(
    ifc, wall,
    is_external: bool = True,
    fire_rating: str | None = None,
    acoustic_rating: str | None = None,
    thermal_transmittance: float | None = None,
):
    """Apply Pset_WallCommon to a wall or wall type."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=wall, name="Pset_WallCommon")
    props: dict = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if acoustic_rating:
        props["AcousticRating"] = acoustic_rating
    if thermal_transmittance is not None:
        props["ThermalTransmittance"] = thermal_transmittance
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_door_common_pset(
    ifc, door,
    fire_rating: str | None = None,
    is_external: bool = False,
    security_rating: str | None = None,
):
    """Apply Pset_DoorCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=door, name="Pset_DoorCommon")
    props: dict = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if security_rating:
        props["SecurityRating"] = security_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_window_common_pset(
    ifc, window,
    fire_rating: str | None = None,
    is_external: bool = True,
    thermal_transmittance: float | None = None,
):
    """Apply Pset_WindowCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=window, name="Pset_WindowCommon")
    props: dict = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if thermal_transmittance is not None:
        props["ThermalTransmittance"] = thermal_transmittance
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_column_common_pset(
    ifc, column,
    fire_rating: str | None = None,
    is_external: bool = False,
    load_bearing: bool = True,
):
    """Apply Pset_ColumnCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=column, name="Pset_ColumnCommon")
    props: dict = {"IsExternal": is_external, "LoadBearing": load_bearing}
    if fire_rating:
        props["FireRating"] = fire_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_slab_common_pset(
    ifc, slab,
    is_external: bool = False,
    fire_rating: str | None = None,
    load_bearing: bool = True,
):
    """Apply Pset_SlabCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=slab, name="Pset_SlabCommon")
    props: dict = {"IsExternal": is_external, "LoadBearing": load_bearing}
    if fire_rating:
        props["FireRating"] = fire_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_beam_common_pset(
    ifc, beam,
    fire_rating: str | None = None,
    is_external: bool = False,
    load_bearing: bool = True,
):
    """Apply Pset_BeamCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=beam, name="Pset_BeamCommon")
    props: dict = {"IsExternal": is_external, "LoadBearing": load_bearing}
    if fire_rating:
        props["FireRating"] = fire_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_space_common_pset(
    ifc, space,
    reference: str | None = None,
    category: str | None = None,
):
    """Apply Pset_SpaceCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=space, name="Pset_SpaceCommon")
    props: dict = {}
    if reference:
        props["Reference"] = reference
    if category:
        props["Category"] = category
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_roof_common_pset(
    ifc, roof,
    is_external: bool = True,
    fire_rating: str | None = None,
):
    """Apply Pset_RoofCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=roof, name="Pset_RoofCommon")
    props: dict = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_stair_common_pset(
    ifc, stair,
    fire_rating: str | None = None,
    is_external: bool = False,
    number_of_risers: int | None = None,
    riser_height: float | None = None,
    tread_length: float | None = None,
):
    """Apply Pset_StairCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=stair, name="Pset_StairCommon")
    props: dict = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if number_of_risers is not None:
        props["NumberOfRiser"] = number_of_risers
    if riser_height is not None:
        props["RiserHeight"] = riser_height
    if tread_length is not None:
        props["TreadLength"] = tread_length
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)
