import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function notFoundHandler(req: NextRequest): Promise<NextResponse> {
  return NextResponse.json(
    { error: `No explicit Next API proxy route is defined for ${req.nextUrl.pathname}` },
    { status: 404 },
  );
}

export const GET = notFoundHandler;
export const POST = notFoundHandler;
export const PUT = notFoundHandler;
export const DELETE = notFoundHandler;
export const PATCH = notFoundHandler;
