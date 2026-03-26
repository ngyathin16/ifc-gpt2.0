/**
 * Shared BuildingPlan TypeScript types.
 * Mirrors agent/schemas.py for frontend use.
 */

export interface StoreyDefinition {
  storey_ref: string;
  name: string;
  elevation: number;
  floor_to_floor_height: number;
}

export interface WallPlacement {
  element_type: "wall";
  wall_ref: string;
  component_id: string;
  storey_ref: string;
  start_point: [number, number];
  end_point: [number, number];
  height: number;
  thickness: number;
  fire_rating?: string;
  is_external: boolean;
  wall_type_ref?: string;
}

export interface ColumnPlacement {
  element_type: "column";
  column_ref: string;
  storey_ref: string;
  position: [number, number];
  base_elevation: number;
  height: number;
  profile_type: "RECTANGULAR" | "CIRCULAR" | "I_SECTION";
  width: number;
  depth: number;
  radius: number;
  column_type_ref?: string;
}

export interface BeamPlacement {
  element_type: "beam";
  beam_ref: string;
  storey_ref: string;
  start_point: [number, number];
  end_point: [number, number];
  elevation: number;
  profile_type: "RECTANGULAR" | "I_SECTION";
  width: number;
  depth: number;
  beam_type_ref?: string;
}

export interface SlabPlacement {
  element_type: "slab";
  storey_ref: string;
  boundary_points: [number, number][];
  depth: number;
  elevation: number;
  slab_type: "FLOOR" | "ROOF" | "LANDING";
}

export interface OpeningPlacement {
  element_type: "door" | "window";
  storey_ref: string;
  host_wall_ref: string;
  distance_along_wall: number;
  sill_height: number;
  width: number;
  height: number;
  operation_type?: string;
  partition_type?: string;
  fire_rating?: string;
}

export interface RoofPlacement {
  element_type: "roof";
  storey_ref: string;
  boundary_points: [number, number][];
  roof_type: "FLAT" | "GABLE" | "HIP";
  ridge_height: number;
  thickness: number;
}

export interface StairPlacement {
  element_type: "stair";
  storey_ref: string;
  start_point: [number, number];
  direction: [number, number];
  width: number;
  num_risers: number;
  riser_height: number;
  tread_depth: number;
}

export interface RailingPlacement {
  element_type: "railing";
  storey_ref: string;
  path_points: [number, number, number][];
  height: number;
  railing_diameter: number;
}

export interface ElevatorPlacement {
  element_type: "elevator";
  storey_ref: string;
  position: [number, number];
  width: number;
  depth: number;
  name: string;
}

export type ElementPlacement =
  | WallPlacement
  | ColumnPlacement
  | BeamPlacement
  | SlabPlacement
  | OpeningPlacement
  | RoofPlacement
  | StairPlacement
  | RailingPlacement
  | ElevatorPlacement;

export interface TypeDefinition {
  type_ref: string;
  ifc_class: string;
  preset?: string;
  custom_params: Record<string, unknown>;
}

export interface BuildingPlan {
  description: string;
  site: { name: string };
  building: { name: string; building_type: string };
  storeys: StoreyDefinition[];
  types: TypeDefinition[];
  elements: ElementPlacement[];
  wall_junctions: Record<string, string>[];
  rooms: Record<string, unknown>[];
}
