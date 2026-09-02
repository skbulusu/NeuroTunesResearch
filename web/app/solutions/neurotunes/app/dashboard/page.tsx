'use client'

import { PatientDashboard } from '@/components/dashboard/PatientDashboard'

export default function DashboardPage() {
  return (
    <PatientDashboard
      userName="current_user" // Get from your auth system
      isPremiumMode={true} // Open platform: all features available to everyone
      onUpgrade={() => {
        // Open platform: no upgrade flow (paywall removed)
      }}
    />
  )
}
