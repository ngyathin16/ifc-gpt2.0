"use client";
import { useEffect, useState } from "react";

const API = "";

export type JobStatus = "idle" | "queued" | "running" | "complete" | "error";

export interface Job {
  job_id: string;
  status: JobStatus;
  ifc_url: string | null;
  error: string | null;
}

export function useJob() {
  const [job, setJob] = useState<Job | null>(null);

  const dispatch = async (endpoint: string, body: object): Promise<string> => {
    const url = `${API}/api/${endpoint}`;
    console.log("[useJob] POST", url, body);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      console.log("[useJob] response status:", res.status);
      const text = await res.text();
      console.log("[useJob] response body:", text);
      const data = JSON.parse(text);
      setJob({ ...data, ifc_url: null });
      return data.job_id;
    } catch (err: any) {
      console.error("[useJob] dispatch FAILED:", err);
      setJob({ job_id: "error", status: "error", ifc_url: null, error: err.message || "Connection error" });
      return "error";
    }
  };

  const dispatchFormData = async (endpoint: string, formData: FormData): Promise<string> => {
    try {
      const res = await fetch(`${API}/api/${endpoint}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setJob({ ...data, ifc_url: null });
      return data.job_id;
    } catch (err: any) {
      console.error("[useJob] dispatchFormData error:", err);
      setJob({ job_id: "error", status: "error", ifc_url: null, error: err.message || "Connection error" });
      return "error";
    }
  };

  useEffect(() => {
    if (!job?.job_id || job.status === "complete" || job.status === "error") return;
    const jobId = job.job_id;
    let closed = false;

    const pollFinalStatus = async () => {
      if (closed) return;
      try {
        const res = await fetch(`${API}/api/status/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === "complete" || data.status === "error") {
          setJob((prev) => ({ ...prev!, ...data }));
        }
      } catch {
        /* fallback poll failed — non-fatal */
      }
    };

    const es = new EventSource(`${API}/api/status/${jobId}/stream`);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setJob((prev) => ({ ...prev!, ...data }));
        if (data.status === "complete" || data.status === "error") {
          closed = true;
          es.close();
        }
      } catch {
        /* malformed SSE data — ignore */
      }
    };
    es.onerror = () => {
      es.close();
      if (!closed) pollFinalStatus();
    };
    return () => {
      closed = true;
      es.close();
    };
  }, [job?.job_id]);

  return { job, dispatch, dispatchFormData, setJob };
}
