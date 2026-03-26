"""
Expanded BuildingPlan for v2. All elements map 1:1 to building_blocks functions.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class StoreyDefinition(BaseModel):
    storey_ref: str
    name: str
    elevation: float = 0.0
    floor_to_floor_height: float = 3.0


class WallPlacement(BaseModel):
    element_type: Literal["wall"] = "wall"
    wall_ref: str
    component_id: str = "exterior_wall"
    storey_ref: str
    start_point: list[float] = Field(description="[x, y] coordinates")
    end_point: list[float] = Field(description="[x, y] coordinates")
    height: float = 3.0
    thickness: float = 0.2
    fire_rating: Optional[str] = None
    is_external: bool = True
    wall_type_ref: Optional[str] = None


class ColumnPlacement(BaseModel):
    element_type: Literal["column"] = "column"
    column_ref: str
    storey_ref: str
    position: list[float] = Field(description="[x, y] coordinates")
    base_elevation: float = 0.0
    height: float = 3.0
    profile_type: Literal["RECTANGULAR", "CIRCULAR", "I_SECTION"] = "RECTANGULAR"
    width: float = 0.3
    depth: float = 0.3
    radius: float = 0.15
    column_type_ref: Optional[str] = None


class BeamPlacement(BaseModel):
    element_type: Literal["beam"] = "beam"
    beam_ref: str
    storey_ref: str
    start_point: list[float] = Field(description="[x, y] coordinates")
    end_point: list[float] = Field(description="[x, y] coordinates")
    elevation: float = 3.0
    profile_type: Literal["RECTANGULAR", "I_SECTION"] = "I_SECTION"
    width: float = 0.2
    depth: float = 0.4
    beam_type_ref: Optional[str] = None


class SlabPlacement(BaseModel):
    element_type: Literal["slab"] = "slab"
    storey_ref: str
    boundary_points: list[list[float]] = Field(description="List of [x, y] coordinates")
    depth: float = 0.2
    elevation: float = 0.0
    slab_type: Literal["FLOOR", "ROOF", "LANDING"] = "FLOOR"


class OpeningPlacement(BaseModel):
    element_type: Literal["door", "window"]
    storey_ref: str
    host_wall_ref: str
    distance_along_wall: float
    sill_height: float = 0.0
    width: float = 0.9
    height: float = 2.1
    operation_type: Optional[str] = None    # for doors: SINGLE_SWING_LEFT, etc.
    partition_type: Optional[str] = None   # for windows: SINGLE_PANEL, etc.
    fire_rating: Optional[str] = None


class RoofPlacement(BaseModel):
    element_type: Literal["roof"] = "roof"
    storey_ref: str
    boundary_points: list[list[float]] = Field(description="List of [x, y] coordinates")
    roof_type: Literal["FLAT", "GABLE", "HIP"] = "FLAT"
    ridge_height: float = 1.5
    thickness: float = 0.25


class StairPlacement(BaseModel):
    element_type: Literal["stair"] = "stair"
    storey_ref: str
    start_point: list[float] = Field(description="[x, y] coordinates")
    direction: list[float] = Field(default=[1.0, 0.0], description="[dx, dy] unit vector")
    width: float = 1.2
    num_risers: int = 18
    riser_height: float = 0.175
    tread_depth: float = 0.25


class RailingPlacement(BaseModel):
    element_type: Literal["railing"] = "railing"
    storey_ref: str
    path_points: list[list[float]] = Field(description="List of [x, y, z] coordinates")
    height: float = 1.0
    railing_diameter: float = 0.05


class ElevatorPlacement(BaseModel):
    element_type: Literal["elevator"] = "elevator"
    storey_ref: str
    position: list[float] = Field(description="[x, y] centre of shaft")
    width: float = 2.0
    depth: float = 2.0
    name: str = "Elevator"


ElementPlacement = (
    WallPlacement | ColumnPlacement | BeamPlacement | SlabPlacement |
    OpeningPlacement | RoofPlacement | StairPlacement | RailingPlacement |
    ElevatorPlacement
)


class TypeDefinition(BaseModel):
    """Pre-defined IfcXxxType to register before placing occurrences."""
    type_ref: str
    ifc_class: str     # "IfcWallType", "IfcColumnType", etc.
    preset: Optional[str] = None   # e.g. "exterior_wall_200", "concrete_column_300x300"
    custom_params: dict[str, Any] = Field(default_factory=dict)


class BuildingPlan(BaseModel):
    description: str
    site: dict = Field(default_factory=lambda: {"name": "Default Site"})
    building: dict = Field(default_factory=lambda: {"name": "Building A", "building_type": "Mixed-use"})
    storeys: list[StoreyDefinition]
    types: list[TypeDefinition] = Field(default_factory=list)
    elements: list[ElementPlacement]
    wall_junctions: list[dict] = Field(default_factory=list)
    rooms: list[dict] = Field(default_factory=list)
