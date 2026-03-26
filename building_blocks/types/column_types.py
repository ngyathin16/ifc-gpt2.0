"""
Pre-defined IfcColumnType definitions with material profile sets.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root


def create_concrete_column_type(
    ifc: ifcopenshell.file,
    name: str = "COL-RC-300x300",
    width: float = 0.3,
    depth: float = 0.3,
) -> object:
    """
    Creates an IfcColumnType with a rectangular concrete profile set.
    """
    col_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcColumnType", name=name, predefined_type="COLUMN",
    )

    # Material profile set
    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialProfileSet",
    )
    mat = ifcopenshell.api.material.add_material(ifc, name="C30/37", category="concrete")

    profile = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=f"{name}_profile",
        XDim=width,
        YDim=depth,
    )

    ifcopenshell.api.material.add_profile(
        ifc, profile_set=material_set, material=mat, profile=profile,
    )

    ifcopenshell.api.material.assign_material(ifc, products=[col_type], material=material_set)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=col_type, name="Pset_ColumnCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": False, "LoadBearing": True},
    )

    return col_type


def create_circular_column_type(
    ifc: ifcopenshell.file,
    name: str = "COL-RC-CIRC-300",
    radius: float = 0.15,
) -> object:
    """
    Creates an IfcColumnType with a circular concrete profile set.
    """
    col_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcColumnType", name=name, predefined_type="COLUMN",
    )

    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialProfileSet",
    )
    mat = ifcopenshell.api.material.add_material(ifc, name="C30/37", category="concrete")

    profile = ifc.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        ProfileName=f"{name}_profile",
        Radius=radius,
    )

    ifcopenshell.api.material.add_profile(
        ifc, profile_set=material_set, material=mat, profile=profile,
    )

    ifcopenshell.api.material.assign_material(ifc, products=[col_type], material=material_set)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=col_type, name="Pset_ColumnCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": False, "LoadBearing": True},
    )

    return col_type
