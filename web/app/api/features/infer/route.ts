import { NextRequest } from "next/server";

import { proxyRequest } from "@/app/api/_proxy";

export const dynamic = "force-dynamic";
export const maxDuration = 600;

export async function POST(req: NextRequest) {
  return proxyRequest(req, "/api/features/infer");
}
