"""
Sets up the IFC4 project/site/building/storey spatial hierarchy.
All other building_blocks functions receive the IFC file and storey references.
"""
from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit


def create_ifc_project(
    project_name: str = "IFC-GPT Project",
    site_name: str = "Default Site",
    building_name: str = "Building A",
) -> tuple[ifcopenshell.file, dict]:
    """
    Create a blank IFC4 file with Project/Site/Building hierarchy.

    Returns:
        (ifc_file, context_dict) where context_dict has keys:
        - model3d: IfcGeometricRepresentationContext (3D)
        - body:    Model/Body/MODEL_VIEW context
        - axis:    Plan/Axis/GRAPH_VIEW context
        - project, site, building
    """
    ifc = ifcopenshell.file(schema="IFC4")

    # Project
    project = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcProject", name=project_name)
    ifcopenshell.api.unit.assign_unit(ifc, length={"is_metric": True, "raw": "METRES"})

    # Geometric contexts
    model3d = ifcopenshell.api.context.add_context(ifc, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        ifc, context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=model3d,
    )
    axis = ifcopenshell.api.context.add_context(
        ifc, context_type="Plan", context_identifier="Axis",
        target_view="GRAPH_VIEW", parent=model3d,
    )

    # Spatial hierarchy
    site = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSite", name=site_name)
    building = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBuilding", name=building_name)

    ifcopenshell.api.aggregate.assign_object(ifc, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(ifc, products=[building], relating_object=site)

    return ifc, {
        "model3d": model3d,
        "body": body,
        "axis": axis,
        "project": project,
        "site": site,
        "building": building,
    }


def add_storey(
    ifc: ifcopenshell.file,
    building,
    name: str = "Ground Floor",
    elevation: float = 0.0,
) -> object:
    """Add an IfcBuildingStorey to the building at the given elevation."""
    storey = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBuildingStorey", name=name)
    storey.Elevation = float(elevation)
    ifcopenshell.api.aggregate.assign_object(ifc, products=[storey], relating_object=building)
    ifcopenshell.api.geometry.edit_object_placement(
        ifc,
        product=storey,
        matrix=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, elevation], [0, 0, 0, 1]],
    )
    return storey
