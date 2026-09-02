import React from 'react'

export default function Logo({ className = "h-10 w-auto" }: { className?: string }) {
  return (
    <div className={`flex items-center ${className}`}>
      <div className="text-2xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
        Netr.ai
      </div>
    </div>
  )
}