"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { 
  Brain, 
  TrendingUp, 
  Calendar, 
  Music, 
  BarChart3, 
  Download, 
  Crown, 
  Lock,
  CheckCircle,
  AlertCircle,
  Clock,
  Target,
  Activity,
  Heart,
  Zap
} from 'lucide-react'

interface SubscriptionStatus {
  subscription_status: string
  plan_name: string
  plan_type: string
  has_active_subscription: boolean
  can_generate_music: boolean
  can_create_session: boolean
  generations_used_this_month: number
  sessions_used_this_month: number
  max_generations_per_month: number
  max_sessions_per_month: number
  trial_end_date?: string
  subscription_end_date?: string
  irb_compliance_enabled: boolean
  advanced_analytics_enabled: boolean
}

interface AnalyticsData {
  mood_trends: {
    dates: string[]
    mood_scores: number[]
    stress_levels: number[]
    energy_levels: number[]
  }
  therapy_effectiveness: {
    overall_improvement: number
    session_count: number
    avg_rating: number
    most_effective_goal: string
  }
  usage_stats: {
    total_generations: number
    total_listening_minutes: number
    favorite_tempo_range: string
    preferred_therapy_goals: string[]
  }
}

interface PatientDashboardProps {
  userName?: string
  isPremiumMode: boolean
  onUpgrade: () => void
}

export function PatientDashboard({ userName, isPremiumMode, onUpgrade }: PatientDashboardProps) {
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("overview")

  useEffect(() => {
    fetchDashboardData()
  }, [userName])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Fetch subscription status
      const subResponse = await fetch('/api/premium/subscription', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName })
      })
      
      if (subResponse.ok) {
        const subData = await subResponse.json()
        setSubscriptionStatus(subData)
      }

      // Fetch analytics data (only if premium)
      if (isPremiumMode) {
        const analyticsResponse = await fetch('/api/premium/analytics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_name: userName })
        })
        
        if (analyticsResponse.ok) {
          const analyticsData = await analyticsResponse.json()
          setAnalyticsData(analyticsData)
        }
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const exportData = async (format: 'csv' | 'pdf') => {
    try {
      const response = await fetch('/api/premium/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_name: userName, 
          format,
          data_type: 'analytics'
        })
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `neurotunes_analytics_${userName}_${new Date().toISOString().split('T')[0]}.${format}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const PremiumFeatureLock = ({ children, feature }: { children: React.ReactNode, feature: string }) => {
    // Open platform: the paywall has been removed, so every feature is
    // available to all users. Kept as a pass-through wrapper to avoid
    // touching every call site; set hasAccess back to a subscription check
    // to restore gating.
    const hasAccess = true

    if (!hasAccess) {
      return (
        <div className="relative">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm z-10 rounded-lg flex items-center justify-center">
            <div className="text-center text-white">
              <Lock className="w-8 h-8 mx-auto mb-2" />
              <p className="text-sm font-medium">Premium Feature</p>
              <Button 
                size="sm" 
                className="mt-2 bg-gradient-to-r from-purple-500 to-pink-500"
                onClick={onUpgrade}
              >
                <Crown className="w-4 h-4 mr-1" />
                Upgrade
              </Button>
            </div>
          </div>
          <div className="opacity-30 pointer-events-none">
            {children}
          </div>
        </div>
      )
    }

    return <>{children}</>
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Brain className="w-8 h-8 text-blue-400" />
            Patient Dashboard
          </h1>
          {userName && (
            <p className="text-gray-400 mt-1">Welcome back, {userName}</p>
          )}
        </div>
        
        {subscriptionStatus && (
          <div className="flex items-center gap-3">
            <Badge 
              variant={subscriptionStatus.has_active_subscription ? "default" : "secondary"}
              className={subscriptionStatus.has_active_subscription ? 
                "bg-gradient-to-r from-purple-500 to-pink-500" : ""}
            >
              {subscriptionStatus.plan_name || 'Basic'}
            </Badge>
            {!subscriptionStatus.has_active_subscription && (
              <Button onClick={onUpgrade} className="bg-gradient-to-r from-purple-500 to-pink-500">
                <Crown className="w-4 h-4 mr-2" />
                Upgrade
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Usage Overview */}
      {subscriptionStatus && (
        <Card className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-500/30">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Usage This Month
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-300">Music Generations</span>
                  <span className="text-white font-medium">
                    {subscriptionStatus.generations_used_this_month}/
                    {subscriptionStatus.max_generations_per_month === -1 ? '∞' : subscriptionStatus.max_generations_per_month}
                  </span>
                </div>
                <Progress 
                  value={subscriptionStatus.max_generations_per_month === -1 ? 0 : 
                    (subscriptionStatus.generations_used_this_month / subscriptionStatus.max_generations_per_month) * 100} 
                  className="h-2"
                />
              </div>
              
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-300">Sessions Created</span>
                  <span className="text-white font-medium">
                    {subscriptionStatus.sessions_used_this_month}/
                    {subscriptionStatus.max_sessions_per_month === -1 ? '∞' : subscriptionStatus.max_sessions_per_month}
                  </span>
                </div>
                <Progress 
                  value={subscriptionStatus.max_sessions_per_month === -1 ? 0 : 
                    (subscriptionStatus.sessions_used_this_month / subscriptionStatus.max_sessions_per_month) * 100} 
                  className="h-2"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Dashboard Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-gray-800/50">
          <TabsTrigger value="overview" className="data-[state=active]:bg-blue-600">
            <BarChart3 className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="mood" className="data-[state=active]:bg-blue-600">
            <Heart className="w-4 h-4 mr-2" />
            Mood Tracking
          </TabsTrigger>
          <TabsTrigger value="progress" className="data-[state=active]:bg-blue-600">
            <TrendingUp className="w-4 h-4 mr-2" />
            Progress
          </TabsTrigger>
          <TabsTrigger value="insights" className="data-[state=active]:bg-blue-600">
            <Target className="w-4 h-4 mr-2" />
            Insights
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="bg-gradient-to-br from-green-900/20 to-blue-900/20 border-green-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-white text-lg flex items-center gap-2">
                  <Music className="w-5 h-5" />
                  Total Sessions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-400">
                  {analyticsData?.usage_stats.total_generations || 0}
                </div>
                <p className="text-gray-400 text-sm">Music generations</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border-purple-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-white text-lg flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Listening Time
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-purple-400">
                  {analyticsData?.usage_stats.total_listening_minutes || 0}
                </div>
                <p className="text-gray-400 text-sm">Minutes listened</p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-orange-900/20 to-red-900/20 border-orange-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-white text-lg flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Avg Rating
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-orange-400">
                  {analyticsData?.therapy_effectiveness.avg_rating?.toFixed(1) || '0.0'}
                </div>
                <p className="text-gray-400 text-sm">Out of 5.0</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="mood" className="space-y-6">
          <PremiumFeatureLock feature="mood_tracking">
            <Card className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border-blue-500/30">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Heart className="w-5 h-5" />
                  Mood Trends
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Track your emotional well-being over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 flex items-center justify-center text-gray-400">
                  <div className="text-center">
                    <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>Mood tracking chart would appear here</p>
                    <p className="text-sm mt-2">Shows mood, stress, and energy trends</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </PremiumFeatureLock>
        </TabsContent>

        <TabsContent value="progress" className="space-y-6">
          <PremiumFeatureLock feature="progress_tracking">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="bg-gradient-to-br from-green-900/20 to-teal-900/20 border-green-500/30">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Therapy Effectiveness
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-gray-300">Overall Improvement</span>
                        <span className="text-green-400 font-medium">
                          {analyticsData?.therapy_effectiveness.overall_improvement || 0}%
                        </span>
                      </div>
                      <Progress value={analyticsData?.therapy_effectiveness.overall_improvement || 0} className="h-2" />
                    </div>
                    
                    <div className="pt-4 border-t border-gray-700">
                      <p className="text-gray-400 text-sm">Most Effective Goal</p>
                      <p className="text-white font-medium">
                        {analyticsData?.therapy_effectiveness.most_effective_goal || 'Not enough data'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border-purple-500/30">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Preferences
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <p className="text-gray-400 text-sm">Preferred Tempo</p>
                      <p className="text-white font-medium">
                        {analyticsData?.usage_stats.favorite_tempo_range || 'Not determined'}
                      </p>
                    </div>
                    
                    <div>
                      <p className="text-gray-400 text-sm">Top Therapy Goals</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {analyticsData?.usage_stats.preferred_therapy_goals?.slice(0, 3).map((goal, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {goal}
                          </Badge>
                        )) || <span className="text-gray-500 text-sm">Not enough data</span>}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </PremiumFeatureLock>
        </TabsContent>

        <TabsContent value="insights" className="space-y-6">
          <PremiumFeatureLock feature="insights">
            <Card className="bg-gradient-to-br from-indigo-900/20 to-purple-900/20 border-indigo-500/30">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  AI-Powered Insights
                </CardTitle>
                <CardDescription className="text-gray-400">
                  Personalized recommendations based on your therapy data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Alert className="border-blue-500/30 bg-blue-900/20">
                    <CheckCircle className="h-4 w-4 text-blue-400" />
                    <AlertDescription className="text-gray-300">
                      Your most effective sessions occur in the evening with slower tempo music (60-80 BPM).
                    </AlertDescription>
                  </Alert>
                  
                  <Alert className="border-green-500/30 bg-green-900/20">
                    <TrendingUp className="h-4 w-4 text-green-400" />
                    <AlertDescription className="text-gray-300">
                      Your mood scores have improved by 23% over the past month. Keep up the great work!
                    </AlertDescription>
                  </Alert>
                  
                  <Alert className="border-yellow-500/30 bg-yellow-900/20">
                    <AlertCircle className="h-4 w-4 text-yellow-400" />
                    <AlertDescription className="text-gray-300">
                      Consider trying "Anxiety Relief" sessions - similar users report 15% better outcomes.
                    </AlertDescription>
                  </Alert>
                </div>
              </CardContent>
            </Card>
          </PremiumFeatureLock>
        </TabsContent>
      </Tabs>

      {/* Export Options */}
      {subscriptionStatus?.has_active_subscription && subscriptionStatus?.advanced_analytics_enabled && (
        <Card className="bg-gradient-to-br from-gray-900/20 to-slate-900/20 border-gray-500/30">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Download className="w-5 h-5" />
              Export Data
            </CardTitle>
            <CardDescription className="text-gray-400">
              Download your therapy data for external analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button 
                variant="outline" 
                onClick={() => exportData('csv')}
                className="border-gray-600 text-gray-300 hover:bg-gray-800"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button 
                variant="outline" 
                onClick={() => exportData('pdf')}
                className="border-gray-600 text-gray-300 hover:bg-gray-800"
              >
                <Download className="w-4 h-4 mr-2" />
                Export PDF Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
