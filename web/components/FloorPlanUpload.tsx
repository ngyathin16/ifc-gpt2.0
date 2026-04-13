"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileImage, Loader2, X, ChevronDown } from "lucide-react";

interface FloorPlanUploadProps {
  onUpload: (file: File, numStoreys: number, floorToFloor: number) => void;
  isLoading: boolean;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/tiff",
  "image/bmp",
  "image/webp",
];

const ACCEPTED_EXTENSIONS = ".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp";

export default function FloorPlanUpload({ onUpload, isLoading }: FloorPlanUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [numStoreys, setNumStoreys] = useState(1);
  const [floorToFloor, setFloorToFloor] = useState(3.0);
  const [showOptions, setShowOptions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer.files?.[0];
    if (file && isAcceptedFile(file)) {
      setSelectedFile(file);
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }, []);

  const handleSubmit = useCallback(() => {
    if (!selectedFile || isLoading) return;
    onUpload(selectedFile, numStoreys, floorToFloor);
  }, [selectedFile, numStoreys, floorToFloor, isLoading, onUpload]);

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  return (
    <div className="p-4 space-y-3" data-testid="floorplan-upload">
      {/* Drop zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 cursor-pointer transition-all ${
          dragActive
            ? "border-accent bg-accent/10"
            : selectedFile
            ? "border-success/50 bg-success/5"
            : "border-border hover:border-accent/50 bg-surface"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleFileChange}
          className="hidden"
        />

        <AnimatePresence mode="wait">
          {selectedFile ? (
            <motion.div
              key="selected"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center gap-3"
            >
              <FileImage className="h-8 w-8 text-success" />
              <div>
                <p className="text-sm font-medium text-white truncate max-w-[200px]">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted">
                  {(selectedFile.size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  clearFile();
                }}
                className="p-1 rounded hover:bg-surface"
              >
                <X className="h-4 w-4 text-muted" />
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="text-center"
            >
              <Upload className="h-8 w-8 text-muted mx-auto mb-2" />
              <p className="text-sm text-muted">
                Drop a floor plan here or click to browse
              </p>
              <p className="text-xs text-muted/60 mt-1">
                PDF, PNG, JPEG, TIFF, BMP
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Options toggle */}
      {selectedFile && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="space-y-3"
        >
          <button
            onClick={() => setShowOptions(!showOptions)}
            className="flex items-center gap-1.5 text-xs text-muted hover:text-white transition-colors"
          >
            <ChevronDown
              className={`h-3 w-3 transition-transform ${showOptions ? "rotate-180" : ""}`}
            />
            Options
          </button>

          <AnimatePresence>
            {showOptions && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-3 overflow-hidden"
              >
                <div>
                  <label className="block text-xs text-muted mb-1">
                    Number of storeys
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={numStoreys}
                    onChange={(e) => setNumStoreys(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted mb-1">
                    Floor-to-floor height (m)
                  </label>
                  <input
                    type="number"
                    min={2.4}
                    max={6.0}
                    step={0.1}
                    value={floorToFloor}
                    onChange={(e) => setFloorToFloor(parseFloat(e.target.value) || 3.0)}
                    className="w-full rounded-lg bg-surface border border-border px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent/50"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit button */}
          <button
            data-testid="floorplan-submit"
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2.5 text-sm font-medium text-white transition-all"
          >
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <Loader2 className="h-4 w-4 animate-spin" />
                </motion.div>
              ) : (
                <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <Upload className="h-4 w-4" />
                </motion.div>
              )}
            </AnimatePresence>
            {isLoading ? "Processing..." : "Convert to IFC"}
          </button>
        </motion.div>
      )}
    </div>
  );
}

function isAcceptedFile(file: File): boolean {
  return ACCEPTED_TYPES.includes(file.type) || /\.(pdf|png|jpe?g|tiff?|bmp|webp)$/i.test(file.name);
}
