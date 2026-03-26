"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Wrench, Send, Loader2 } from "lucide-react";

interface ModifyPanelProps {
  selectedGuids: string[];
  onModify: (guid: string, instruction: string) => void;
  isLoading: boolean;
}

export default function ModifyPanel({ selectedGuids, onModify, isLoading }: ModifyPanelProps) {
  const [instruction, setInstruction] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!instruction.trim() || !selectedGuids.length || isLoading) return;
      onModify(selectedGuids[0], instruction.trim());
      setInstruction("");
    },
    [instruction, selectedGuids, isLoading, onModify]
  );

  if (!selectedGuids.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="p-4 border-t border-border"
    >
      <div className="flex items-center gap-2 mb-3">
        <Wrench className="h-4 w-4 text-accent" />
        <span className="text-sm font-medium text-white">Modify Element</span>
      </div>

      <div className="rounded-lg bg-surface border border-border p-2 mb-3">
        <p className="text-xs text-muted">Selected GUID</p>
        <p className="text-xs font-mono text-white truncate">{selectedGuids[0]}</p>
        {selectedGuids.length > 1 && (
          <p className="text-xs text-muted mt-1">+{selectedGuids.length - 1} more</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-2">
        <input
          type="text"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="e.g. Change wall height to 4m..."
          className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
        />
        <button
          type="submit"
          disabled={isLoading || !instruction.trim()}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-medium text-white transition-all"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          {isLoading ? "Modifying..." : "Apply"}
        </button>
      </form>
    </motion.div>
  );
}
