"use client";
import { create } from "zustand";

interface PascalEditorState {
  nodes: object[];
  edges: object[];
  addNode: (node: object) => void;
  removeNode: (id: string) => void;
  clear: () => void;
  toBuildingPlan: () => object;
}

export const usePascalEditor = create<PascalEditorState>((set, get) => ({
  nodes: [],
  edges: [],
  addNode: (node) => set((s) => ({ nodes: [...s.nodes, node] })),
  removeNode: (id) =>
    set((s) => ({ nodes: s.nodes.filter((n: any) => n.id !== id) })),
  clear: () => set({ nodes: [], edges: [] }),
  toBuildingPlan: () => {
    // Placeholder: convert Pascal editor state to BuildingPlan JSON
    // This will be implemented when Pascal editor npm packages are available
    const state = get();
    return {
      description: "Visual editor plan",
      storeys: [],
      elements: [],
      types: [],
    };
  },
}));
