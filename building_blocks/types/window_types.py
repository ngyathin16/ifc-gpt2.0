"""
Pre-defined IfcWindowType definitions.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root


def create_standard_window_type(
    ifc: ifcopenshell.file,
    name: str = "WIN-STD-1200x1500",
    width: float = 1.2,
    height: float = 1.5,
) -> object:
    """
    Creates an IfcWindowType for standard single-panel windows.
    """
    win_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcWindowType", name=name,
        predefined_type="WINDOW",
    )

    mat = ifcopenshell.api.material.add_material(ifc, name="Aluminium", category="aluminium")
    ifcopenshell.api.material.assign_material(ifc, products=[win_type], material=mat)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=win_type, name="Pset_WindowCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={
            "IsExternal": True,
            "OverallWidth": width,
            "OverallHeight": height,
            "ThermalTransmittance": 1.6,
        },
    )

    return win_type


def create_double_glazed_window_type(
    ifc: ifcopenshell.file,
    name: str = "WIN-DG-1200x1500",
    width: float = 1.2,
    height: float = 1.5,
    thermal_transmittance: float = 1.1,
) -> object:
    """
    Creates an IfcWindowType for double-glazed windows.
    """
    win_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcWindowType", name=name,
        predefined_type="WINDOW",
    )

    mat = ifcopenshell.api.material.add_material(ifc, name="Aluminium-DG", category="aluminium")
    ifcopenshell.api.material.assign_material(ifc, products=[win_type], material=mat)

    pset = ifcopenshell.api.pset.add_pset(ifc, product=win_type, name="Pset_WindowCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={
            "IsExternal": True,
            "OverallWidth": width,
            "OverallHeight": height,
            "ThermalTransmittance": thermal_transmittance,
            "GlazingAreaFraction": 0.8,
        },
    )

    return win_type
