"""
Pre-defined IfcBeamType definitions with material profile sets.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root


def create_concrete_beam_type(
    ifc: ifcopenshell.file,
    name: str = "BM-RC-200x400",
    width: float = 0.2,
    depth: float = 0.4,
) -> object:
    """
    Creates an IfcBeamType with a rectangular concrete profile set.
    """
    beam_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcBeamType", name=name, predefined_type="BEAM",
    )

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

    ifcopenshell.api.material.assign_material(ifc, products=[beam_type], material=material_set)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=beam_type, name="Pset_BeamCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": False, "LoadBearing": True},
    )

    return beam_type


def create_steel_beam_type(
    ifc: ifcopenshell.file,
    name: str = "BM-STL-UB254x146",
    width: float = 0.146,
    depth: float = 0.254,
    web_thickness: float = 0.0063,
    flange_thickness: float = 0.0109,
) -> object:
    """
    Creates an IfcBeamType with a steel I-section profile set.
    """
    beam_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcBeamType", name=name, predefined_type="BEAM",
    )

    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialProfileSet",
    )
    mat = ifcopenshell.api.material.add_material(ifc, name="S355", category="steel")

    profile = ifc.create_entity(
        "IfcIShapeProfileDef",
        ProfileType="AREA",
        ProfileName=f"{name}_profile",
        OverallWidth=width,
        OverallDepth=depth,
        WebThickness=web_thickness,
        FlangeThickness=flange_thickness,
    )

    ifcopenshell.api.material.add_profile(
        ifc, profile_set=material_set, material=mat, profile=profile,
    )

    ifcopenshell.api.material.assign_material(ifc, products=[beam_type], material=material_set)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=beam_type, name="Pset_BeamCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": False, "LoadBearing": True},
    )

    return beam_type
