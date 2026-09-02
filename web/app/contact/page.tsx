"use client"

import { useState, useEffect } from "react"
import type React from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

import { Checkbox } from "@/components/ui/checkbox"
import { Mail, MapPin, Send, Database, Handshake, ChevronDown } from 'lucide-react'
import Navigation from "../../components/navigation"

const INQUIRY_OPTIONS: { value: string; label: string }[] = [
  { value: "general", label: "General Inquiry" },
  { value: "api-key", label: "API Key Request (Researchers)" },
  { value: "partnership", label: "Partnership Opportunity" },
  { value: "research", label: "Research Collaboration" },
  { value: "clinical", label: "Clinical Integration" },
  { value: "data", label: "Data Contribution" },
  { value: "technical", label: "Technical Support" },
  { value: "media", label: "Media/Press" },
]

export default function ContactPage() {
  // Cursor tracking for ripple effects
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const [isMouseMoving, setIsMouseMoving] = useState(false)

  // Controlled fields so the form can be pre-filled from the URL
  // (e.g. /contact?inquiry=api-key from the researcher console).
  // Read the ?inquiry= param synchronously during the first render so the
  // Radix Select mounts with the value already set. Radix only registers a
  // controlled value against its SelectItems, and those don't mount until the
  // dropdown first opens, so a value applied later (in useEffect) never shows
  // in the trigger. A lazy initializer avoids that entirely.
  const getInitialInquiry = (): string | undefined => {
    if (typeof window === "undefined") return undefined
    return new URLSearchParams(window.location.search).get("inquiry") || undefined
  }
  const [inquiry, setInquiry] = useState<string | undefined>(getInitialInquiry)
  const [message, setMessage] = useState<string>(() =>
    getInitialInquiry() === "api-key"
      ? "I'd like to request a NeuroTunes Research API key.\n\n" +
          "Name / institution:\n" +
          "Research project & intended use:\n" +
          "Requested scopes (generate, feedback, sessions, read):\n" +
          "Expected request volume:"
      : ""
  )

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    alert("Thank you for your message! We'll get back to you as soon as possible.")
  }

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      {/* Enhanced Contact Neural Background */}
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
            className="absolute w-20 h-20 rounded-full border border-green-400/40 pointer-events-none"
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
            className="absolute w-8 h-8 rounded-full bg-gradient-to-r from-blue-400/50 to-green-400/50 pointer-events-none"
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

        {/* Contact-specific Communication Neural Patterns */}
        <motion.div
          className="absolute inset-0 opacity-25"
          initial={{ opacity: 0.1 }}
          whileInView={{ opacity: 0.25 }}
          transition={{ duration: 1 }}
        >
          <svg className="w-full h-full" viewBox="0 0 1000 1000">
            <defs>
              <linearGradient id="contactGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3B82F6" />
                <stop offset="33%" stopColor="#10B981" />
                <stop offset="66%" stopColor="#06B6D4" />
                <stop offset="100%" stopColor="#8B5CF6" />
              </linearGradient>
              <radialGradient id="contactSynapse">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity="1.0" />
                <stop offset="50%" stopColor="#10B981" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="cursorContact">
                <stop offset="0%" stopColor="#10B981" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#3B82F6" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#06B6D4" stopOpacity="0" />
              </radialGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Cursor-influenced contact field */}
            <motion.circle
              cx={mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))}
              cy={mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))}
              r="110"
              fill="url(#cursorContact)"
              animate={{
                r: isMouseMoving ? [90, 130, 110] : 90,
                opacity: isMouseMoving ? [0.3, 0.7, 0.3] : 0.2,
              }}
              transition={{
                duration: 0.8,
                ease: "easeOut",
              }}
            />

            {/* Communication network pathways */}
            <motion.path
              d="M200,200 Q400,150 600,200 Q800,250 900,200"
              fill="none"
              stroke="url(#contactGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.8, 0.4],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 5,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
            />

            <motion.path
              d="M100,400 Q300,350 500,400 Q700,450 900,400"
              fill="none"
              stroke="url(#contactGradient)"
              strokeWidth="3"
              filter="url(#glow)"
              animate={{
                opacity: [0.4, 0.7, 0.4],
                strokeWidth: [2, 4, 2],
              }}
              transition={{
                duration: 6,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
                delay: 1,
              }}
            />

            {/* Communication nodes */}
            {[...Array(12)].map((_, i) => {
              const nodeX = 150 + (i % 4) * 200
              const nodeY = 200 + Math.floor(i / 4) * 200
              const distance = Math.sqrt(
                Math.pow((mousePosition.x * (1000 / (typeof window !== 'undefined' ? window.innerWidth : 1000))) - nodeX, 2) +
                Math.pow((mousePosition.y * (1000 / (typeof window !== 'undefined' ? window.innerHeight : 1000))) - nodeY, 2)
              )
              const isNearCursor = distance < 150

              return (
                <motion.circle
                  key={`contact-synapse-${i}`}
                  cx={nodeX}
                  cy={nodeY}
                  r="4"
                  fill="url(#contactSynapse)"
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

            {/* Message flow particles */}
            {[...Array(6)].map((_, i) => (
              <motion.circle
                key={`message-flow-${i}`}
                cx="200"
                cy="200"
                r="3"
                fill="#10B981"
                animate={{
                  cx: [200, 400, 600, 800, 900],
                  cy: [200, 175, 200, 225, 200],
                  opacity: [0, 1, 1, 1, 0],
                  scale: [0.5, 1, 1, 1, 0.5],
                }}
                transition={{
                  duration: 4,
                  delay: i * 0.8,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              />
            ))}

            {/* Email wave patterns */}
            <motion.path
              d="M0,600 Q100,580 200,600 Q300,620 400,600 Q500,580 600,600 Q700,620 800,600 Q900,580 1000,600"
              fill="none"
              stroke="#06B6D4"
              strokeWidth="2"
              opacity="0.6"
              animate={{
                d: [
                  "M0,600 Q100,580 200,600 Q300,620 400,600 Q500,580 600,600 Q700,620 800,600 Q900,580 1000,600",
                  "M0,600 Q100,620 200,600 Q300,580 400,600 Q500,620 600,600 Q700,580 800,600 Q900,620 1000,600",
                  "M0,600 Q100,580 200,600 Q300,620 400,600 Q500,580 600,600 Q700,620 800,600 Q900,580 1000,600",
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
            <h1 className="text-5xl md:text-6xl font-bold mb-8">
              Get In <span className="text-blue-400">Touch</span>
            </h1>
            <p className="text-xl text-white/70 max-w-3xl mx-auto leading-relaxed mb-12">
              Ready to transform healthcare with AI? Let's discuss how we can work together to revolutionize
              neurological rehabilitation and beyond.
            </p>
          </motion.div>
        </div>
      </motion.section>

      {/* Contact Form and Info */}
      <motion.section 
        className="py-20 px-6 relative z-10"
        initial={{ opacity: 0.8 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1 }}
        viewport={{ once: false, amount: 0.2 }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12">
            {/* Contact Form */}
            <motion.div
              initial={{ x: -50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              whileHover={{ y: -5 }}
            >
              <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                <CardContent className="p-8">
                  <h3 className="text-2xl font-bold mb-6">Send us a message</h3>
                  <p className="text-white/70 mb-6">
                    We'd love to hear from you. Fill out the form below and we'll get back to you as soon as possible.
                  </p>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <label className="block text-sm font-medium mb-2">Name *</label>
                      <Input
                        required
                        className="bg-white/10 border-white/20 text-white placeholder:text-white/50 hover:bg-white/15 transition-all duration-300"
                        placeholder="Your full name"
                      />
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <label className="block text-sm font-medium mb-2">Email *</label>
                      <Input
                        type="email"
                        required
                        className="bg-white/10 border-white/20 text-white placeholder:text-white/50 hover:bg-white/15 transition-all duration-300"
                        placeholder="your.email@example.com"
                      />
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <label className="block text-sm font-medium mb-2">Company/Organization</label>
                      <Input
                        className="bg-white/10 border-white/20 text-white placeholder:text-white/50 hover:bg-white/15 transition-all duration-300"
                        placeholder="Your organization"
                      />
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <label className="block text-sm font-medium mb-2">Inquiry Type</label>
                      {/*
                        Native <select> (styled to match the dark theme) is used
                        here instead of the Radix Select so that a value pre-filled
                        from the URL (?inquiry=api-key, coming from the researcher
                        console) is reliably reflected in the control on first
                        render. Radix Select only displays a controlled value once
                        its items have mounted (on first open), so a deep-linked
                        value would otherwise show the placeholder.
                      */}
                      <div className="relative">
                        <select
                          value={inquiry ?? ""}
                          onChange={(e) => setInquiry(e.target.value || undefined)}
                          className="w-full appearance-none rounded-md bg-white/10 border border-white/20 text-white px-3 py-2 pr-10 text-sm hover:bg-white/15 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400/50 [&>option]:bg-slate-900 [&>option]:text-white"
                        >
                          <option value="" disabled>
                            Select inquiry type
                          </option>
                          {INQUIRY_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 opacity-50" />
                      </div>
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <label className="block text-sm font-medium mb-2">Message *</label>
                      <Textarea
                        required
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        className="bg-white/10 border-white/20 text-white placeholder:text-white/50 min-h-[120px] hover:bg-white/15 transition-all duration-300"
                        placeholder="Tell us about your project, research, or how we can help..."
                      />
                    </motion.div>
                    <motion.div className="flex items-center space-x-2" whileHover={{ scale: 1.02 }}>
                      <Checkbox id="newsletter" />
                      <label htmlFor="newsletter" className="text-sm text-white/70">
                        Subscribe to our newsletter for updates on research and platform developments
                      </label>
                    </motion.div>
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        type="submit"
                        size="lg"
                        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-all duration-300"
                      >
                        <Send className="w-5 h-5 mr-2" />
                        Send Message
                      </Button>
                    </motion.div>
                  </form>
                </CardContent>
              </Card>
            </motion.div>

            {/* Contact Info */}
            <motion.div
              initial={{ x: 50, opacity: 0 }}
              whileInView={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              viewport={{ once: true }}
              className="space-y-8"
            >
              {/* Email */}
              <motion.div whileHover={{ y: -5, scale: 1.02 }}>
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-4">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: 5 }}
                      >
                        <Mail className="w-6 h-6 text-white" />
                      </motion.div>
                      <div>
                        <h4 className="font-semibold mb-1 text-blue-400">Email</h4>
                        <p className="text-white/70">info@netr.ai</p>
                        <p className="text-white/50 text-sm">We typically respond within 24 hours</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Location */}
              <motion.div whileHover={{ y: -5, scale: 1.02 }}>
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-4">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: -5 }}
                      >
                        <MapPin className="w-6 h-6 text-white" />
                      </motion.div>
                      <div>
                        <h4 className="font-semibold mb-1 text-green-400">Location</h4>
                        <p className="text-white/70">California, United States</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Partnership Opportunities */}
              <motion.div whileHover={{ y: -5, scale: 1.02 }}>
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: 5 }}
                      >
                        <Handshake className="w-6 h-6 text-white" />
                      </motion.div>
                      <div>
                        <h4 className="font-semibold mb-3 text-purple-400">Partnership Opportunities</h4>
                        <p className="text-white/70 text-sm mb-4">
                          Interested in collaborating on neuroscience research or integrating our AI solutions into your
                          healthcare practice?
                        </p>
                        <div className="space-y-2 text-sm">
                          <div>
                            <strong className="text-white">Research Institutions:</strong>
                            <span className="text-white/70"> Academic partnerships and joint studies</span>
                          </div>
                          <div>
                            <strong className="text-white">Healthcare Providers:</strong>
                            <span className="text-white/70"> Clinical integration and pilot programs</span>
                          </div>
                          <div>
                            <strong className="text-white">Technology Partners:</strong>
                            <span className="text-white/70"> API integrations and platform development</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Data Contribution */}
              <motion.div whileHover={{ y: -5, scale: 1.02 }}>
                <Card className="bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all duration-300">
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <motion.div 
                        className="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center"
                        whileHover={{ scale: 1.1, rotate: -5 }}
                      >
                        <Database className="w-6 h-6 text-white" />
                      </motion.div>
                      <div>
                        <h4 className="font-semibold mb-3 text-orange-400">Data Contribution</h4>
                        <p className="text-white/70 text-sm mb-4">
                          Help advance speech recognition technology by contributing voice data to our community dataset.
                        </p>
                        <div className="space-y-2 text-sm">
                          <div>
                            <strong className="text-white">Voice Contributors:</strong>
                            <span className="text-white/70"> Record speech samples in multiple languages</span>
                          </div>
                          <div>
                            <strong className="text-white">Researchers:</strong>
                            <span className="text-white/70"> Access anonymized datasets for your studies</span>
                          </div>
                          <div>
                            <strong className="text-white">Developers:</strong>
                            <span className="text-white/70"> Build applications using our speech recognition APIs</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </motion.section>
    </div>
  )
}
