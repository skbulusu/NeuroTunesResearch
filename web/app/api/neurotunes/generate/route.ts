import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
  
    console.log('Generating music for patient data:', body)
  
    // Use your actual server URL
    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/solutions/neurotunes/app/generate`

    console.log(`🎵 Proxying music generation to: ${endpoint}`)

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
      console.error('Backend error:', responseData)
      return NextResponse.json(
        { error: responseData.error || 'Music generation failed' },
        { status: response.status }
      )
    }

    // V1 backend already returns the correct structure:
    // { session_id, tracks, patient_state, music_params }
    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Music Generation API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
