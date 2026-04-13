import { NextRequest } from "next/server";

import { proxyRequest } from "@/app/api/_proxy";

export const dynamic = "force-dynamic";
export const maxDuration = 600;

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;
  return proxyRequest(req, `/api/status/${jobId}/stream`, { sse: true });
}
