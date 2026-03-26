import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://127.0.0.1:8000";

async function handler(req: NextRequest) {
  const path = req.nextUrl.pathname;
  const search = req.nextUrl.search;
  const url = `${BACKEND}${path}${search}`;

  try {
    const headers: Record<string, string> = {};
    req.headers.forEach((v, k) => {
      if (k !== "host" && k !== "connection") headers[k] = v;
    });

    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? await req.arrayBuffer() : undefined,
    });

    const ct = res.headers.get("content-type") || "";

    // Stream SSE responses
    if (ct.includes("text/event-stream") && res.body) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          "content-type": "text/event-stream",
          "cache-control": "no-cache",
          "connection": "keep-alive",
        },
      });
    }

    // Buffer normal responses
    const data = await res.arrayBuffer();
    return new NextResponse(data, {
      status: res.status,
      headers: { "content-type": ct || "application/json" },
    });
  } catch (err: any) {
    console.error("[api proxy]", url, err.message);
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
