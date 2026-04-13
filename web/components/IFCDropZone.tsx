"use client";

import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileBox, Building2, Sparkles } from "lucide-react";

interface Props {
  onFileLoaded: (blobUrl: string, fileName: string) => void;
}

export default function IFCDropZone({ onFileLoaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".ifc")) {
        alert("Please select a valid .ifc file");
        return;
      }
      setIsProcessing(true);
      const url = URL.createObjectURL(file);
      // Small delay for visual feedback
      setTimeout(() => {
        onFileLoaded(url, file.name);
        setIsProcessing(false);
      }, 300);
    },
    [onFileLoaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [handleFile]
  );

  return (
    <div
      data-testid="ifc-drop-zone"
      className="flex flex-col items-center justify-center h-full bg-canvas"
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".ifc"
        className="hidden"
        onChange={onInputChange}
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md px-8"
      >
        {/* Icon area */}
        <motion.div
          animate={isDragging ? { scale: 1.1, y: -4 } : { scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="mb-6"
        >
          {isDragging ? (
            <div className="relative mx-auto w-20 h-20">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 rounded-2xl border-2 border-dashed border-accent/60"
              />
              <div className="flex items-center justify-center w-full h-full">
                <Upload className="h-9 w-9 text-accent" />
              </div>
            </div>
          ) : (
            <Building2 className="h-16 w-16 text-border mx-auto" />
          )}
        </motion.div>

        {/* Text */}
        <p className="text-sm text-muted mb-1">
          {isProcessing
            ? "Loading model..."
            : isDragging
            ? "Drop your IFC file here"
            : "Describe a building to get started"}
        </p>
        <p className="text-xs text-muted/60 mb-6">
          Your 3D IFC model will appear here
        </p>

        {/* Divider */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1 h-px bg-border" />
          <span className="text-[10px] text-muted/50 uppercase tracking-wider">
            or
          </span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Load IFC button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          data-testid="open-ifc-button"
          onClick={() => inputRef.current?.click()}
          disabled={isProcessing}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg
                     bg-white/[0.06] hover:bg-white/[0.1] border border-border
                     text-sm text-white/80 hover:text-white
                     transition-colors disabled:opacity-50 disabled:pointer-events-none"
        >
          <FileBox className="h-4 w-4" />
          {isProcessing ? "Loading..." : "Open IFC File"}
        </motion.button>

        <p className="text-[10px] text-muted/40 mt-3 flex items-center justify-center gap-1">
          <Sparkles className="h-3 w-3" />
          Drag &amp; drop also supported
        </p>
      </motion.div>
    </div>
  );
}
