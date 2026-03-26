/**
 * Convert Pascal editor scene data to BuildingPlan JSON.
 *
 * This is a placeholder converter. When Pascal's @pascal-app/core
 * package becomes available as a clean npm bundle, this will parse
 * the Zustand-based node graph into BuildingPlan schema.
 */
export function toPlanJSON(sceneData: object): object {
  // Placeholder implementation
  return {
    description: "Plan generated from visual editor",
    storeys: [
      {
        storey_ref: "GF",
        name: "Ground Floor",
        elevation: 0.0,
        floor_to_floor_height: 3.0,
      },
    ],
    types: [],
    elements: [],
    wall_junctions: [],
    rooms: [],
  };
}
