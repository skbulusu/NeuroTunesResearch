"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Target, Heart, Zap, User } from 'lucide-react'
import Navigation from "../../components/navigation"
import Footer from "../../components/footer"

export default function AboutPage() {
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
      {/* Enhanced About Neural Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-teal-900/20" />

        {/* Interactive Cursor Ripple Effects */}
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            className="absolute w-32 h-32 rounded-full border border-purple-400/30 pointer-events-none"
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
            className="absolute w-20 h-20 rounded-full border border-teal-400/40 pointer-events-none"
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
            className="absolute w-8 h-8 rounded-full bg-gradient-to-r from-purple-400/50 to-teal-400/50 pointer-events-none"
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

        {/* About-specific Team Neural Patterns */}
        <motion.div
          className="absolute inset-0 opacity-25"
          initial={{ opacity: 0.1 }}
          whileInView={{ opacity: 0.25 }}
          transition={{ duration: 1 }}
        >
          <svg className="w-full h-full" viewBox="0 0 1000 1000">
            <defs>
              <linearGradient id="aboutGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#8B5CF6" />
                <stop offset="33%" stopColor="#06B6D4" />
                <stop offset="66%" stopColor="#10B981" />
                <stop offset="100%" stopColor="#EC4899" />
              </linearGradient>
              <radialGradient id="aboutSynapse">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity="1.0" />
                <stop offset="50%" stopColor="#06B6D4" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="cursorAbout">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#06B6D4" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
              </radialGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Cursor-influenced about field */}
            <motion.circle
              cx={mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))}
              cy={mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))}
              r="115"
              fill="url(#cursorAbout)"
              animate={{
                r: isMouseMoving ? [95, 135, 115] : 95,
                opacity: isMouseMoving ? [0.3, 0.7, 0.3] : 0.2,
              }}
              transition={{
                duration: 0.8,
                ease: "easeOut",
              }}
            />

            {/* Team collaboration pathways */}
            <motion.path
              d="M200,300 Q400,250 600,300 Q800,350 900,300"
              fill="none"
              stroke="url(#aboutGradient)"
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
              d="M100,500 Q300,450 500,500 Q700,550 900,500"
              fill="none"
              stroke="url(#aboutGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.7, 0.4],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 7,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
                delay: 1.5,
              }}
            />

            {/* Team member nodes */}
            {[...Array(12)].map((_, i) => {
              const nodeX = 200 + (i % 4) * 200
              const nodeY = 250 + Math.floor(i / 4) * 200
              const distance = Math.sqrt(
                Math.pow((mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))) - nodeX, 2) +
                Math.pow((mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))) - nodeY, 2)
              )
              const isNearCursor = distance < 150

              return (
                <motion.circle
                  key={`about-synapse-${i}`}
                  cx={nodeX}
                  cy={nodeY}
                  r="5"
                  fill="url(#aboutSynapse)"
                  filter="url(#glow)"
                  animate={{
                    opacity: isNearCursor ? [0.4, 0.9, 0.4] : [0.2, 0.6, 0.2],
                    scale: isNearCursor ? [1, 1.6, 1] : [1, 1.3, 1],
                    r: isNearCursor ? [5, 8, 5] : [4, 6, 4],
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

            {/* Collaboration flow particles */}
            {[...Array(6)].map((_, i) => (
              <motion.circle
                key={`collab-flow-${i}`}
                cx="200"
                cy="300"
                r="3"
                fill="#8B5CF6"
                animate={{
                  cx: [200, 400, 600, 800, 900],
                  cy: [300, 275, 300, 325, 300],
                  opacity: [0, 1, 1, 1, 0],
                  scale: [0.5, 1, 1, 1, 0.5],
                }}
                transition={{
                  duration: 5,
                  delay: i * 0.8,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
            ))}

            {/* Vision wave patterns */}
            <motion.path
              d="M0,700 Q100,680 200,700 Q300,720 400,700 Q500,680 600,700 Q700,720 800,700 Q900,680 1000,700"
              fill="none"
              stroke="#10B981"
              strokeWidth="2"
              opacity="0.6"
              animate={{
                d: [
                  "M0,700 Q100,680 200,700 Q300,720 400,700 Q500,680 600,700 Q700,720 800,700 Q900,680 1000,700",
                  "M0,700 Q100,720 200,700 Q300,680 400,700 Q500,720 600,700 Q700,680 800,700 Q900,720 1000,700",
                  "M0,700 Q100,680 200,700 Q300,720 400,700 Q500,680 600,700 Q700,720 800,700 Q900,680 1000,700",
                ],
                opacity: [0.4, 0.8, 0.4],
              }}
              transition={{
                duration: 4,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
                delay: 2,
              }}
            />

            {/* Mission pulse indicators */}
            {[...Array(8)].map((_, i) => (
              <motion.circle
                key={`mission-pulse-${i}`}
                cx={150 + i * 100}
                cy={700}
                r="2"
                fill="#EC4899"
                animate={{
                  opacity: [0.3, 0.9, 0.3],
                  scale: [1, 1.5, 1],
                  cy: [700, 680, 720, 700],
                }}
                transition={{
                  duration: 2.5,
                  delay: i * 0.3,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
            ))}
          </svg>
        </motion.div>
      </div>

      <Navigation />

      {/* Hero Section */}
      <motion.section 
        className="pt-32 px-6 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.3 }}
      >
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <Badge className="mb-6 bg-blue-500/20 text-blue-300 border-blue-500/30">Our Story</Badge>
            <h1 className="text-5xl md:text-6xl font-bold mb-8">
              About <span className="text-purple-400">Netr.ai</span>
            </h1>
            <p className="text-xl text-white/70 max-w-3xl mx-auto leading-relaxed">
              We're a team of passionate innovators dedicated to advancing neuroscience and healthcare through
              cutting-edge AI technology.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Mission, Vision, Impact */}
      <motion.section 
        className="py-20 px-6 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-6xl mx-auto">
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
                    <Target className="w-8 h-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold mb-4 text-blue-400">Our Mission</h3>
                  <p className="text-white/70 leading-relaxed">
                    Democratize access to advanced neuroscience and healthcare through AI-powered solutions that enhance
                    human potential and improve quality of life.
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
                    className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: -5 }}
                  >
                    <Heart className="w-8 h-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold mb-4 text-purple-400">Our Vision</h3>
                  <p className="text-white/70 leading-relaxed">
                    A world where AI-powered healthcare solutions are accessible to everyone, transforming
                    rehabilitation and enhancing human capabilities.
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
                    className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Zap className="w-8 h-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold mb-4 text-green-400">Our Impact</h3>
                  <p className="text-white/70 leading-relaxed">
                    Pioneering breakthrough technologies that bridge advanced neuroscience ideas and practical
                    healthcare applications.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Meet Our Team */}
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
              Meet Our <span className="text-blue-400">Team</span>
            </h3>
            <p className="text-white/70 text-lg max-w-2xl mx-auto">
              Driving innovation at the intersection of neuroscience, music, and AI
            </p>
          </motion.div>

          <div className="flex justify-center">
            <motion.div
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -10, scale: 1.02 }}
              className="w-full max-w-md"
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm h-full hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8 text-center">
                  <motion.div 
                    className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <User className="w-10 h-10 text-white" />
                  </motion.div>
                  <h4 className="text-xl font-bold mb-2">Sai Karthik Bulusu</h4>
                  <p className="text-purple-400 mb-4">Founder &amp; Lead Researcher</p>
                  <p className="text-white/70 text-sm leading-relaxed mb-4">
                    Founder of Netr.ai, leading the development of NeuroTunes &mdash; an open,
                    AI-powered music-therapy research platform. Inventor on patent-pending
                    RLHF-driven federated neurological music therapy technology, with research
                    interests spanning machine learning, neuroscience, biological intelligence,
                    and world models for physical AI.
                  </p>
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2 justify-center">
                      <Badge variant="secondary" className="text-xs">
                        Machine Learning
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        Neuroscience
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        Biological Intelligence
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        World Models for Physical AI
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Our Values */}
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
            <h3 className="text-4xl md:text-5xl font-bold mb-6">Our Values</h3>
            <p className="text-white/70 text-lg max-w-2xl mx-auto">The principles that guide our work and innovation</p>
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
                    <Zap className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4 text-blue-400">Innovation</h4>
                  <p className="text-white/70 leading-relaxed">
                    Continuously pushing the boundaries of what's possible in neuroscience and AI, creating breakthrough
                    solutions that transform lives.
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
                    className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: -5 }}
                  >
                    <Heart className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4 text-purple-400">Compassion</h4>
                  <p className="text-white/70 leading-relaxed">
                    Every decision we make is centered around improving patient outcomes and enhancing quality of life
                    for those we serve.
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
                    className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Target className="w-8 h-8 text-white" />
                  </motion.div>
                  <h4 className="text-2xl font-bold mb-4 text-green-400">Excellence</h4>
                  <p className="text-white/70 leading-relaxed">
                    Maintaining the highest standards in research, development, and clinical applications to ensure safe
                    and effective solutions.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.section>

      <Footer />
    </div>
  )
}
