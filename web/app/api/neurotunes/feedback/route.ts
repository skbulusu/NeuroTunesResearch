import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
  
    console.log('Forwarding feedback to backend:', body)
  
    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/neurotunes/feedback`

    console.log(`📝 Proxying feedback submission to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
      body: JSON.stringify(body),
    })

    const responseData = await response.json()

    if (!response.ok) {
      console.error('Backend feedback error:', responseData)
      return NextResponse.json(
        { error: responseData.error || 'Feedback submission failed' },
        { status: response.status }
      )
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Feedback API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
