import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/neurotunes/health`

    console.log(`🏥 Checking backend health at: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
      signal: AbortSignal.timeout(5000)
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { 
          status: 'unhealthy',
          error: responseData.error || 'Backend service unavailable',
          timestamp: new Date().toISOString()
        },
        { status: response.status }
      )
    }

    return NextResponse.json({
      ...responseData,
      frontend: {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '2.0.0'
      }
    })

  } catch (error) {
    console.error('❌ Health Check API Route Error:', error)
  
    const isTimeout = error instanceof Error && error.name === 'TimeoutError'
    const isConnectionError = error instanceof Error && error.message.includes('fetch')

    return NextResponse.json(
      { 
        status: 'unhealthy',
        error: isTimeout ? 'Backend timeout' : isConnectionError ? 'Backend unreachable' : 'Health check failed',
        timestamp: new Date().toISOString(),
        frontend: {
          status: 'healthy',
          timestamp: new Date().toISOString(),
          version: '2.0.0'
        }
      },
      { status: 503 }
    )
  }
}
