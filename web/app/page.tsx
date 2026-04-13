"use client";

import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { Building2, Sparkles, FolderOpen } from "lucide-react";
import AppShell from "@/components/AppShell";
import ChatPanel from "@/components/ChatPanel";
import FeaturePicker from "@/components/FeaturePicker";
import ModifyPanel from "@/components/ModifyPanel";
import JobStatusBadge from "@/components/JobStatusBadge";
import VisualEditor from "@/components/VisualEditor";
import FloorPlanUpload from "@/components/FloorPlanUpload";
import IFCDropZone from "@/components/IFCDropZone";
import { useJob } from "@/hooks/useJob";
import {
  getIfcUrl,
  getFeatures,
  inferFeatures,
  type FeatureItem,
  type InferredDefaults,
} from "@/lib/api";

const IFCViewer = dynamic(() => import("@/components/IFCViewer"), { ssr: false });

type Step = "prompt" | "features" | "generating";

export default function Home() {
  const { job, dispatch, dispatchFormData } = useJob();
  const [selectedGuids, setSelectedGuids] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"text" | "draw" | "upload">("text");
  const [userIfcUrl, setUserIfcUrl] = useState<string | null>(null);
  const [userIfcName, setUserIfcName] = useState<string>("");

  // Feature-picking state
  const [step, setStep] = useState<Step>("prompt");
  const [pendingMessage, setPendingMessage] = useState("");
  const [featureCatalog, setFeatureCatalog] = useState<FeatureItem[]>([]);
  const [inferredDefaults, setInferredDefaults] = useState<InferredDefaults | null>(null);
  const [isInferring, setIsInferring] = useState(false);

  const isLoading = job?.status === "queued" || job?.status === "running";
  const jobIfcUrl = job?.ifc_url ? getIfcUrl(job.ifc_url) : null;
  const ifcUrl = userIfcUrl ?? jobIfcUrl;

  const handleIfcFileLoaded = useCallback((blobUrl: string, fileName: string) => {
    setUserIfcUrl(blobUrl);
    setUserIfcName(fileName);
  }, []);

  const handleClearUserIfc = useCallback(() => {
    if (userIfcUrl) URL.revokeObjectURL(userIfcUrl);
    setUserIfcUrl(null);
    setUserIfcName("");
  }, [userIfcUrl]);

  // Fetch feature catalog once on mount
  useEffect(() => {
    getFeatures()
      .then(setFeatureCatalog)
      .catch((err) => console.error("Failed to load features:", err));
  }, []);

  // Step 1 → 2: User submits prompt, infer default features
  const handleInferFeatures = useCallback(
    async (message: string) => {
      setPendingMessage(message);
      setIsInferring(true);
      try {
        const defaults = await inferFeatures(message);
        setInferredDefaults(defaults);
        setStep("features");
      } catch (err) {
        console.error("Feature inference failed:", err);
        // Fallback: skip feature picking, generate directly
        dispatch("generate", { message });
        setStep("generating");
      } finally {
        setIsInferring(false);
      }
    },
    [dispatch]
  );

  // Step 2 → 3: User confirms features, generate
  const handleFeatureConfirm = useCallback(
    (selectedFeatures: string[], floorToFloorHeight?: number) => {
      dispatch("generate", {
        message: pendingMessage,
        selected_features: selectedFeatures,
        floor_to_floor_height: floorToFloorHeight,
      });
      setStep("generating");
    },
    [dispatch, pendingMessage]
  );

  // Back from feature picker to prompt
  const handleFeatureCancel = useCallback(() => {
    setStep("prompt");
    setInferredDefaults(null);
  }, []);

  // Quick submit (skip feature picking — for voice etc.)
  const handleTextSubmit = useCallback(
    (message: string) => {
      dispatch("generate", { message });
      setStep("generating");
    },
    [dispatch]
  );

  // Reset to prompt step when job completes or errors
  useEffect(() => {
    if (job?.status === "complete" || job?.status === "error") {
      setStep("prompt");
    }
  }, [job?.status]);

  const handleVoiceSubmit = useCallback(
    (blob: Blob) => {
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      dispatchFormData("voice", formData);
      setStep("generating");
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
              data-testid="tab-text"
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
              data-testid="tab-draw"
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
              data-testid="tab-upload"
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
                  key={step === "features" ? "features" : "text"}
                  initial={{ opacity: 0, x: step === "features" ? 10 : -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: step === "features" ? -10 : 10 }}
                  transition={{ duration: 0.2 }}
                >
                  {step === "features" && inferredDefaults ? (
                    <FeaturePicker
                      features={featureCatalog}
                      defaults={inferredDefaults}
                      onConfirm={handleFeatureConfirm}
                      onCancel={handleFeatureCancel}
                      isLoading={!!isLoading}
                    />
                  ) : (
                    <ChatPanel
                      onSubmit={handleTextSubmit}
                      onVoiceSubmit={handleVoiceSubmit}
                      onInferFeatures={handleInferFeatures}
                      isLoading={!!isLoading}
                      isInferring={isInferring}
                    />
                  )}
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
            <div data-testid="job-status-area">
              <JobStatusBadge
                status={job.status}
                error={job.error}
              />
            </div>
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
          <div className="relative w-full h-full">
            <IFCViewer
              ifcUrl={ifcUrl}
              onElementSelected={setSelectedGuids}
            />
            {/* Toolbar overlay */}
            <div className="absolute top-3 right-3 flex items-center gap-2 z-10">
              {userIfcUrl && (
                <motion.span
                  initial={{ opacity: 0, x: 5 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-[10px] text-white/50 bg-black/40 backdrop-blur px-2 py-1 rounded"
                >
                  {userIfcName}
                </motion.span>
              )}
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  const input = document.createElement("input");
                  input.type = "file";
                  input.accept = ".ifc";
                  input.onchange = () => {
                    const file = input.files?.[0];
                    if (file) handleIfcFileLoaded(URL.createObjectURL(file), file.name);
                  };
                  input.click();
                }}
                className="p-2 rounded-lg bg-black/40 backdrop-blur border border-white/10
                           hover:bg-black/60 text-white/70 hover:text-white transition-colors"
                title="Open IFC file"
              >
                <FolderOpen className="h-4 w-4" />
              </motion.button>
              {userIfcUrl && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleClearUserIfc}
                  className="p-2 rounded-lg bg-black/40 backdrop-blur border border-white/10
                             hover:bg-red-900/40 text-white/70 hover:text-white transition-colors
                             text-xs px-2.5"
                  title="Close uploaded file"
                >
                  ✕
                </motion.button>
              )}
            </div>
          </div>
        ) : (
          <IFCDropZone onFileLoaded={handleIfcFileLoaded} />
        )
      }
    />
  );
}
