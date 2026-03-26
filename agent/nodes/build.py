"""
Build node: takes a BuildingPlan and calls building_blocks functions to produce an IFC file.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from agent.schemas import (
    BeamPlacement,
    BuildingPlan,
    ColumnPlacement,
    ElevatorPlacement,
    OpeningPlacement,
    RailingPlacement,
    RoofPlacement,
    SlabPlacement,
    StairPlacement,
    WallPlacement,
)
from building_blocks.context import add_storey, create_ifc_project
from building_blocks.types.wall_types import create_exterior_wall_type, create_interior_wall_type
from building_blocks.types.column_types import create_concrete_column_type, create_circular_column_type
from building_blocks.types.beam_types import create_concrete_beam_type, create_steel_beam_type
from building_blocks.types.door_types import create_single_swing_door_type, create_fire_door_type
from building_blocks.types.window_types import create_standard_window_type, create_double_glazed_window_type
from building_blocks.primitives.beam import create_beam
from building_blocks.primitives.column import create_column
from building_blocks.primitives.elevator import create_elevator_shaft
from building_blocks.primitives.door import create_door
from building_blocks.primitives.railing import create_railing
from building_blocks.primitives.roof import create_flat_roof, create_pitched_roof
from building_blocks.primitives.slab import create_slab
from building_blocks.primitives.stair import create_stair
from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.window import create_window

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))

# Preset name → factory function mapping
_TYPE_FACTORIES: dict[str, Any] = {
    # Wall types
    "exterior_wall": create_exterior_wall_type,
    "exterior_wall_200": create_exterior_wall_type,
    "interior_wall": create_interior_wall_type,
    "interior_wall_100": create_interior_wall_type,
    # Column types
    "concrete_column": create_concrete_column_type,
    "concrete_column_300x300": create_concrete_column_type,
    "circular_column": create_circular_column_type,
    # Beam types
    "concrete_beam": create_concrete_beam_type,
    "concrete_beam_200x400": create_concrete_beam_type,
    "steel_beam": create_steel_beam_type,
    # Door types
    "single_swing_door": create_single_swing_door_type,
    "fire_door": create_fire_door_type,
    # Window types
    "standard_window": create_standard_window_type,
    "double_glazed_window": create_double_glazed_window_type,
}

# IFC class → default factory (used when no preset is specified)
_CLASS_DEFAULT_FACTORY: dict[str, Any] = {
    "IfcWallType": create_exterior_wall_type,
    "IfcColumnType": create_concrete_column_type,
    "IfcBeamType": create_concrete_beam_type,
    "IfcDoorType": create_single_swing_door_type,
    "IfcWindowType": create_standard_window_type,
}


def _create_type(
    ifc: Any,
    ifc_class: str,
    preset: str | None,
    custom_params: dict[str, Any],
) -> Any | None:
    """Dispatch to the correct type factory based on preset or ifc_class."""
    factory = None
    if preset:
        factory = _TYPE_FACTORIES.get(preset)
    if factory is None:
        factory = _CLASS_DEFAULT_FACTORY.get(ifc_class)
    if factory is None:
        return None
    kwargs: dict[str, Any] = {"ifc": ifc}
    if custom_params:
        kwargs.update(custom_params)
    try:
        return factory(**kwargs)
    except Exception:
        return None


def build(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an IFC file from the BuildingPlan.

    Expected state keys:
        - building_plan: BuildingPlan
        - job_id: str (optional, for file naming)

    Produces:
        - final_ifc_path: str — path to the generated IFC file
        - ifc_entities: dict — mapping of refs to IFC entities
    """
    plan: BuildingPlan = state["building_plan"]
    job_id = state.get("job_id", str(uuid.uuid4())[:8])

    # 1. Create IFC project
    site_name = plan.site.get("name", "Default Site")
    building_name = plan.building.get("name", "Building A")
    ifc, contexts = create_ifc_project(
        project_name="IFC-GPT Project",
        site_name=site_name,
        building_name=building_name,
    )

    # 2. Add storeys
    storeys: dict[str, Any] = {}
    storey_elevations: dict[str, float] = {}
    for storey_def in plan.storeys:
        storey = add_storey(
            ifc, contexts["building"],
            name=storey_def.name,
            elevation=storey_def.elevation,
        )
        storeys[storey_def.storey_ref] = storey
        storey_elevations[storey_def.storey_ref] = storey_def.elevation

    # 3. Register types — dispatch to type factories
    types: dict[str, Any] = {}
    for type_def in plan.types:
        types[type_def.type_ref] = _create_type(ifc, type_def.ifc_class, type_def.preset, type_def.custom_params)

    # 4. Place elements
    walls: dict[str, Any] = {}
    entities: dict[str, Any] = {}

    for element in plan.elements:
        storey_ref = element.storey_ref
        storey = storeys.get(storey_ref)
        if storey is None:
            continue
        s_elev = storey_elevations.get(storey_ref, 0.0)

        if isinstance(element, WallPlacement):
            wall_type = types.get(element.wall_type_ref) if element.wall_type_ref else None
            wall = create_wall(
                ifc, contexts, storey,
                p1=element.start_point,
                p2=element.end_point,
                elevation=s_elev,
                height=element.height,
                thickness=element.thickness,
                name=element.wall_ref,
                wall_type=wall_type,
                fire_rating=element.fire_rating,
                is_external=element.is_external,
            )
            walls[element.wall_ref] = wall
            entities[element.wall_ref] = wall

        elif isinstance(element, ColumnPlacement):
            col_type = types.get(element.column_type_ref) if element.column_type_ref else None
            col = create_column(
                ifc, contexts, storey,
                position=element.position,
                base_elevation=s_elev + element.base_elevation,
                height=element.height,
                profile_type=element.profile_type,
                width=element.width,
                depth=element.depth,
                radius=element.radius,
                name=element.column_ref,
                column_type=col_type,
            )
            entities[element.column_ref] = col

        elif isinstance(element, BeamPlacement):
            bm_type = types.get(element.beam_type_ref) if element.beam_type_ref else None
            beam = create_beam(
                ifc, contexts, storey,
                p1=element.start_point,
                p2=element.end_point,
                elevation=s_elev + element.elevation,
                profile_type=element.profile_type,
                width=element.width,
                depth=element.depth,
                name=element.beam_ref,
                beam_type=bm_type,
            )
            entities[element.beam_ref] = beam

        elif isinstance(element, SlabPlacement):
            slab = create_slab(
                ifc, contexts, storey,
                boundary_points=element.boundary_points,
                depth=element.depth,
                elevation=s_elev + element.elevation,
                predefined_type=element.slab_type,
            )
            entities[f"slab_{storey_ref}"] = slab

        elif isinstance(element, OpeningPlacement):
            host_wall = walls.get(element.host_wall_ref)
            if host_wall is None:
                continue

            if element.element_type == "door":
                door = create_door(
                    ifc, contexts, storey, host_wall,
                    distance_along_wall=element.distance_along_wall,
                    sill_height=element.sill_height,
                    width=element.width,
                    height=element.height,
                    operation_type=element.operation_type or "SINGLE_SWING_LEFT",
                    fire_rating=element.fire_rating,
                )
                entities[f"door_{element.host_wall_ref}"] = door
            elif element.element_type == "window":
                win = create_window(
                    ifc, contexts, storey, host_wall,
                    distance_along_wall=element.distance_along_wall,
                    sill_height=element.sill_height,
                    width=element.width,
                    height=element.height,
                    partition_type=element.partition_type or "SINGLE_PANEL",
                    fire_rating=element.fire_rating,
                )
                entities[f"window_{element.host_wall_ref}"] = win

        elif isinstance(element, RoofPlacement):
            # Roof sits at top of storey walls; use storey elevation + wall height
            storey_def = next((s for s in plan.storeys if s.storey_ref == storey_ref), None)
            roof_elev = s_elev + (storey_def.floor_to_floor_height if storey_def else 3.0)
            if element.roof_type == "FLAT":
                roof = create_flat_roof(
                    ifc, contexts, storey,
                    boundary_points=element.boundary_points,
                    thickness=element.thickness,
                    elevation=roof_elev,
                )
            else:
                roof_type_map = {"GABLE": "GABLE_ROOF", "HIP": "HIP_ROOF"}
                roof = create_pitched_roof(
                    ifc, contexts, storey,
                    boundary_points=element.boundary_points,
                    ridge_height=element.ridge_height,
                    roof_type=roof_type_map.get(element.roof_type, "GABLE_ROOF"),
                    elevation=roof_elev,
                )
            entities[f"roof_{storey_ref}"] = roof

        elif isinstance(element, StairPlacement):
            stair = create_stair(
                ifc, contexts, storey,
                start_point=element.start_point,
                direction=element.direction,
                width=element.width,
                num_risers=element.num_risers,
                riser_height=element.riser_height,
                tread_depth=element.tread_depth,
                elevation=s_elev,
            )
            entities[f"stair_{storey_ref}"] = stair

        elif isinstance(element, RailingPlacement):
            # Offset railing path_points z by storey elevation
            abs_path = [
                [p[0], p[1], p[2] + s_elev] for p in element.path_points
            ]
            railing = create_railing(
                ifc, contexts, storey,
                path_points=abs_path,
                height=element.height,
                railing_diameter=element.railing_diameter,
            )
            entities[f"railing_{storey_ref}"] = railing

        elif isinstance(element, ElevatorPlacement):
            storey_def = next((s for s in plan.storeys if s.storey_ref == storey_ref), None)
            ftf = storey_def.floor_to_floor_height if storey_def else 3.0
            elev = create_elevator_shaft(
                ifc, contexts, storey,
                position=element.position,
                elevation=s_elev,
                width=element.width,
                depth=element.depth,
                height=ftf,
                name=element.name,
            )
            entities[f"elevator_{storey_ref}_{element.name}"] = elev

    # 5. Wall connectivity
    import ifcopenshell.api.geometry

    for junction in plan.wall_junctions:
        ref1 = junction.get("wall_ref_1")
        ref2 = junction.get("wall_ref_2")
        w1 = walls.get(ref1)
        w2 = walls.get(ref2)
        if w1 and w2:
            try:
                ifcopenshell.api.geometry.connect_wall(ifc, wall1=w1, wall2=w2)
            except Exception:
                pass  # Non-critical if connectivity fails

    # 6. Save the IFC file
    WORKSPACE.mkdir(exist_ok=True)
    output_path = WORKSPACE / f"{job_id}.ifc"
    ifc.write(str(output_path))

    return {
        **state,
        "final_ifc_path": str(output_path),
        "ifc_entities": {k: str(v) for k, v in entities.items()},
    }
