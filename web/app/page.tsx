"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { Building2, Sparkles } from "lucide-react";
import AppShell from "@/components/AppShell";
import ChatPanel from "@/components/ChatPanel";
import ModifyPanel from "@/components/ModifyPanel";
import JobStatusBadge from "@/components/JobStatusBadge";
import VisualEditor from "@/components/VisualEditor";
import FloorPlanUpload from "@/components/FloorPlanUpload";
import { useJob } from "@/hooks/useJob";
import { getIfcUrl } from "@/lib/api";

const IFCViewer = dynamic(() => import("@/components/IFCViewer"), { ssr: false });

export default function Home() {
  const { job, dispatch, dispatchFormData } = useJob();
  const [selectedGuids, setSelectedGuids] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"text" | "draw" | "upload">("text");

  const isLoading = job?.status === "queued" || job?.status === "running";
  const ifcUrl = job?.ifc_url ? getIfcUrl(job.ifc_url) : null;

  const handleTextSubmit = useCallback(
    (message: string) => {
      dispatch("generate", { message });
    },
    [dispatch]
  );

  const handleVoiceSubmit = useCallback(
    (blob: Blob) => {
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      dispatchFormData("voice", formData);
    },
    [dispatchFormData]
  );

  const handleFloorPlanUpload = useCallback(
    (file: File, numStoreys: number, floorToFloor: number) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("num_storeys", String(numStoreys));
      formData.append("floor_to_floor_height", String(floorToFloor));
      dispatchFormData("floorplan", formData);
    },
    [dispatchFormData]
  );

  const handlePlanGenerated = useCallback(
    (plan: object) => {
      dispatch("build-from-plan", { plan });
    },
    [dispatch]
  );

  const handleModify = useCallback(
    (guid: string, instruction: string) => {
      if (!job?.ifc_url) return;
      dispatch("modify", { guid, instruction, ifc_url: job.ifc_url });
    },
    [dispatch, job?.ifc_url]
  );

  return (
    <AppShell
      leftPanel={
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-accent/10">
                <Building2 className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-base font-semibold text-white tracking-tight">
                  IFC-GPT
                </h1>
                <div className="flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3 text-accent" />
                  <span className="text-[10px] text-muted font-mono">
                    gpt-5.4-pro
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Tab switcher */}
          <div className="flex border-b border-border">
            <button
              onClick={() => setActiveTab("text")}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === "text"
                  ? "text-accent border-b-2 border-accent"
                  : "text-muted hover:text-white"
              }`}
            >
              Text / Voice
            </button>
            <button
              onClick={() => setActiveTab("draw")}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === "draw"
                  ? "text-accent border-b-2 border-accent"
                  : "text-muted hover:text-white"
              }`}
            >
              Draw
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === "upload"
                  ? "text-accent border-b-2 border-accent"
                  : "text-muted hover:text-white"
              }`}
            >
              Upload
            </button>
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            <AnimatePresence mode="wait">
              {activeTab === "text" ? (
                <motion.div
                  key="text"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChatPanel
                    onSubmit={handleTextSubmit}
                    onVoiceSubmit={handleVoiceSubmit}
                    isLoading={!!isLoading}
                  />
                </motion.div>
              ) : activeTab === "draw" ? (
                <motion.div
                  key="draw"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <VisualEditor onPlanGenerated={handlePlanGenerated} />
                </motion.div>
              ) : (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <FloorPlanUpload
                    onUpload={handleFloorPlanUpload}
                    isLoading={!!isLoading}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Job status */}
          {job && (
            <JobStatusBadge
              status={job.status}
              error={job.error}
            />
          )}

          {/* Modify panel */}
          <AnimatePresence>
            {selectedGuids.length > 0 && (
              <ModifyPanel
                selectedGuids={selectedGuids}
                onModify={handleModify}
                isLoading={!!isLoading}
              />
            )}
          </AnimatePresence>
        </div>
      }
      rightPanel={
        ifcUrl ? (
          <IFCViewer
            ifcUrl={ifcUrl}
            onElementSelected={setSelectedGuids}
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-canvas">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <Building2 className="h-16 w-16 text-border mx-auto mb-4" />
              <p className="text-sm text-muted">
                Describe a building to get started
              </p>
              <p className="text-xs text-muted/60 mt-1">
                Your 3D IFC model will appear here
              </p>
            </motion.div>
          </div>
        )
      }
    />
  );
}
