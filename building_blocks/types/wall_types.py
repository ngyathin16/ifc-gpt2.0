"""
Pre-defined IfcWallType definitions with material layer sets.
These are registered once per IFC file and shared by all wall occurrences.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root


def create_exterior_wall_type(
    ifc: ifcopenshell.file,
    name: str = "EXT-WALL-200",
    outer_finish_thickness: float = 0.012,   # plasterboard
    insulation_thickness: float = 0.1,
    structural_thickness: float = 0.2,       # concrete
    inner_finish_thickness: float = 0.012,
) -> object:
    """
    Creates an IfcWallType with a 4-layer material set:
    plasterboard / insulation / structural / plasterboard.
    """
    wall_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcWallType", name=name, predefined_type="STANDARD",
    )

    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialLayerSet",
    )

    layers_spec = [
        ("PB01", "gypsum",     inner_finish_thickness),
        ("INS01", "mineral_wool", insulation_thickness),
        ("CON01", "concrete",  structural_thickness),
        ("PB02", "gypsum",     outer_finish_thickness),
    ]

    for mat_name, category, thickness in layers_spec:
        mat = ifcopenshell.api.material.add_material(ifc, name=mat_name, category=category)
        layer = ifcopenshell.api.material.add_layer(ifc, layer_set=material_set, material=mat)
        ifcopenshell.api.material.edit_layer(
            ifc, layer=layer, attributes={"LayerThickness": thickness},
        )

    ifcopenshell.api.material.assign_material(ifc, products=[wall_type], material=material_set)

    # Pset_WallCommon
    pset = ifcopenshell.api.pset.add_pset(ifc, product=wall_type, name="Pset_WallCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": True, "LoadBearing": True},
    )

    return wall_type


def create_interior_wall_type(
    ifc: ifcopenshell.file,
    name: str = "INT-WALL-100",
    finish_thickness: float = 0.012,
    structural_thickness: float = 0.1,
) -> object:
    """
    Creates an IfcWallType with a 3-layer material set for interior partitions:
    plasterboard / blockwork / plasterboard.
    """
    wall_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcWallType", name=name, predefined_type="PARTITIONING",
    )

    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialLayerSet",
    )

    layers_spec = [
        ("PB01", "gypsum",     finish_thickness),
        ("BLK01", "blockwork", structural_thickness),
        ("PB02", "gypsum",     finish_thickness),
    ]

    for mat_name, category, thickness in layers_spec:
        mat = ifcopenshell.api.material.add_material(ifc, name=mat_name, category=category)
        layer = ifcopenshell.api.material.add_layer(ifc, layer_set=material_set, material=mat)
        ifcopenshell.api.material.edit_layer(
            ifc, layer=layer, attributes={"LayerThickness": thickness},
        )

    ifcopenshell.api.material.assign_material(ifc, products=[wall_type], material=material_set)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=wall_type, name="Pset_WallCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": False, "LoadBearing": False},
    )

    return wall_type
