"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Mic, MicOff, Loader2, ArrowRight } from "lucide-react";

interface ChatPanelProps {
  onSubmit: (message: string) => void;
  onVoiceSubmit: (blob: Blob) => void;
  onInferFeatures: (message: string) => void;
  isLoading: boolean;
  isInferring: boolean;
}

export default function ChatPanel({
  onSubmit,
  onVoiceSubmit,
  onInferFeatures,
  isLoading,
  isInferring,
}: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const handleNext = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!message.trim() || isLoading || isInferring) return;
      onInferFeatures(message.trim());
    },
    [message, isLoading, isInferring, onInferFeatures]
  );

  const handleQuickGenerate = useCallback(
    () => {
      if (!message.trim() || isLoading) return;
      onSubmit(message.trim());
      setMessage("");
    },
    [message, isLoading, onSubmit]
  );

  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        onVoiceSubmit(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      console.error("Microphone access denied");
    }
  }, [isRecording, onVoiceSubmit]);

  const busy = isLoading || isInferring;

  return (
    <div className="p-4 space-y-3" data-testid="chat-panel">
      <form onSubmit={handleNext} className="space-y-3">
        <textarea
          data-testid="chat-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describe a building to generate...&#10;e.g. 15-storey residential tower with balconies"
          className="w-full min-h-[120px] resize-none rounded-lg bg-surface border border-border p-3 text-sm text-white placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleNext(e);
            }
          }}
        />

        <div className="flex items-center gap-2">
          <button
            data-testid="next-button"
            type="submit"
            disabled={busy || !message.trim()}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2.5 text-sm font-medium text-white transition-all"
          >
            <AnimatePresence mode="wait">
              {isInferring ? (
                <motion.div key="inferring" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <Loader2 className="h-4 w-4 animate-spin" />
                </motion.div>
              ) : (
                <motion.div key="next" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <ArrowRight className="h-4 w-4" />
                </motion.div>
              )}
            </AnimatePresence>
            {isInferring ? "Analyzing..." : "Next — Pick Features"}
          </button>

          <button
            data-testid="voice-button"
            type="button"
            onClick={toggleRecording}
            disabled={busy}
            className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
              isRecording
                ? "bg-danger text-white animate-pulse-fast"
                : "bg-surface border border-border text-muted hover:text-white hover:border-accent/50"
            } disabled:opacity-50`}
          >
            {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </button>
        </div>
      </form>

      <p className="text-[10px] text-muted/50 text-center">
        Press Enter or click Next to choose building features before generating.
      </p>
    </div>
  );
}
