import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_PROXY_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";
const FORWARDED_HEADERS = ["accept", "content-type", "if-none-match"];

function buildProxyUrl(request: NextRequest, path: string[]): URL {
  const target = new URL(`${API_PROXY_TARGET}/api/${path.join("/")}`);
  target.search = new URL(request.url).search;
  return target;
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();

  FORWARDED_HEADERS.forEach((name) => {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  });

  return headers;
}

async function proxyRequest(
  request: NextRequest,
  context: { params: { path: string[] } }
): Promise<NextResponse> {
  const target = buildProxyUrl(request, context.params.path);
  const headers = buildForwardHeaders(request);
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "API unavailable" },
      { status: 503 }
    );
  }

  const responseHeaders = new Headers();
  const contentType = upstream.headers.get("content-type");
  if (contentType) {
    responseHeaders.set("content-type", contentType);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: { path: string[] } }
) {
  return proxyRequest(request, context);
}
