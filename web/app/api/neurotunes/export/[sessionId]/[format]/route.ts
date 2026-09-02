import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string; format: string }> }
) {
  try {
    const { sessionId, format } = await context.params

    if (!sessionId || !format) {
      return NextResponse.json(
        { error: 'Session ID and format are required' },
        { status: 400 }
      )
    }

    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/neurotunes/export/${sessionId}/${format}`

    console.log(`📤 Proxying export request to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
    })

    if (!response.ok) {
      const responseData = await response.json()
      return NextResponse.json(
        { error: responseData.error || 'Export failed' },
        { status: response.status }
      )
    }

    // Handle different content types
    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const buffer = await response.arrayBuffer()

    // Set appropriate filename
    const filename = `neurotunes_session_${sessionId}.${format}`

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })

  } catch (error) {
    console.error('❌ Export API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
