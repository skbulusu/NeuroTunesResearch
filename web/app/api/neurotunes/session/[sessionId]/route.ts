import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await context.params

    if (!sessionId) {
      return NextResponse.json(
        { error: 'Session ID is required' },
        { status: 400 }
      )
    }

    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/neurotunes/session/${sessionId}`

    console.log(`📋 Proxying session request to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: responseData.error || 'Session not found' },
        { status: response.status }
      )
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Session API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
