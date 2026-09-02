import { NextRequest, NextResponse } from 'next/server'
import { verifyRecaptcha } from '@/lib/recaptcha'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { user_name, password, authCode, recaptchaValue } = body

    if (!user_name || !password) {
      return NextResponse.json(
        { error: 'Username and password are required' },
        { status: 400 }
      )
    }

    // Verify the reCAPTCHA response - matching your original implementation
    console.log("recaptchaValue: ", recaptchaValue)
    if (recaptchaValue && process.env.RECAPTCHA_SECRET_KEY) {
      const isRecaptchaValid = await verifyRecaptcha(recaptchaValue)
      if (!isRecaptchaValid) {
        return NextResponse.json(
          { error: "reCAPTCHA verification failed" },
          { status: 400 }
        )
      }
    }

    const serverUrl = process.env.SERVER_URL || 'http://netraiserver:4000'
    const endpoint = `${serverUrl}/api/login`

    console.log(`🔐 Proxying login to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
      body: JSON.stringify({
        user_name,
        password,
        authCode: authCode || undefined,
        recaptchaValue // Pass through for server-side verification too
      }),
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: responseData.error || 'Login failed' },
        { status: response.status }
      )
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Login API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
