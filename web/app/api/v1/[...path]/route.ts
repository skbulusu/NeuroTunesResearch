// ====================================================================
// Next.js proxy for the versioned research API  —  /api/v1/*
// --------------------------------------------------------------------
// Mirrors the existing /api/neurotunes proxy pattern: forwards requests
// from the Next.js client to the Express server's /api/v1 router, passing
// through the X-API-Key header and query string. Additive — it does not
// affect any existing route.
// ====================================================================

import { NextRequest, NextResponse } from 'next/server'

const SERVER_URL = process.env.SERVER_URL || 'http://192.168.10.151:4000'

function targetUrl(req: NextRequest, path: string[]): string {
  const search = req.nextUrl.search || ''
  return `${SERVER_URL}/api/v1/${path.join('/')}${search}`
}

function forwardHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const apiKey = req.headers.get('x-api-key')
  if (apiKey) headers['X-API-Key'] = apiKey
  return headers
}

async function relay(upstream: Response): Promise<NextResponse> {
  const contentType = upstream.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const data = await upstream.json().catch(() => ({}))
    return NextResponse.json(data, { status: upstream.status })
  }
  const buffer = await upstream.arrayBuffer()
  return new NextResponse(buffer, {
    status: upstream.status,
    headers: {
      'Content-Type': contentType || 'application/octet-stream',
      'Content-Disposition': upstream.headers.get('content-disposition') || '',
    },
  })
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await context.params
    const upstream = await fetch(targetUrl(req, path), {
      method: 'GET',
      headers: forwardHeaders(req),
    })
    return await relay(upstream)
  } catch (e: any) {
    return NextResponse.json(
      { error: 'proxy_error', message: e?.message || 'Upstream unreachable' },
      { status: 502 }
    )
  }
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await context.params
    const body = await req.text()
    const upstream = await fetch(targetUrl(req, path), {
      method: 'POST',
      headers: forwardHeaders(req),
      body,
    })
    return await relay(upstream)
  } catch (e: any) {
    return NextResponse.json(
      { error: 'proxy_error', message: e?.message || 'Upstream unreachable' },
      { status: 502 }
    )
  }
}
