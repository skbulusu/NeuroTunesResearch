import { NextRequest, NextResponse } from 'next/server'
import { verifyRecaptcha } from '@/lib/recaptcha'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { user_name, authCode, newPassword, recaptchaValue } = body

    if (!user_name || !newPassword || !authCode) {
      return NextResponse.json(
        { error: 'Username, new password, and authCode are required' },
        { status: 400 }
      )
    }

    if (newPassword.length < 8) {
      return NextResponse.json(
        { error: 'New password must be at least 8 characters long' },
        { status: 400 }
      )
    }

    // Verify the reCAPTCHA response - matching your original implementation
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
    const endpoint = `${serverUrl}/api/reset-password`

    console.log(`🔄 Proxying password reset to: ${endpoint}`)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'NeuroTunes-NextJS-Proxy/1.0',
      },
      body: JSON.stringify({
        user_name,
        authCode,
        newPassword,
        recaptchaValue // Pass through for server-side verification too
      }),
    })

    const responseData = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: responseData.error || 'Password reset failed' },
        { status: response.status }
      )
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('❌ Reset Password API Route Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
