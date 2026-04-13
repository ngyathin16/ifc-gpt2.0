"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Columns3,
  DoorOpen,
  Layers,
  ArrowUpDown,
  Home,
  Check,
  Loader2,
  ChevronDown,
  Sparkles,
} from "lucide-react";
import type { FeatureItem, InferredDefaults } from "@/lib/api";

interface FeaturePickerProps {
  features: FeatureItem[];
  defaults: InferredDefaults;
  onConfirm: (selectedFeatures: string[], floorToFloorHeight: number) => void;
  onCancel: () => void;
  isLoading: boolean;
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Structure: <Columns3 className="h-3.5 w-3.5" />,
  Facade: <Building2 className="h-3.5 w-3.5" />,
  "Vertical Circulation": <ArrowUpDown className="h-3.5 w-3.5" />,
  Roof: <Layers className="h-3.5 w-3.5" />,
  Interior: <DoorOpen className="h-3.5 w-3.5" />,
  "Ground Floor": <Home className="h-3.5 w-3.5" />,
};

export default function FeaturePicker({
  features,
  defaults,
  onConfirm,
  onCancel,
  isLoading,
}: FeaturePickerProps) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(defaults.default_features)
  );
  const [floorHeight, setFloorHeight] = useState<number>(defaults.floor_to_floor_height);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSelected(new Set(defaults.default_features));
    setFloorHeight(defaults.floor_to_floor_height);
    // Auto-expand all categories
    const cats = new Set(features.map((f) => f.category));
    setExpandedCats(cats);
  }, [defaults, features]);

  const grouped = useMemo(() => {
    const map = new Map<string, FeatureItem[]>();
    for (const f of features) {
      if (!map.has(f.category)) map.set(f.category, []);
      map.get(f.category)!.push(f);
    }
    return map;
  }, [features]);

  const toggle = useCallback(
    (id: string) => {
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
          // Remove conflicting features
          const feat = features.find((f) => f.id === id);
          if (feat?.conflicts_with) {
            for (const cid of feat.conflicts_with) {
              next.delete(cid);
            }
          }
        }
        return next;
      });
    },
    [features]
  );

  const toggleCat = useCallback((cat: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.25 }}
      className="p-4 space-y-3"
      data-testid="feature-picker"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-4 w-4 text-accent" />
        <span className="text-sm font-semibold text-white">
          Building Features
        </span>
      </div>

      {/* Inferred info */}
      <div className="rounded-lg bg-surface border border-border p-3 space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-muted">Type</span>
          <span className="text-white font-medium capitalize">
            {defaults.building_type}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted">Storeys</span>
          <span className="text-white font-medium">
            {defaults.num_storeys}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted">Floor height (m)</span>
          <input
            type="number"
            min={2.4}
            max={6.0}
            step={0.1}
            value={floorHeight}
            onChange={(e) => setFloorHeight(parseFloat(e.target.value) || 3.0)}
            className="w-16 rounded bg-canvas border border-border px-2 py-0.5 text-xs text-white text-right focus:outline-none focus:ring-1 focus:ring-accent/50"
          />
        </div>
      </div>

      {/* Feature groups */}
      <div className="space-y-1 max-h-[340px] overflow-y-auto pr-1">
        {Array.from(grouped.entries()).map(([cat, items]) => (
          <div key={cat}>
            <button
              onClick={() => toggleCat(cat)}
              className="flex items-center gap-2 w-full py-1.5 text-xs font-medium text-muted hover:text-white transition-colors"
            >
              {CATEGORY_ICONS[cat] ?? <Layers className="h-3.5 w-3.5" />}
              <span className="flex-1 text-left">{cat}</span>
              <span className="text-[10px] text-muted/60 mr-1">
                {items.filter((f) => selected.has(f.id)).length}/{items.length}
              </span>
              <ChevronDown
                className={`h-3 w-3 transition-transform ${
                  expandedCats.has(cat) ? "rotate-180" : ""
                }`}
              />
            </button>

            <AnimatePresence>
              {expandedCats.has(cat) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  {items.map((feat) => {
                    const isOn = selected.has(feat.id);
                    return (
                      <button
                        key={feat.id}
                        onClick={() => toggle(feat.id)}
                        className={`flex items-start gap-2.5 w-full rounded-md px-2.5 py-2 mb-0.5 text-left transition-all ${
                          isOn
                            ? "bg-accent/10 border border-accent/30"
                            : "bg-surface/50 border border-transparent hover:border-border"
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex items-center justify-center w-4 h-4 rounded border transition-all shrink-0 ${
                            isOn
                              ? "bg-accent border-accent"
                              : "border-muted/50"
                          }`}
                        >
                          {isOn && (
                            <Check className="h-2.5 w-2.5 text-white" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p
                            className={`text-xs font-medium ${
                              isOn ? "text-white" : "text-muted"
                            }`}
                          >
                            {feat.label}
                          </p>
                          <p className="text-[10px] text-muted/70 leading-tight mt-0.5">
                            {feat.description}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          data-testid="feature-back-button"
          onClick={onCancel}
          disabled={isLoading}
          className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-muted hover:text-white hover:border-accent/50 transition-all disabled:opacity-50"
        >
          Back
        </button>
        <button
          data-testid="feature-confirm-button"
          onClick={() => onConfirm(Array.from(selected), floorHeight)}
          disabled={isLoading || selected.size === 0}
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2.5 text-sm font-medium text-white transition-all"
        >
          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Loader2 className="h-4 w-4 animate-spin" />
              </motion.div>
            ) : (
              <motion.div
                key="go"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Building2 className="h-4 w-4" />
              </motion.div>
            )}
          </AnimatePresence>
          {isLoading ? "Generating..." : `Generate (${selected.size})`}
        </button>
      </div>
    </motion.div>
  );
}
