"use client";

import { motion } from "framer-motion";
import { Check, Loader2, AlertCircle, Clock } from "lucide-react";
import type { JobStatus } from "@/hooks/useJob";

interface JobStatusBadgeProps {
  status: JobStatus;
  error?: string | null;
}

const statusConfig: Record<JobStatus, { icon: React.ReactNode; label: string; className: string }> = {
  idle: {
    icon: null,
    label: "Ready",
    className: "bg-surface text-muted border-border",
  },
  queued: {
    icon: <Clock className="h-3 w-3" />,
    label: "Queued",
    className: "bg-warning/10 text-warning border-warning/30",
  },
  running: {
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
    label: "Generating",
    className: "bg-accent/10 text-accent border-accent/30",
  },
  complete: {
    icon: <Check className="h-3 w-3" />,
    label: "Complete",
    className: "bg-success/10 text-success border-success/30",
  },
  error: {
    icon: <AlertCircle className="h-3 w-3" />,
    label: "Error",
    className: "bg-danger/10 text-danger border-danger/30",
  },
};

export default function JobStatusBadge({ status, error }: JobStatusBadgeProps) {
  const config = statusConfig[status];

  if (status === "idle") return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="px-4 py-2"
    >
      <div data-testid={`job-status-${status}`} className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium ${config.className}`}>
        {config.icon}
        <span>{config.label}</span>
      </div>
      {error && status === "error" && (
        <p data-testid="job-error-message" className="mt-1 px-1 text-xs text-danger/80 truncate">{error}</p>
      )}
    </motion.div>
  );
}
