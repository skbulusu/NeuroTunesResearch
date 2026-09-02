"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowRight, Brain, Users, Rocket, Target, Heart, Zap, Music, Waves } from 'lucide-react'
import Link from "next/link"
import Navigation from "../components/navigation"
import Footer from "../components/footer"
import { useState, useEffect } from "react"

export default function HomePage() {
const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
const [isMouseMoving, setIsMouseMoving] = useState(false)
const [windowSize, setWindowSize] = useState({ width: 1000, height: 1000 })

useEffect(() => {
  // Set initial window size
  if (typeof window !== 'undefined') {
    setWindowSize({ width: window.innerWidth, height: window.innerHeight })
    
    const handleResize = () => {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight })
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }
}, [])

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

  if (typeof window !== 'undefined') {
    window.addEventListener('mousemove', handleMouseMove)
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      clearTimeout(timeoutId)
    }
  }
}, [])

// Safe calculation functions
const getScaledX = () => {
  if (windowSize.width === 0) return 500
  return (mousePosition.x * 1000) / windowSize.width
}

const getScaledY = () => {
  if (windowSize.height === 0) return 500
  return (mousePosition.y * 1000) / windowSize.height
}

return (
  <div className="min-h-screen bg-black text-white overflow-hidden relative">
    {/* Enhanced Neural-Themed Background */}
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

      {/* Base Neural Network Layer */}
      <motion.div
        className="absolute inset-0 opacity-20"
        initial={{ opacity: 0.1 }}
        whileInView={{ opacity: 0.20 }}
        transition={{ duration: 1 }}
      >
        <svg className="w-full h-full" viewBox="0 0 1000 1000">
          <defs>
            <linearGradient id="neuralGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8B5CF6" />
              <stop offset="50%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
            <radialGradient id="synapseGradient">
              <stop offset="0%" stopColor="#8B5CF6" stopOpacity="1.0" />
              <stop offset="50%" stopColor="#06B6D4" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="cursorInfluence">
              <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
            </radialGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Cursor-influenced neural field */}
          <motion.circle
            cx={getScaledX()}
            cy={getScaledY()}
            r="100"
            fill="url(#cursorInfluence)"
            animate={{
              r: isMouseMoving ? [80, 120, 100] : 80,
              opacity: isMouseMoving ? [0.3, 0.6, 0.3] : 0.2,
            }}
            transition={{
              duration: 0.8,
              ease: "easeOut",
            }}
          />

          {/* Base neural pathways */}
          <motion.path
            d="M100,200 Q300,150 500,200 Q700,250 900,200"
            fill="none"
            stroke="url(#neuralGradient)"
            strokeWidth="2"
            filter="url(#glow)"
            animate={{
              opacity: [0.2, 0.4, 0.2],
              strokeWidth: [1, 3, 1],
            }}
            transition={{
              duration: 8,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />

          <motion.path
            d="M50,400 Q250,350 450,400 Q650,450 850,400"
            fill="none"
            stroke="url(#neuralGradient)"
            strokeWidth="2"
            filter="url(#glow)"
            animate={{
              opacity: [0.2, 0.5, 0.2],
              strokeWidth: [1, 3, 1],
            }}
            transition={{
              duration: 10,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 2,
            }}
          />

          {/* Base synaptic nodes */}
          {[...Array(12)].map((_, i) => {
            const nodeX = 100 + (i % 4) * 250
            const nodeY = 150 + Math.floor(i / 4) * 200
            const distance = Math.sqrt(
              Math.pow(getScaledX() - nodeX, 2) +
              Math.pow(getScaledY() - nodeY, 2)
            )
            const isNearCursor = distance < 150

            return (
              <motion.circle
                key={`base-synapse-${i}`}
                cx={nodeX}
                cy={nodeY}
                r="3"
                fill="url(#synapseGradient)"
                filter="url(#glow)"
                animate={{
                  opacity: isNearCursor ? [0.4, 0.8, 0.4] : [0.2, 0.6, 0.2],
                  scale: isNearCursor ? [1, 1.5, 1] : [1, 1.2, 1],
                  r: isNearCursor ? [3, 6, 3] : [2, 4, 2],
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
        </svg>
      </motion.div>
    </div>

    <Navigation />

    {/* Hero Section with EEG Brainwave Patterns */}
    <motion.section
      className="min-h-screen flex items-center justify-center px-6 pt-20 relative"
      initial={{ opacity: 0.8 }}
      whileInView={{ opacity: 1 }}
      transition={{ duration: 1 }}
      viewport={{ once: false, amount: 0.3 }}
    >
      {/* Hero-specific EEG Neural Patterns */}
      <div className="absolute inset-0 opacity-30 pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1000 800">
          <defs>
            <linearGradient id="eegGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="33%" stopColor="#06B6D4" />
              <stop offset="66%" stopColor="#8B5CF6" />
              <stop offset="100%" stopColor="#EC4899" />
            </linearGradient>
          </defs>
          
          {/* EEG Brainwave Patterns */}
          <motion.path
            d="M0,200 Q50,180 100,200 Q150,220 200,200 Q250,170 300,200 Q350,230 400,200 Q450,175 500,200 Q550,225 600,200 Q650,180 700,200 Q750,220 800,200 Q850,185 900,200 Q950,215 1000,200"
            fill="none"
            stroke="url(#eegGradient)"
            strokeWidth="3"
            filter="url(#glow)"
            animate={{
              d: [
                "M0,200 Q50,180 100,200 Q150,220 200,200 Q250,170 300,200 Q350,230 400,200 Q450,175 500,200 Q550,225 600,200 Q650,180 700,200 Q750,220 800,200 Q850,185 900,200 Q950,215 1000,200",
                "M0,200 Q50,225 100,200 Q150,175 200,200 Q250,230 300,200 Q350,170 400,200 Q450,225 500,200 Q550,180 600,200 Q650,220 700,200 Q750,185 800,200 Q850,215 900,200 Q950,180 1000,200",
                "M0,200 Q50,180 100,200 Q150,220 200,200 Q250,170 300,200 Q350,230 400,200 Q450,175 500,200 Q550,225 600,200 Q650,180 700,200 Q750,220 800,200 Q850,185 900,200 Q950,215 1000,200",
              ],
              opacity: [0.4, 0.8, 0.4],
              strokeWidth: [2, 4, 2],
            }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />

          {/* Alpha Wave Pattern */}
          <motion.path
            d="M0,300 Q25,285 50,300 Q75,315 100,300 Q125,280 150,300 Q175,320 200,300 Q225,285 250,300 Q275,315 300,300 Q325,280 350,300 Q375,320 400,300 Q425,285 450,300 Q475,315 500,300 Q525,280 550,300 Q575,320 600,300 Q625,285 650,300 Q675,315 700,300 Q725,280 750,300 Q775,320 800,300 Q825,285 850,300 Q875,315 900,300 Q925,280 950,300 Q975,320 1000,300"
            fill="none"
            stroke="#10B981"
            strokeWidth="2"
            opacity="0.6"
            animate={{
              d: [
                "M0,300 Q25,285 50,300 Q75,315 100,300 Q125,280 150,300 Q175,320 200,300 Q225,285 250,300 Q275,315 300,300 Q325,280 350,300 Q375,320 400,300 Q425,285 450,300 Q475,315 500,300 Q525,280 550,300 Q575,320 600,300 Q625,285 650,300 Q675,315 700,300 Q725,280 750,300 Q775,320 800,300 Q825,285 850,300 Q875,315 900,300 Q925,280 950,300 Q975,320 1000,300",
                "M0,300 Q25,320 50,300 Q75,280 100,300 Q125,315 150,300 Q175,285 200,300 Q225,320 250,300 Q275,280 300,300 Q325,315 350,300 Q375,285 400,300 Q425,320 450,300 Q475,280 500,300 Q525,315 550,300 Q575,285 600,300 Q625,320 650,300 Q675,280 700,300 Q725,315 750,300 Q775,285 800,300 Q825,320 850,300 Q875,280 900,300 Q925,315 950,300 Q975,285 1000,300",
                "M0,300 Q25,285 50,300 Q75,315 100,300 Q125,280 150,300 Q175,320 200,300 Q225,285 250,300 Q275,315 300,300 Q325,280 350,300 Q375,320 400,300 Q425,285 450,300 Q475,315 500,300 Q525,280 550,300 Q575,320 600,300 Q625,285 650,300 Q675,315 700,300 Q725,280 750,300 Q775,320 800,300 Q825,285 850,300 Q875,315 900,300 Q925,280 950,300 Q975,320 1000,300",
              ],
              opacity: [0.4, 0.7, 0.4],
            }}
            transition={{
              duration: 6,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 1,
            }}
          />

          {/* Beta Wave Pattern */}
          <motion.path
            d="M0,400 Q12.5,390 25,400 Q37.5,410 50,400 Q62.5,385 75,400 Q87.5,415 100,400 Q112.5,390 125,400 Q137.5,410 150,400 Q162.5,385 175,400 Q187.5,415 200,400 Q212.5,390 225,400 Q237.5,410 250,400 Q262.5,385 275,400 Q287.5,415 300,400 Q312.5,390 325,400 Q337.5,410 350,400 Q362.5,385 375,400 Q387.5,415 400,400 Q412.5,390 425,400 Q437.5,410 450,400 Q462.5,385 475,400 Q487.5,415 500,400 Q512.5,390 525,400 Q537.5,410 550,400 Q562.5,385 575,400 Q587.5,415 600,400 Q612.5,390 625,400 Q637.5,410 650,400 Q662.5,385 675,400 Q687.5,415 700,400 Q712.5,390 725,400 Q737.5,410 750,400 Q762.5,385 775,400 Q787.5,415 800,400 Q812.5,390 825,400 Q837.5,410 850,400 Q862.5,385 875,400 Q887.5,415 900,400 Q912.5,390 925,400 Q937.5,410 950,400 Q962.5,385 975,400 Q987.5,415 1000,400"
            fill="none"
            stroke="#06B6D4"
            strokeWidth="2"
            opacity="0.5"
            animate={{
              opacity: [0.3, 0.6, 0.3],
              strokeWidth: [1, 3, 1],
            }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 2,
            }}
          />
        </svg>
      </div>

      <div className="max-w-7xl mx-auto text-center relative z-10">
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="mb-12"
        >
          <h1 className="text-5xl md:text-7xl font-bold mb-8 bg-gradient-to-r from-green-400 via-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent relative z-10">
            The Open Platform for AI Music Therapy Research
          </h1>
          <h2 className="text-2xl md:text-4xl font-light mb-8 text-white/90">
            Personalized therapeutic music — generate it, study it, improve it.
          </h2>
          <p className="text-lg md:text-xl text-white/70 max-w-4xl mx-auto leading-relaxed mb-6">
            NeuroTunes&trade; is an open, reproducible research platform for AI-personalized therapeutic
            music — with a programmatic API, open code, and a transparent roadmap. Clinicians, researchers,
            and users are welcome to explore and try it.
          </p>
          <p className="text-sm md:text-base text-white/50 max-w-3xl mx-auto leading-relaxed mb-10">
            Patent Pending&nbsp;·&nbsp;Open source, closed weights — the platform code is open and reproducible;
            trained model weights and datasets remain private. Research &amp; educational use only; not a medical device.
          </p>

          <div className="flex flex-col sm:flex-row gap-6 justify-center mb-8">
            <Link href="/solutions/neurotunes/platform">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="group relative">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white px-8 py-4 text-lg shadow-lg hover:shadow-xl transition-all duration-300 relative overflow-hidden"
                >
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-green-400/30 to-blue-400/30"
                    initial={{ x: "-100%" }}
                    whileHover={{ x: "100%" }}
                    transition={{ duration: 0.6 }}
                  />
                  <Music className="w-5 h-5 mr-2 relative z-10" />
                  <span className="relative z-10">Explore the Platform</span>
                  <ArrowRight className="w-5 h-5 ml-2 relative z-10 group-hover:translate-x-1 transition-transform" />
                </Button>
              </motion.div>
            </Link>

            <Link href="/contact?inquiry=research">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="group relative">
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm hover:border-white/50 transition-all duration-300 relative overflow-hidden"
                >
                  <motion.div
                    className="absolute inset-0 bg-white/5"
                    initial={{ scale: 0, opacity: 0 }}
                    whileHover={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.3 }}
                  />
                  <span className="relative z-10">Join Our Journey</span>
                  <ArrowRight className="w-5 h-5 ml-2 relative z-10 group-hover:translate-x-1 transition-transform" />
                </Button>
              </motion.div>
            </Link>
          </div>

          {/* Status Indicators with Synchronized Neural Pulses */}
          <motion.div
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 1 }}
            className="flex flex-wrap justify-center gap-8"
          >
            <motion.div
              className="flex items-center gap-3 bg-white/5 backdrop-blur-sm rounded-full px-6 py-3 border border-white/10 group cursor-pointer"
              whileHover={{ scale: 1.05, borderColor: "rgba(34, 197, 94, 0.5)" }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <motion.div
                className="w-2 h-2 bg-green-400 rounded-full relative"
                animate={{
                  opacity: [0.5, 1, 0.5],
                  scale: [1, 1.3, 1],
                  boxShadow: [
                    "0 0 5px rgba(34, 197, 94, 0.5)",
                    "0 0 15px rgba(34, 197, 94, 0.8)",
                    "0 0 5px rgba(34, 197, 94, 0.5)",
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
              <span className="text-white/90 font-medium group-hover:text-green-300 transition-colors">
                Prototype Ready
              </span>
            </motion.div>

            <motion.div
              className="flex items-center gap-3 bg-white/5 backdrop-blur-sm rounded-full px-6 py-3 border border-white/10 group cursor-pointer"
              whileHover={{ scale: 1.05, borderColor: "rgba(59, 130, 246, 0.5)" }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <motion.div
                className="w-2 h-2 bg-blue-400 rounded-full relative"
                animate={{
                  opacity: [0.5, 1, 0.5],
                  scale: [1, 1.3, 1],
                  boxShadow: [
                    "0 0 5px rgba(59, 130, 246, 0.5)",
                    "0 0 15px rgba(59, 130, 246, 0.8)",
                    "0 0 5px rgba(59, 130, 246, 0.5)",
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: 0.7,
                  ease: "easeInOut",
                }}
              />
              <span className="text-white/90 font-medium group-hover:text-blue-300 transition-colors">
                Research Based
              </span>
            </motion.div>

            <motion.div
              className="flex items-center gap-3 bg-white/5 backdrop-blur-sm rounded-full px-6 py-3 border border-white/10 group cursor-pointer"
              whileHover={{ scale: 1.05, borderColor: "rgba(139, 92, 246, 0.5)" }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <motion.div
                className="w-2 h-2 bg-purple-400 rounded-full relative"
                animate={{
                  opacity: [0.5, 1, 0.5],
                  scale: [1, 1.3, 1],
                  boxShadow: [
                    "0 0 5px rgba(139, 92, 246, 0.5)",
                    "0 0 15px rgba(139, 92, 246, 0.8)",
                    "0 0 5px rgba(139, 92, 246, 0.5)",
                  ],
                }}
                transition={{
                  duration: 2,
                  repeat: Number.POSITIVE_INFINITY,
                  delay: 1.4,
                  ease: "easeInOut",
                }}
              />
              <span className="text-white/90 font-medium group-hover:text-purple-300 transition-colors">
                AI Powered
              </span>
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </motion.section>

    {/* Solutions Section with Distinct Neural Patterns */}
    <motion.section
      className="py-20 px-6 relative"
      initial={{ opacity: 0.7 }}
      whileInView={{ opacity: 1 }}
      transition={{ duration: 1.2 }}
      viewport={{ once: false, amount: 0.2 }}
    >
      {/* Solutions-specific Neural Background */}
      <div className="absolute inset-0 opacity-25 pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1000 600">
          <defs>
            <linearGradient id="therapeuticGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#3B82F6" />
            </linearGradient>
            <linearGradient id="iotGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8B5CF6" />
              <stop offset="50%" stopColor="#EC4899" />
              <stop offset="100%" stopColor="#F59E0B" />
            </linearGradient>
          </defs>

          {/* Therapeutic Wave Patterns for NeuroTunes */}
          <motion.path
            d="M50,150 Q150,120 250,150 Q350,180 450,150"
            fill="none"
            stroke="url(#therapeuticGradient)"
            strokeWidth="3"
            filter="url(#glow)"
            animate={{
              d: [
                "M50,150 Q150,120 250,150 Q350,180 450,150",
                "M50,150 Q150,180 250,150 Q350,120 450,150",
                "M50,150 Q150,120 250,150 Q350,180 450,150",
              ],
              opacity: [0.4, 0.8, 0.4],
              strokeWidth: [2, 4, 2],
            }}
            transition={{
              duration: 5,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />

          {/* Musical Rhythm Nodes */}
          {[...Array(6)].map((_, i) => (
            <motion.circle
              key={`music-node-${i}`}
              cx={100 + i * 60}
              cy={150}
              r="4"
              fill="#10B981"
              filter="url(#glow)"
              animate={{
                opacity: [0.3, 0.9, 0.3],
                scale: [1, 1.5, 1],
                r: [3, 6, 3],
              }}
              transition={{
                duration: 1.5,
                repeat: Number.POSITIVE_INFINITY,
                delay: i * 0.25,
                ease: "easeInOut",
              }}
            />
          ))}

          {/* Circuit-like IoT Patterns */}
          <motion.path
            d="M550,150 L650,150 L650,200 L750,200 L750,100 L850,100"
            fill="none"
            stroke="url(#iotGradient)"
            strokeWidth="3"
            filter="url(#glow)"
            animate={{
              opacity: [0.4, 0.8, 0.4],
              strokeWidth: [2, 4, 2],
            }}
            transition={{
              duration: 4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
              delay: 1,
            }}
          />

          {/* Data Packet Flow */}
          {[...Array(4)].map((_, i) => (
            <motion.rect
              key={`data-packet-${i}`}
              x="550"
              y="145"
              width="8"
              height="8"
              fill="#8B5CF6"
              rx="2"
              animate={{
                x: [550, 650, 650, 750, 750, 850],
                y: [145, 145, 195, 195, 95, 95],
                opacity: [0, 1, 1, 1, 1, 0],
              }}
              transition={{
                duration: 3,
                repeat: Number.POSITIVE_INFINITY,
                delay: i * 0.75,
                ease: "easeInOut",
              }}
            />
          ))}

          {/* IoT Connection Nodes */}
          {[[650, 150], [650, 200], [750, 200], [750, 100], [850, 100]].map(([x, y], i) => (
            <motion.circle
              key={`iot-node-${i}`}
              cx={x}
              cy={y}
              r="5"
              fill="#EC4899"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.9, 0.4],
                scale: [1, 1.3, 1],
              }}
              transition={{
                duration: 2,
                repeat: Number.POSITIVE_INFINITY,
                delay: i * 0.4,
                ease: "easeInOut",
              }}
            />
          ))}
        </svg>
      </div>

      <div className="max-w-7xl mx-auto relative z-10">
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h3 className="text-4xl md:text-5xl font-bold mb-6">Our Solutions</h3>
          <p className="text-white/70 text-xl max-w-3xl mx-auto">
            Innovative technologies designed to solve real-world problems
          </p>
        </motion.div>

        <div className="max-w-2xl mx-auto">
          <motion.div
            initial={{ x: -50, opacity: 0 }}
            whileInView={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            whileHover={{ y: -10 }}
            className="group"
          >
            <Link href="/solutions/neurotunes">
              <Card className="bg-gradient-to-br from-green-500/10 to-blue-500/10 border-green-500/20 backdrop-blur-sm hover:from-green-500/20 hover:to-blue-500/20 transition-all duration-300 cursor-pointer h-full relative overflow-hidden">
                {/* NeuroTunes-specific Neural Pattern */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                  <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 300">
                    <defs>
                      <radialGradient id="therapeuticSynapse">
                        <stop offset="0%" stopColor="#10B981" stopOpacity="1" />
                        <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
                      </radialGradient>
                    </defs>
                    
                    {/* Therapeutic wave pattern */}
                    <motion.path
                      d="M50,150 Q100,120 150,150 Q200,180 250,150 Q300,120 350,150"
                      fill="none"
                      stroke="#10B981"
                      strokeWidth="2"
                      opacity="0.6"
                      animate={{
                        d: [
                          "M50,150 Q100,120 150,150 Q200,180 250,150 Q300,120 350,150",
                          "M50,150 Q100,180 150,150 Q200,120 250,150 Q300,180 350,150",
                          "M50,150 Q100,120 150,150 Q200,180 250,150 Q300,120 350,150",
                        ],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }}
                    />

                    {/* Musical rhythm nodes */}
                    {[...Array(5)].map((_, i) => (
                      <motion.circle
                        key={i}
                        cx={75 + i * 60}
                        cy={150}
                        r="3"
                        fill="url(#therapeuticSynapse)"
                        animate={{
                          opacity: [0, 1, 0],
                          scale: [0, 1.5, 0],
                        }}
                        transition={{
                          duration: 0.8,
                          delay: i * 0.2,
                          repeat: Number.POSITIVE_INFINITY,
                          repeatDelay: 1.5,
                        }}
                      />
                    ))}
                  </svg>
                </div>

                <CardContent className="p-8 relative z-10">
                  <div className="flex items-center gap-4 mb-6">
                    <motion.div
                      className="w-16 h-16 bg-gradient-to-br from-green-500 to-blue-500 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 relative"
                      animate={{ rotate: [0, 2, -2, 0] }}
                      transition={{ duration: 8, repeat: Number.POSITIVE_INFINITY }}
                    >
                      <Brain className="w-8 h-8 text-white" />
                      <motion.div
                        className="absolute inset-0 bg-gradient-to-br from-green-400/50 to-blue-400/50 rounded-2xl"
                        initial={{ opacity: 0, scale: 1 }}
                        whileHover={{
                          opacity: [0, 0.8, 0],
                          scale: [1, 1.2, 1],
                        }}
                        transition={{ duration: 0.6 }}
                      />
                    </motion.div>
                    <h4 className="text-2xl font-bold group-hover:text-green-300 transition-colors duration-300">
                      NeuroTunes
                    </h4>
                    <motion.div
                      animate={{
                        scale: [1, 1.1, 1],
                        opacity: [0.7, 1, 0.7],
                      }}
                      transition={{
                        duration: 2,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }}
                    >
                      <Waves className="w-6 h-6 text-green-400" />
                    </motion.div>
                  </div>
                  <p className="text-white/70 text-lg mb-6 group-hover:text-white/90 transition-colors duration-300">
                    AI-powered personalized music therapy platform revolutionizing neurological rehabilitation through
                    the therapeutic power of sound and artificial intelligence.
                  </p>
                  <motion.div
                    className="flex items-center text-green-400 group-hover:text-green-300 transition-colors"
                    whileHover={{ x: 5 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    <span className="font-semibold">Learn More</span>
                    <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                  </motion.div>
                </CardContent>
              </Card>
            </Link>
          </motion.div>

        </div>
      </div>
    </motion.section>

    {/* Status Section with Progress-based Neural Firing */}
    <motion.section
      className="py-20 px-6 bg-white/5 backdrop-blur-sm relative"
      initial={{ opacity: 0.8 }}
      whileInView={{ opacity: 1 }}
      transition={{ duration: 1 }}
      viewport={{ once: false, amount: 0.3 }}
    >
      {/* Status-specific Neural Patterns */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1000 400">
          <defs>
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#F59E0B" />
              <stop offset="25%" stopColor="#3B82F6" />
              <stop offset="50%" stopColor="#10B981" />
              <stop offset="75%" stopColor="#EC4899" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>
          </defs>

          {/* Progress pathway */}
          <motion.path
            d="M100,200 Q300,150 500,200 Q700,250 900,200"
            fill="none"
            stroke="url(#progressGradient)"
            strokeWidth="4"
            filter="url(#glow)"
            animate={{
              opacity: [0.4, 0.8, 0.4],
              strokeWidth: [3, 5, 3],
            }}
            transition={{
              duration: 6,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />

          {/* Progress nodes representing development stages */}
          {[
            { x: 200, color: "#F59E0B", stage: "Beta" },
            { x: 400, color: "#3B82F6", stage: "Research" },
            { x: 600, color: "#10B981", stage: "Community" },
            { x: 800, color: "#EC4899", stage: "Funding" },
          ].map((node, i) => (
            <motion.circle
              key={`progress-node-${i}`}
              cx={node.x}
              cy={200}
              r="8"
              fill={node.color}
              filter="url(#glow)"
              animate={{
                opacity: [0.5, 1, 0.5],
                scale: [1, 1.4, 1],
                r: [6, 10, 6],
              }}
              transition={{
                duration: 3,
                delay: i * 0.5,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />
          ))}

          {/* Progress indicators */}
          {[...Array(4)].map((_, i) => (
            <motion.circle
              key={`progress-indicator-${i}`}
              cx="100"
              cy="200"
              r="4"
              fill="#06B6D4"
              animate={{
                cx: [100, 200 + i * 200],
                opacity: [0, 1, 0.8, 0],
              }}
              transition={{
                duration: 8,
                delay: i * 2,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />
          ))}
        </svg>
      </div>

      <div className="max-w-7xl mx-auto relative z-10">
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h3 className="text-4xl md:text-5xl font-bold mb-6">Our Current Status</h3>
          <p className="text-white/70 text-lg max-w-2xl mx-auto">
            Transparency is key. Here's exactly where we are in our journey to revolutionize music therapy.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-4 gap-8">
          {[
            { icon: Rocket, title: "Beta", subtitle: "Development Stage", color: "from-orange-500 to-red-500" },
            { icon: Target, title: "Active", subtitle: "Research Focus", color: "from-blue-500 to-purple-500" },
            { icon: Users, title: "Building", subtitle: "Community", color: "from-green-500 to-teal-500" },
            { icon: Heart, title: "Bootstrap", subtitle: "Funding Status", color: "from-pink-500 to-purple-500" },
          ].map((item, index) => (
            <motion.div
              key={index}
              initial={{ y: 30, opacity: 0 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <motion.div
                className={`w-16 h-16 bg-gradient-to-br ${item.color} rounded-2xl flex items-center justify-center mx-auto mb-4`}
                animate={{ 
                  rotate: [0, 3, -3, 0],
                  boxShadow: [
                    "0 0 10px rgba(255, 255, 255, 0.1)",
                    "0 0 20px rgba(255, 255, 255, 0.2)",
                    "0 0 10px rgba(255, 255, 255, 0.1)",
                  ],
                }}
                transition={{ 
                  rotate: { duration: 12, repeat: Number.POSITIVE_INFINITY, delay: index * 3 },
                  boxShadow: { duration: 4, repeat: Number.POSITIVE_INFINITY, delay: index * 1 },
                }}
              >
                <item.icon className="w-8 h-8 text-white" />
              </motion.div>
              <h4 className="text-2xl font-bold mb-2">{item.title}</h4>
              <p className="text-white/60">{item.subtitle}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.section>

    {/* Join Us Section with Convergent Neural Pathways */}
    <motion.section
      className="py-20 px-6 relative"
      initial={{ opacity: 0.7 }}
      whileInView={{ opacity: 1 }}
      transition={{ duration: 1.5 }}
      viewport={{ once: false, amount: 0.2 }}
    >
      {/* Convergent Neural Pathways */}
      <div className="absolute inset-0 opacity-25 pointer-events-none">
        <svg className="w-full h-full" viewBox="0 0 1000 600">
          <defs>
            <radialGradient id="convergenceGradient">
              <stop offset="0%" stopColor="#FBBF24" stopOpacity="1" />
              <stop offset="50%" stopColor="#F59E0B" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#D97706" stopOpacity="0.4" />
            </radialGradient>
          </defs>

          {/* Convergent pathways flowing toward center */}
          {[
            { start: [100, 100], end: [500, 300] },
            { start: [900, 100], end: [500, 300] },
            { start: [100, 500], end: [500, 300] },
            { start: [900, 500], end: [500, 300] },
            { start: [50, 300], end: [500, 300] },
            { start: [950, 300], end: [500, 300] },
          ].map((path, i) => (
            <motion.path
              key={`convergent-path-${i}`}
              d={`M${path.start[0]},${path.start[1]} Q${(path.start[0] + path.end[0]) / 2},${(path.start[1] + path.end[1]) / 2 + (i % 2 === 0 ? -50 : 50)} ${path.end[0]},${path.end[1]}`}
              fill="none"
              stroke="url(#convergenceGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.3, 0.7, 0.3],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 4 + i * 0.5,
                repeat: Number.POSITIVE_INFINITY,
                delay: i * 0.3,
                ease: "easeInOut",
              }}
            />
          ))}

          {/* Community nodes flowing toward center */}
          {[...Array(8)].map((_, i) => {
            const angle = (i / 8) * Math.PI * 2
            const startX = 500 + Math.cos(angle) * 300
            const startY = 300 + Math.sin(angle) * 200
            
            return (
              <motion.circle
                key={`community-node-${i}`}
                cx={startX}
                cy={startY}
                r="4"
                fill="#FBBF24"
                animate={{
                  cx: [startX, 500],
                  cy: [startY, 300],
                  opacity: [0, 1, 0.8, 0],
                  scale: [0.5, 1.2, 1, 0.5],
                }}
                transition={{
                  duration: 6,
                  delay: i * 0.5,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
            )
          })}

          {/* Central convergence point */}
          <motion.circle
            cx="500"
            cy="300"
            r="12"
            fill="url(#convergenceGradient)"
            filter="url(#glow)"
            animate={{
              opacity: [0.6, 1, 0.6],
              scale: [1, 1.3, 1],
              r: [10, 15, 10],
            }}
            transition={{
              duration: 3,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
        </svg>
      </div>

      <div className="max-w-6xl mx-auto text-center relative z-10">
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
        >
          <h3 className="text-5xl md:text-6xl font-bold mb-8">
            Join Us From <span className="text-yellow-400">Day One</span>
          </h3>
          <p className="text-white/70 text-xl mb-12 max-w-4xl mx-auto leading-relaxed">
            We're not promising overnight success. We're promising transparency, dedication, and the chance to be part
            of something that could revolutionize healthcare. Help us build the future of music therapy.
          </p>

          <div className="flex flex-col sm:flex-row gap-6 justify-center mb-16">
            <Link href="/solutions/neurotunes/app">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size="lg"
                  className="bg-white text-purple-900 hover:bg-gray-100 px-8 py-4 text-lg font-semibold shadow-lg"
                >
                  Try NeuroTunes Demo
                </Button>
              </motion.div>
            </Link>
            <Link href="/contact">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/30 text-white hover:bg-white/10 px-8 py-4 text-lg bg-transparent backdrop-blur-sm"
                >
                  Join Our Mission
                </Button>
              </motion.div>
            </Link>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Rocket,
                title: "Early Access",
                desc: "Be among the first to test and shape our platform",
                color: "from-orange-500 to-red-500",
              },
              {
                icon: Target,
                title: "Direct Impact",
                desc: "Your feedback directly influences our development",
                color: "from-yellow-500 to-orange-500",
              },
              {
                icon: Zap,
                title: "Ground Floor",
                desc: "Join a potential breakthrough in healthcare technology",
                color: "from-yellow-400 to-yellow-500",
              },
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ y: 30, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                whileHover={{ y: -5 }}
                className="text-center"
              >
                <motion.div
                  className={`w-16 h-16 bg-gradient-to-br ${item.color} rounded-2xl flex items-center justify-center mx-auto mb-4`}
                  animate={{
                    boxShadow: [
                      "0 0 10px rgba(255, 255, 255, 0.05)",
                      "0 0 20px rgba(255, 255, 255, 0.1)",
                      "0 0 10px rgba(255, 255, 255, 0.05)",
                    ],
                  }}
                  transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, delay: index * 1.5 }}
                >
                  <item.icon className="w-8 h-8 text-white" />
                </motion.div>
                <h4 className="text-2xl font-bold mb-4">{item.title}</h4>
                <p className="text-white/70">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.section>

    <Footer />
  </div>
)
}
