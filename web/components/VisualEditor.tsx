"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { Pencil, Trash2, Send } from "lucide-react";
import { usePascalEditor } from "@/hooks/usePascalEditor";
import { toPlanJSON } from "@/lib/toPlanJSON";

interface VisualEditorProps {
  onPlanGenerated?: (plan: object) => void;
}

export default function VisualEditor({ onPlanGenerated }: VisualEditorProps) {
  const { nodes, clear, toBuildingPlan } = usePascalEditor();

  const handleGenerate = useCallback(() => {
    const sceneData = toBuildingPlan();
    const plan = toPlanJSON(sceneData);
    onPlanGenerated?.(plan);
  }, [toBuildingPlan, onPlanGenerated]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-64 rounded-lg border border-dashed border-border bg-surface/50 m-4"
    >
      <Pencil className="h-8 w-8 text-muted mb-3" />
      <p className="text-sm text-muted text-center px-4">
        Pascal visual editor will be available here.
      </p>
      <p className="text-xs text-muted/60 mt-1">
        Draw walls, levels, and spaces to generate BuildingPlan JSON.
      </p>
      {nodes.length > 0 && (
        <div className="flex gap-2 mt-4">
          <button
            onClick={clear}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted hover:text-white bg-surface rounded-md border border-border transition-colors"
          >
            <Trash2 className="h-3 w-3" />
            Clear
          </button>
          <button
            onClick={handleGenerate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white bg-accent/80 hover:bg-accent rounded-md transition-colors"
          >
            <Send className="h-3 w-3" />
            Generate
          </button>
        </div>
      )}
    </motion.div>
  );
}
