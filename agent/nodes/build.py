"""
Build node: takes a BuildingPlan and calls building_blocks functions to produce an IFC file.

Uses a dispatch-table pattern instead of a long isinstance chain for
maintainability and O(1) lookup per element.
"""
from __future__ import annotations

import logging
import os
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import ifcopenshell.api.geometry

from agent.schemas import (
    BalconyPlacement,
    BeamPlacement,
    BuildingPlan,
    ColumnPlacement,
    CoveringPlacement,
    ElevatorPlacement,
    FootingPlacement,
    OpeningPlacement,
    RailingPlacement,
    RampPlacement,
    RoofPlacement,
    SlabPlacement,
    StairPlacement,
    StoreyDefinition,
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
from building_blocks.primitives.covering import create_covering
from building_blocks.primitives.elevator import create_elevator_shaft
from building_blocks.primitives.door import create_door
from building_blocks.primitives.footing import create_footing
from building_blocks.primitives.railing import create_railing
from building_blocks.primitives.ramp import create_ramp
from building_blocks.primitives.roof import create_flat_roof, create_pitched_roof
from building_blocks.primitives.slab import create_slab
from building_blocks.primitives.stair import create_stair
from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.window import create_window

logger = logging.getLogger(__name__)

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))

# ---------------------------------------------------------------------------
# Type factory dispatch
# ---------------------------------------------------------------------------

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
        logger.warning("Type factory %s failed for %s", factory.__name__, kwargs, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Build context — passed to every element handler
# ---------------------------------------------------------------------------

class _BuildCtx:
    """Mutable build context shared across element handlers."""

    __slots__ = (
        "ifc", "contexts", "plan", "storeys", "storey_elevations",
        "storey_defs", "types", "walls", "entities", "key_counter",
    )

    def __init__(
        self,
        ifc: Any,
        contexts: dict[str, Any],
        plan: BuildingPlan,
        storeys: dict[str, Any],
        storey_elevations: dict[str, float],
        storey_defs: dict[str, StoreyDefinition],
        types: dict[str, Any],
    ) -> None:
        self.ifc = ifc
        self.contexts = contexts
        self.plan = plan
        self.storeys = storeys
        self.storey_elevations = storey_elevations
        self.storey_defs = storey_defs
        self.types = types
        self.walls: dict[str, Any] = {}
        self.entities: dict[str, Any] = {}
        self.key_counter: Counter[str] = Counter()

    def unique_key(self, prefix: str) -> str:
        """Generate a unique entity key using a monotonic counter."""
        self.key_counter[prefix] += 1
        count = self.key_counter[prefix]
        return f"{prefix}_{count}" if count > 1 else prefix


# ---------------------------------------------------------------------------
# Element handlers — one function per element_type
# ---------------------------------------------------------------------------

ElementHandler = Callable[[Any, Any, float, str, _BuildCtx], None]


def _handle_wall(element: WallPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    wall_type = ctx.types.get(element.wall_type_ref) if element.wall_type_ref else None
    wall = create_wall(
        ctx.ifc, ctx.contexts, storey,
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
    ctx.walls[element.wall_ref] = wall
    ctx.entities[element.wall_ref] = wall


def _handle_column(element: ColumnPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    col_type = ctx.types.get(element.column_type_ref) if element.column_type_ref else None
    col = create_column(
        ctx.ifc, ctx.contexts, storey,
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
    ctx.entities[element.column_ref] = col


def _handle_beam(element: BeamPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    bm_type = ctx.types.get(element.beam_type_ref) if element.beam_type_ref else None
    beam = create_beam(
        ctx.ifc, ctx.contexts, storey,
        p1=element.start_point,
        p2=element.end_point,
        elevation=s_elev + element.elevation,
        profile_type=element.profile_type,
        width=element.width,
        depth=element.depth,
        name=element.beam_ref,
        beam_type=bm_type,
    )
    ctx.entities[element.beam_ref] = beam


def _handle_slab(element: SlabPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    slab = create_slab(
        ctx.ifc, ctx.contexts, storey,
        boundary_points=element.boundary_points,
        depth=element.depth,
        elevation=s_elev + element.elevation,
        predefined_type=element.slab_type,
    )
    key = ctx.unique_key(f"slab_{storey_ref}")
    ctx.entities[key] = slab


def _handle_door(element: OpeningPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    host_wall = ctx.walls.get(element.host_wall_ref)
    if host_wall is None:
        logger.warning("Door skipped: host_wall_ref %r not found in built walls", element.host_wall_ref)
        return
    door = create_door(
        ctx.ifc, ctx.contexts, storey, host_wall,
        distance_along_wall=element.distance_along_wall,
        sill_height=element.sill_height,
        width=element.width,
        height=element.height,
        operation_type=element.operation_type or "SINGLE_SWING_LEFT",
        fire_rating=element.fire_rating,
    )
    key = ctx.unique_key(f"door_{element.host_wall_ref}")
    ctx.entities[key] = door


def _handle_window(element: OpeningPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    host_wall = ctx.walls.get(element.host_wall_ref)
    if host_wall is None:
        logger.warning("Window skipped: host_wall_ref %r not found in built walls", element.host_wall_ref)
        return
    win = create_window(
        ctx.ifc, ctx.contexts, storey, host_wall,
        distance_along_wall=element.distance_along_wall,
        sill_height=element.sill_height,
        width=element.width,
        height=element.height,
        partition_type=element.partition_type or "SINGLE_PANEL",
        fire_rating=element.fire_rating,
    )
    key = ctx.unique_key(f"window_{element.host_wall_ref}")
    ctx.entities[key] = win


def _handle_roof(element: RoofPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    sd = ctx.storey_defs.get(storey_ref)
    roof_elev = s_elev + (sd.floor_to_floor_height if sd else 3.0)
    if element.roof_type == "FLAT":
        roof = create_flat_roof(
            ctx.ifc, ctx.contexts, storey,
            boundary_points=element.boundary_points,
            thickness=element.thickness,
            elevation=roof_elev,
        )
    else:
        roof_type_map = {"GABLE": "GABLE_ROOF", "HIP": "HIP_ROOF"}
        roof = create_pitched_roof(
            ctx.ifc, ctx.contexts, storey,
            boundary_points=element.boundary_points,
            ridge_height=element.ridge_height,
            roof_type=roof_type_map.get(element.roof_type, "GABLE_ROOF"),
            elevation=roof_elev,
        )
    key = ctx.unique_key(f"roof_{storey_ref}")
    ctx.entities[key] = roof


def _handle_stair(element: StairPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    stair = create_stair(
        ctx.ifc, ctx.contexts, storey,
        start_point=element.start_point,
        direction=element.direction,
        width=element.width,
        num_risers=element.num_risers,
        riser_height=element.riser_height,
        tread_depth=element.tread_depth,
        elevation=s_elev,
    )
    key = ctx.unique_key(f"stair_{storey_ref}")
    ctx.entities[key] = stair


def _handle_railing(element: RailingPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    abs_path = [[p[0], p[1], p[2] + s_elev] for p in element.path_points]
    railing = create_railing(
        ctx.ifc, ctx.contexts, storey,
        path_points=abs_path,
        height=element.height,
        railing_diameter=element.railing_diameter,
    )
    key = ctx.unique_key(f"railing_{storey_ref}")
    ctx.entities[key] = railing


def _handle_elevator(element: ElevatorPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    sd = ctx.storey_defs.get(storey_ref)
    ftf = sd.floor_to_floor_height if sd else 3.0
    elev = create_elevator_shaft(
        ctx.ifc, ctx.contexts, storey,
        position=element.position,
        elevation=s_elev,
        width=element.width,
        depth=element.depth,
        height=ftf,
        name=element.name,
    )
    ctx.entities[f"elevator_{storey_ref}_{element.name}"] = elev


def _handle_covering(element: CoveringPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    cov = create_covering(
        ctx.ifc, ctx.contexts, storey,
        boundary_points=element.boundary_points,
        thickness=element.thickness,
        elevation=s_elev + element.elevation,
        name=element.name,
        predefined_type=element.covering_type,
    )
    ctx.entities[f"covering_{storey_ref}_{element.name}"] = cov


def _handle_footing(element: FootingPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    ftg = create_footing(
        ctx.ifc, ctx.contexts, storey,
        position=tuple(element.position),
        width=element.width,
        length=element.length,
        depth=element.depth,
        elevation=s_elev + element.elevation,
        name=element.name,
    )
    key = ctx.unique_key(f"footing_{element.name}")
    ctx.entities[key] = ftg


def _handle_ramp(element: RampPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    rmp = create_ramp(
        ctx.ifc, ctx.contexts, storey,
        start_point=tuple(element.start_point),
        direction=tuple(element.direction),
        width=element.width,
        length=element.length,
        rise=element.rise,
        name=element.name,
    )
    key = ctx.unique_key(f"ramp_{element.name}")
    ctx.entities[key] = rmp


def _handle_balcony(element: BalconyPlacement, storey: Any, s_elev: float, storey_ref: str, ctx: _BuildCtx) -> None:
    bal_slab = create_slab(
        ctx.ifc, ctx.contexts, storey,
        boundary_points=element.boundary_points,
        depth=element.depth,
        elevation=s_elev + element.elevation,
        name=f"{element.name}_Slab",
    )
    ctx.entities[f"balcony_slab_{storey_ref}_{element.name}"] = bal_slab
    if element.railing_path:
        abs_path = [[p[0], p[1], p[2] + s_elev] for p in element.railing_path]
        bal_rail = create_railing(
            ctx.ifc, ctx.contexts, storey,
            path_points=abs_path,
            height=element.railing_height,
        )
        ctx.entities[f"balcony_rail_{storey_ref}_{element.name}"] = bal_rail


# ---------------------------------------------------------------------------
# Dispatch table: element_type string → handler function
# ---------------------------------------------------------------------------

_ELEMENT_HANDLERS: dict[str, ElementHandler] = {
    "wall": _handle_wall,
    "column": _handle_column,
    "beam": _handle_beam,
    "slab": _handle_slab,
    "door": _handle_door,
    "window": _handle_window,
    "roof": _handle_roof,
    "stair": _handle_stair,
    "railing": _handle_railing,
    "elevator": _handle_elevator,
    "covering": _handle_covering,
    "footing": _handle_footing,
    "ramp": _handle_ramp,
    "balcony": _handle_balcony,
}


# ---------------------------------------------------------------------------
# Build node
# ---------------------------------------------------------------------------

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

    # 2. Add storeys + pre-compute lookup dicts
    storeys: dict[str, Any] = {}
    storey_elevations: dict[str, float] = {}
    storey_defs: dict[str, StoreyDefinition] = {}
    for sd in plan.storeys:
        storey = add_storey(
            ifc, contexts["building"],
            name=sd.name,
            elevation=sd.elevation,
        )
        storeys[sd.storey_ref] = storey
        storey_elevations[sd.storey_ref] = sd.elevation
        storey_defs[sd.storey_ref] = sd

    # 3. Register types
    types: dict[str, Any] = {}
    for type_def in plan.types:
        types[type_def.type_ref] = _create_type(
            ifc, type_def.ifc_class, type_def.preset, type_def.custom_params,
        )

    # 4. Build context
    ctx = _BuildCtx(
        ifc=ifc, contexts=contexts, plan=plan,
        storeys=storeys, storey_elevations=storey_elevations,
        storey_defs=storey_defs, types=types,
    )

    # 5. Place elements via dispatch table
    for element in plan.elements:
        storey_ref = element.storey_ref
        storey = storeys.get(storey_ref)
        if storey is None:
            logger.warning("Element skipped: storey_ref %r not in storeys list", storey_ref)
            continue
        s_elev = storey_elevations.get(storey_ref, 0.0)

        handler = _ELEMENT_HANDLERS.get(element.element_type)
        if handler is None:
            logger.warning("No handler for element_type %r, skipping", element.element_type)
            continue

        try:
            handler(element, storey, s_elev, storey_ref, ctx)
        except Exception:
            logger.error(
                "Failed to build %s on %s", element.element_type, storey_ref,
                exc_info=True,
            )

    # 6. Wall connectivity
    for junction in plan.wall_junctions:
        ref1 = junction.get("wall_ref_1")
        ref2 = junction.get("wall_ref_2")
        w1 = ctx.walls.get(ref1)
        w2 = ctx.walls.get(ref2)
        if w1 and w2:
            try:
                ifcopenshell.api.geometry.connect_wall(ifc, wall1=w1, wall2=w2)
            except Exception:
                logger.warning("Wall connectivity failed: %s ↔ %s", ref1, ref2, exc_info=True)

    # 7. Save the IFC file
    WORKSPACE.mkdir(exist_ok=True)
    output_path = WORKSPACE / f"{job_id}.ifc"
    ifc.write(str(output_path))

    return {
        **state,
        "final_ifc_path": str(output_path),
        "ifc_entities": {k: str(v) for k, v in ctx.entities.items()},
    }
