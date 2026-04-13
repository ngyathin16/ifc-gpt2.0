import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

export const dynamic = "force-static";

export async function GET(req: Request): Promise<NextResponse> {
  const url = new URL(req.url);
  const requestedFile = url.searchParams.get("file");
  if (requestedFile && requestedFile !== "web-ifc.wasm") {
    return NextResponse.json({ error: `Unsupported wasm file: ${requestedFile}` }, { status: 404 });
  }

  const wasmPath = path.join(process.cwd(), "public", requestedFile ?? "web-ifc.wasm");
  const wasm = await readFile(wasmPath);

  return new NextResponse(wasm, {
    status: 200,
    headers: {
      "content-type": "application/wasm",
      "cache-control": "public, max-age=31536000, immutable",
    },
  });
}
