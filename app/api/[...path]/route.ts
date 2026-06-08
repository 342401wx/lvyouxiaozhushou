import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:7861';

const hopByHopHeaders = [
  'connection',
  'content-length',
  'host',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
];

type RouteContext = {
  params: {
    path?: string[];
  };
};

async function proxy(request: NextRequest, context: RouteContext) {
  const path = (context.params.path || []).join('/');
  const sourceUrl = new URL(request.url);
  const targetUrl = new URL(`/api/${path}${sourceUrl.search}`, backendUrl);
  const requestHeaders = new Headers(request.headers);

  for (const header of hopByHopHeaders) {
    requestHeaders.delete(header);
  }

  const hasBody = !['GET', 'HEAD'].includes(request.method);
  const backendResponse = await fetch(targetUrl, {
    method: request.method,
    headers: requestHeaders,
    body: hasBody ? await request.text() : undefined,
    cache: 'no-store',
    redirect: 'manual',
  });

  const responseHeaders = new Headers();
  const contentType = backendResponse.headers.get('content-type');
  const setCookie = backendResponse.headers.get('set-cookie');

  if (contentType) {
    responseHeaders.set('content-type', contentType);
  }

  if (setCookie) {
    responseHeaders.set('set-cookie', setCookie);
  }

  return new NextResponse(await backendResponse.text(), {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
