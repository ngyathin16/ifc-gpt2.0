import { NextRequest, NextResponse } from "next/server";

const BACKEND = "http://127.0.0.1:8000";

export async function proxyRequest(
  req: NextRequest,
  backendPath: string,
  options?: { maxDurationMs?: number; sse?: boolean },
): Promise<NextResponse> {
  const search = req.nextUrl.search;
  const url = `${BACKEND}${backendPath}${search}`;

  try {
    const headers: Record<string, string> = {};
    req.headers.forEach((value, key) => {
      if (key !== "host" && key !== "connection") {
        headers[key] = value;
      }
    });

    const isSSE = options?.sse ?? backendPath.includes("/stream");
    const controller = new AbortController();
    const timeoutMs = options?.maxDurationMs ?? 600_000;
    const timeout = isSSE ? undefined : setTimeout(() => controller.abort(), timeoutMs);

    const res = await fetch(url, {
      method: req.method,
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? await req.arrayBuffer() : undefined,
      signal: isSSE ? undefined : controller.signal,
    });

    if (timeout) {
      clearTimeout(timeout);
    }

    const contentType = res.headers.get("content-type") || "application/json";

    if (contentType.includes("text/event-stream") && res.body) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          "content-type": "text/event-stream",
          "cache-control": "no-cache",
          connection: "keep-alive",
        },
      });
    }

    const data = await res.arrayBuffer();
    return new NextResponse(data, {
      status: res.status,
      headers: {
        "content-type": contentType,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown proxy error";
    console.error("[api proxy]", url, message);
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
