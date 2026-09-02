"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Play, Users, Zap, Heart, Music, Brain, Target, Download, Github, ExternalLink, UserPlus } from 'lucide-react'
import Link from "next/link"
import Navigation from "../../../components/navigation"

export default function HealthcarePage() {
  // Cursor tracking for ripple effects
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isMouseMoving, setIsMouseMoving] = useState(false)

  useEffect(() => {
    let timeoutId: NodeJS.Timeout

    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY })
      setIsMouseMoving(true)
      
      clearTimeout(timeoutId)
      
      timeoutId = setTimeout(() => {
        setIsMouseMoving(false)
      }, 150)
    }

    window.addEventListener('mousemove', handleMouseMove)
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      clearTimeout(timeoutId)
    }
  }, [])

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      {/* Enhanced Healthcare Neural Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-teal-900/20" />

        {/* Interactive Cursor Ripple Effects */}
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            className="absolute w-32 h-32 rounded-full border border-blue-400/30 pointer-events-none"
            style={{
              left: mousePosition.x - 64,
              top: mousePosition.y - 64,
            }}
            animate={{
              scale: isMouseMoving ? [1, 1.5, 1] : 1,
              opacity: isMouseMoving ? [0.3, 0.6, 0.3] : 0.2,
            }}
            transition={{
              duration: 0.8,
              ease: "easeOut",
            }}
          />
          
          <motion.div
            className="absolute w-20 h-20 rounded-full border border-purple-400/40 pointer-events-none"
            style={{
              left: mousePosition.x - 40,
              top: mousePosition.y - 40,
            }}
            animate={{
              scale: isMouseMoving ? [1, 1.3, 1] : 1,
              opacity: isMouseMoving ? [0.4, 0.7, 0.4] : 0.3,
            }}
            transition={{
              duration: 0.6,
              ease: "easeOut",
              delay: 0.1,
            }}
          />

          <motion.div
            className="absolute w-8 h-8 rounded-full bg-gradient-to-r from-blue-400/50 to-purple-400/50 pointer-events-none"
            style={{
              left: mousePosition.x - 16,
              top: mousePosition.y - 16,
            }}
            animate={{
              scale: isMouseMoving ? [1, 1.2, 1] : 1,
              opacity: isMouseMoving ? [0.6, 0.9, 0.6] : 0.4,
            }}
            transition={{
              duration: 0.4,
              ease: "easeOut",
              delay: 0.05,
            }}
          />
        </div>

        {/* Healthcare-specific Neural Patterns */}
        <motion.div
          className="absolute inset-0 opacity-25"
          initial={{ opacity: 0.1 }}
          whileInView={{ opacity: 0.25 }}
          transition={{ duration: 1 }}
        >
          <svg className="w-full h-full" viewBox="0 0 1000 1000">
            <defs>
              <linearGradient id="healthcareGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3B82F6" />
                <stop offset="33%" stopColor="#8B5CF6" />
                <stop offset="66%" stopColor="#EC4899" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
              <radialGradient id="healthcareSynapse">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity="1.0" />
                <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="cursorHealthcare">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#EC4899" stopOpacity="0" />
              </radialGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Cursor-influenced healthcare field */}
            <motion.circle
              cx={mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))}
              cy={mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))}
              r="110"
              fill="url(#cursorHealthcare)"
              animate={{
                r: isMouseMoving ? [90, 130, 110] : 90,
                opacity: isMouseMoving ? [0.3, 0.7, 0.3] : 0.2,
              }}
              transition={{
                duration: 0.8,
                ease: "easeOut",
              }}
            />

            {/* Healthcare neural pathways */}
            <motion.path
              d="M100,300 Q300,250 500,300 Q700,350 900,300"
              fill="none"
              stroke="url(#healthcareGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.8, 0.4],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 6,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />

            <motion.path
              d="M50,500 Q250,450 450,500 Q650,550 850,500"
              fill="none"
              stroke="url(#healthcareGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.7, 0.4],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 8,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
                delay: 2,
              }}
            />

            {/* Healthcare synaptic nodes */}
            {[...Array(16)].map((_, i) => {
              const nodeX = 100 + (i % 4) * 250
              const nodeY = 200 + Math.floor(i / 4) * 200
              const distance = Math.sqrt(
                Math.pow((mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))) - nodeX, 2) +
                Math.pow((mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))) - nodeY, 2)
              )
              const isNearCursor = distance < 150

              return (
                <motion.circle
                  key={`healthcare-synapse-${i}`}
                  cx={nodeX}
                  cy={nodeY}
                  r="4"
                  fill="url(#healthcareSynapse)"
                  filter="url(#glow)"
                  animate={{
                    opacity: isNearCursor ? [0.4, 0.9, 0.4] : [0.2, 0.6, 0.2],
                    scale: isNearCursor ? [1, 1.6, 1] : [1, 1.3, 1],
                    r: isNearCursor ? [4, 7, 4] : [3, 5, 3],
                  }}
                  transition={{
                    duration: 3 + (i % 3),
                    repeat: Number.POSITIVE_INFINITY,
                    delay: (i % 4) * 0.5,
                    ease: "easeInOut",
                  }}
                />
              )
            })}

            {/* Medical data flow particles */}
            {[...Array(6)].map((_, i) => (
              <motion.rect
                key={`data-flow-${i}`}
                x="100"
                y="295"
                width="6"
                height="6"
                fill="#3B82F6"
                rx="1"
                animate={{
                  x: [100, 300, 500, 700, 900],
                  opacity: [0, 1, 1, 1, 0],
                }}
                transition={{
                  duration: 4,
                  delay: i * 0.7,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
            ))}
          </svg>
        </motion.div>
      </div>

      <Navigation />

      {/* Hero Section - NeuroTunes */}
      <motion.section 
        className="min-h-screen flex items-center justify-center px-6 pt-20 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.3 }}
      >
        <div className="max-w-6xl mx-auto text-center">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.8 }}
            className="mb-8"
          >
            <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              NeuroTunes
            </h1>
            <h2 className="text-3xl md:text-5xl font-light mb-8 bg-gradient-to-r from-blue-300 to-purple-300 bg-clip-text text-transparent">
              The Future of Music Therapy
            </h2>
            <p className="text-lg md:text-xl text-white/70 max-w-4xl mx-auto leading-relaxed mb-6">
              We're building the world's first AI-powered personalized music therapy platform. Join us from day one as
              we revolutionize neurological rehabilitation through the power of sound and artificial intelligence.
            </p>
            <p className="text-sm md:text-base text-white/50 max-w-4xl mx-auto mb-12">
              NeuroTunes&trade; &mdash; Patent Pending.
            </p>
          </motion.div>

          <div className="flex flex-col sm:flex-row gap-6 justify-center mb-8">
            <Link href="/solutions/neurotunes/app">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-4 text-lg shadow-lg hover:shadow-xl transition-all duration-300"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Try NeuroTunes Demo
                </Button>
              </motion.div>
            </Link>
            <Link href="/contact?inquiry=research">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm hover:border-white/50 transition-all duration-300"
                >
                  Join Our Journey →
                </Button>
              </motion.div>
            </Link>
          </div>

          {/* Status Indicators */}
          <motion.div
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 1 }}
            className="flex flex-wrap justify-center gap-6"
          >
            <motion.div
              className="flex items-center gap-2 bg-white/5 backdrop-blur-sm rounded-full px-4 py-2 border border-white/10"
              whileHover={{ scale: 1.05, borderColor: "rgba(34, 197, 94, 0.5)" }}
            >
              <div className="w-3 h-3 bg-green-400 rounded-full"></div>
              <span className="text-white/80">Prototype Ready</span>
            </motion.div>
            <motion.div
              className="flex items-center gap-2 bg-white/5 backdrop-blur-sm rounded-full px-4 py-2 border border-white/10"
              whileHover={{ scale: 1.05, borderColor: "rgba(59, 130, 246, 0.5)" }}
            >
              <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
              <span className="text-white/80">Research Based</span>
            </motion.div>
            <motion.div
              className="flex items-center gap-2 bg-white/5 backdrop-blur-sm rounded-full px-4 py-2 border border-white/10"
              whileHover={{ scale: 1.05, borderColor: "rgba(139, 92, 246, 0.5)" }}
            >
              <div className="w-3 h-3 bg-purple-400 rounded-full"></div>
              <span className="text-white/80">AI Powered</span>
            </motion.div>
            <motion.div
              className="flex items-center gap-2 bg-white/5 backdrop-blur-sm rounded-full px-4 py-2 border border-white/10"
              whileHover={{ scale: 1.05, borderColor: "rgba(234, 179, 8, 0.5)" }}
            >
              <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
              <span className="text-white/80">Patent Pending</span>
            </motion.div>
          </motion.div>
        </div>
      </motion.section>

      {/* Open Research Platform */}
      <motion.section 
        className="py-20 px-6 bg-white/5 backdrop-blur-sm relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h3 className="text-4xl md:text-5xl font-bold mb-6">
              Open <span className="text-blue-400">Research Platform</span>
            </h3>
            <p className="text-white/70 text-lg max-w-3xl mx-auto mb-12">
              Build on our open-source foundation — every feature is free and open for researchers, developers, and clinicians
            </p>

            <div className="flex flex-col sm:flex-row gap-6 justify-center mb-12">
              <a href="https://github.com/netrai" target="_blank" rel="noopener noreferrer">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 text-lg shadow-lg hover:shadow-xl transition-all duration-300">
                    <Download className="w-5 h-5 mr-2" />
                    Download SDK
                  </Button>
                </motion.div>
              </a>
              <a href="https://github.com/netrai" target="_blank" rel="noopener noreferrer">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm hover:border-white/50 transition-all duration-300"
                  >
                    <ExternalLink className="w-5 h-5 mr-2" />
                    Explore Open Core
                  </Button>
                </motion.div>
              </a>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <motion.div
                initial={{ x: -30, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
              >
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300 h-full">
                  <CardContent className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: 5 }}
                      >
                        <Github className="w-6 h-6 text-white" />
                      </motion.div>
                      <h4 className="text-2xl font-bold">Open Source Core</h4>
                    </div>
                    <ul className="space-y-3 text-white/70">
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full" />
                        Basic music generation algorithms
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full" />
                        Core therapeutic protocols
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full" />
                        Community dataset access
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full" />
                        Open source SDK
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-400 rounded-full" />
                        Basic patient profiling
                      </li>
                    </ul>
                    <div className="mt-6">
                      <Link href="/contact?inquiry=research">
                        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                          <Button className="w-full bg-green-600 hover:bg-green-700 transition-all duration-300">
                            <Github className="w-4 h-4 mr-2" />
                            Join Community
                          </Button>
                        </motion.div>
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ x: 30, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.6 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
              >
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300 h-full">
                  <CardContent className="p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: -5 }}
                      >
                        <Zap className="w-6 h-6 text-white" />
                      </motion.div>
                      <h4 className="text-2xl font-bold">For Developers & Researchers</h4>
                    </div>
                    <ul className="space-y-3 text-white/70">
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-400 rounded-full" />
                        <strong>Contribute Anonymized Data:</strong> Help improve our algorithms by contributing
                        anonymized therapeutic data
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-400 rounded-full" />
                        <strong>Build Extensions:</strong> Create custom therapeutic modules using our open APIs
                      </li>
                      <li className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-blue-400 rounded-full" />
                        <strong>Access Community Dataset:</strong> Leverage our growing database of therapeutic patterns
                      </li>
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* How NeuroTunes Works */}
      <motion.section 
        className="py-20 px-6 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h3 className="text-4xl md:text-5xl font-bold mb-6">How NeuroTunes Works</h3>
            <p className="text-white/70 text-lg max-w-3xl mx-auto">
              AI-powered music generation tailored to individual neurological conditions and therapeutic goals
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Users className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">Patient Assessment</h4>
                  <p className="text-white/70">
                    Comprehensive evaluation of patient condition, therapy goals, mood, stress levels, and neurological
                    status to create personalized profiles.
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: -5 }}
                  >
                    <Brain className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">AI Music Generation</h4>
                  <p className="text-white/70">
                    Advanced AI algorithms analyze patient data to generate personalized therapeutic music optimized for
                    specific neurological conditions and recovery goals.
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-green-500 to-teal-500 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Heart className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">Therapeutic Delivery</h4>
                  <p className="text-white/70">
                    Personalized music sessions delivered through our platform with real-time monitoring and
                    adjustment based on patient response and progress.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Our Journey */}
      <motion.section 
        className="py-20 px-6 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h3 className="text-4xl md:text-5xl font-bold mb-6">Our Journey</h3>
            <p className="text-white/70 text-lg max-w-3xl mx-auto">
              From prototype to revolutionary healthcare platform - here's where we are and where we're going
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Target className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">Where We Are</h4>
                  <p className="text-white/60 mb-6">Early-stage prototype with synthetic data</p>
                  <p className="text-white/70 text-sm mb-6">
                    We have a working prototype using synthetic data and basic AI models. No funding yet, but we're
                    building something revolutionary.
                  </p>
                  <Link href="/solutions/NeuroTunes">
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        variant="outline"
                        className="border-orange-500/30 text-orange-400 hover:bg-orange-500/10 bg-transparent transition-all duration-300"
                      >
                        Try Our Prototype
                      </Button>
                    </motion.div>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: -5 }}
                  >
                    <Brain className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">Our Vision</h4>
                  <p className="text-white/60 mb-6">Where we're heading in the next 2-3 years</p>
                  <p className="text-white/70 text-sm mb-6">
                    Clinical trials, real patient data, healthcare partnerships, and FDA approval for our AI-powered
                    music therapy platform.
                  </p>
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      variant="outline"
                      className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10 bg-transparent transition-all duration-300"
                    >
                      Learn Our Story
                    </Button>
                  </motion.div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-16 h-16 bg-gradient-to-br from-green-500 to-teal-500 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Users className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4">Join Our Journey</h4>
                  <p className="text-white/60 mb-6">Be part of something revolutionary</p>
                  <p className="text-white/70 text-sm mb-6">
                    Looking for early adopters, researchers, and healthcare professionals to help validate and improve
                    our approach.
                  </p>
                  <Link href="/contact?inquiry=research">
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        variant="outline"
                        className="border-green-500/30 text-green-400 hover:bg-green-500/10 bg-transparent transition-all duration-300"
                      >
                        <UserPlus className="w-4 h-4 mr-2" />
                        Get Involved
                      </Button>
                    </motion.div>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Ready to Transform Music Therapy? */}
      <motion.section 
        className="py-20 px-6 bg-white/5 backdrop-blur-sm relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h3 className="text-4xl md:text-5xl font-bold mb-6">Ready to Transform Music Therapy?</h3>
            <p className="text-white/70 text-lg mb-12 max-w-3xl mx-auto">
              Join our community of researchers, developers, and healthcare professionals advancing neuroscience through
              AI-powered music therapy.
            </p>
            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <Link href="/solutions/neurotunes/app">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="lg"
                    className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-4 text-lg shadow-lg hover:shadow-xl transition-all duration-300"
                  >
                    Try NeuroTunes Demo
                  </Button>
                </motion.div>
              </Link>
              <a href="https://github.com/netrai" target="_blank" rel="noopener noreferrer">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm hover:border-white/50 transition-all duration-300"
                  >
                    Explore Open Core
                  </Button>
                </motion.div>
              </a>
              <Link href="/contact?inquiry=partnership">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm hover:border-white/50 transition-all duration-300"
                  >
                    Partner With Us
                  </Button>
                </motion.div>
              </Link>
            </div>
          </motion.div>
        </div>
      </motion.section>
    </div>
  )
}
