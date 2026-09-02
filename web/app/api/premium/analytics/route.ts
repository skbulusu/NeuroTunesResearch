import { NextRequest, NextResponse } from 'next/server'

// API Route: /api/premium/analytics
export async function POST(request: NextRequest) {
  try {
    const { user_name } = await request.json()
    
    if (!user_name) {
      return NextResponse.json(
        { error: 'User name is required' },
        { status: 400 }
      )
    }

    // Call your Node.js backend to get analytics data
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:4000'
    
    const response = await fetch(`${backendUrl}/api/premium/analytics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_name })
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`)
    }

    const analyticsData = await response.json()
    
    return NextResponse.json(analyticsData)
    
  } catch (error) {
    console.error('Analytics API error:', error)
    
    // Return mock analytics data for development/demo
    const mockAnalyticsData = {
      mood_trends: {
        dates: [
          '2025-08-10', '2025-08-11', '2025-08-12', '2025-08-13', 
          '2025-08-14', '2025-08-15', '2025-08-16', '2025-08-17'
        ],
        mood_scores: [6.2, 6.8, 7.1, 6.9, 7.3, 7.8, 8.1, 8.0],
        stress_levels: [7.5, 6.8, 6.2, 5.9, 5.4, 4.8, 4.2, 4.0],
        energy_levels: [5.8, 6.1, 6.5, 6.8, 7.2, 7.5, 7.8, 8.0]
      },
      therapy_effectiveness: {
        overall_improvement: 23,
        session_count: 12,
        avg_rating: 4.2,
        most_effective_goal: 'Anxiety Relief'
      },
      usage_stats: {
        total_generations: 28,
        total_listening_minutes: 340,
        favorite_tempo_range: '60-80 BPM',
        preferred_therapy_goals: ['Anxiety Relief', 'Sleep Enhancement', 'Focus Improvement']
      }
    }
    
    return NextResponse.json(mockAnalyticsData)
  }
}

export async function GET() {
  return NextResponse.json(
    { error: 'Method not allowed. Use POST.' },
    { status: 405 }
  )
}
