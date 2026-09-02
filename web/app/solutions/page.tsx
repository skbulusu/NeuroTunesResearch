'use client'

import Link from 'next/link'
import { Brain, Music, Shield, Users, Award } from 'lucide-react'

export default function SolutionsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900 to-purple-900">
      {/* Navigation */}
      <nav className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold text-white">
            Netr.ai
          </Link>
          <div className="hidden md:flex space-x-8">
            <Link href="/solutions/neurotunes/app" className="text-gray-300 hover:text-white transition-colors">
              NeuroTunes
            </Link>
            <Link href="/solutions" className="text-white font-semibold">
              Solutions
            </Link>
            <Link href="/about" className="text-gray-300 hover:text-white transition-colors">
              About
            </Link>
            <Link href="/contact" className="text-gray-300 hover:text-white transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-20">
        <div className="text-center">
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6">
            Our
            <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              {' '}Solutions
            </span>
          </h1>
          <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
            An open, AI-powered music-therapy research platform designed for healthcare,
            research, and therapeutic applications.
          </p>
        </div>
      </section>

      {/* Solutions Grid */}
      <section className="container mx-auto px-6 py-20">
        <div className="max-w-2xl mx-auto">
          {/* NeuroTunes Solution */}
          <div className="neurotunes-card">
            <div className="flex items-center mb-6">
              <Music className="h-12 w-12 text-purple-400 mr-4" />
              <h2 className="text-3xl font-bold text-white">NeuroTunes</h2>
            </div>
            <p className="text-gray-300 mb-6">
              AI-powered music therapy platform that generates personalized therapeutic interventions
              based on patient needs, neuroscience research, and real-time biometric data.
            </p>
            <div className="space-y-3 mb-6">
              <div className="flex items-center text-gray-300">
                <Brain className="h-5 w-5 text-blue-400 mr-3" />
                <span>Neuroscience-based algorithms</span>
              </div>
              <div className="flex items-center text-gray-300">
                <Shield className="h-5 w-5 text-green-400 mr-3" />
                <span>HIPAA-compliant platform</span>
              </div>
              <div className="flex items-center text-gray-300">
                <Users className="h-5 w-5 text-purple-400 mr-3" />
                <span>Clinical trial integration</span>
              </div>
              <div className="flex items-center text-gray-300">
                <Award className="h-5 w-5 text-yellow-400 mr-3" />
                <span>Evidence-based therapy</span>
              </div>
            </div>
            <Link
              href="/solutions/neurotunes/app"
              className="neurotunes-button inline-block text-center w-full"
            >
              Explore NeuroTunes
            </Link>
          </div>

        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-6 py-20">
        <h2 className="text-4xl font-bold text-white text-center mb-16">
          Why Choose Our Solutions?
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="text-center">
            <Brain className="h-16 w-16 text-purple-400 mx-auto mb-6" />
            <h3 className="text-2xl font-semibold text-white mb-4">AI-Powered</h3>
            <p className="text-gray-300">
              Advanced machine learning algorithms trained on neuroscience research and clinical data.
            </p>
          </div>
          <div className="text-center">
            <Shield className="h-16 w-16 text-green-400 mx-auto mb-6" />
            <h3 className="text-2xl font-semibold text-white mb-4">Secure & Compliant</h3>
            <p className="text-gray-300">
              HIPAA-compliant infrastructure with enterprise-grade security and privacy protection.
            </p>
          </div>
          <div className="text-center">
            <Award className="h-16 w-16 text-yellow-400 mx-auto mb-6" />
            <h3 className="text-2xl font-semibold text-white mb-4">Evidence-Based</h3>
            <p className="text-gray-300">
              Built on peer-reviewed research and validated through clinical trials and studies.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
