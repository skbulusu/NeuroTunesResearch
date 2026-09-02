import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const serverUrl = process.env.SERVER_URL || 'http://netraiserver:4000'
    const endpoint = `${serverUrl}/api/getCurrentUser`

    console.log(`👤 Proxying current user to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
        'Authorization': request.headers.get('Authorization') || '',
      },
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: responseData.error || 'Failed to get current user' },
        { status: response.status }
      )
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Current User API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
