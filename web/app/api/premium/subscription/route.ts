import { NextRequest, NextResponse } from 'next/server'

// API Route: /api/premium/subscription
export async function POST(request: NextRequest) {
  try {
    const { user_name } = await request.json()
    
    if (!user_name) {
      return NextResponse.json(
        { error: 'User name is required' },
        { status: 400 }
      )
    }

    // Call your Flask backend to get subscription status
    const backendUrl = process.env.FLASK_BACKEND_URL || 'http://localhost:5000'
    
    const response = await fetch(`${backendUrl}/api/premium/subscription`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_name })
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const subscriptionData = await response.json()
    
    return NextResponse.json(subscriptionData)
    
  } catch (error) {
    console.error('Subscription API error:', error)
    
    // Return mock data for development/demo
    const mockSubscriptionData = {
      subscription_status: 'trial',
      plan_name: 'Basic',
      plan_type: 'basic',
      has_active_subscription: false,
      can_generate_music: true,
      can_create_session: true,
      generations_used_this_month: 3,
      sessions_used_this_month: 2,
      max_generations_per_month: 10,
      max_sessions_per_month: 5,
      trial_end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      subscription_end_date: null,
      irb_compliance_enabled: false,
      advanced_analytics_enabled: false
    }
    
    return NextResponse.json(mockSubscriptionData)
  }
}

export async function GET() {
  return NextResponse.json(
    { error: 'Method not allowed. Use POST.' },
    { status: 405 }
  )
}
