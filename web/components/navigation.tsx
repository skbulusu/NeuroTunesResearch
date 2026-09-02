"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Menu, X, ChevronDown, Headphones, Stethoscope, FlaskConical, LayoutGrid } from 'lucide-react'
import Link from "next/link"
import Image from "next/image"

// Platform dropdown entries — the audience-segmented entry points for the
// open research platform. "Overview" is the platform hub; the three roles
// deep-link straight into their respective interfaces.
const PLATFORM_LINKS = [
  { href: "/solutions/neurotunes/platform", label: "Overview", icon: LayoutGrid, desc: "Features, benefits & roadmap" },
  { href: "/solutions/neurotunes/app?mode=clinical", label: "For Clinicians", icon: Stethoscope, desc: "Clinical console with consent controls" },
  { href: "/solutions/neurotunes/platform/researcher", label: "For Researchers", icon: FlaskConical, desc: "Programmatic API & interactive docs" },
  { href: "/solutions/neurotunes/app", label: "For Users", icon: Headphones, desc: "Try the guided music experience" },
]

export default function Navigation() {
  const [isOpen, setIsOpen] = useState(false)
  const [isScrolled, setIsScrolled] = useState(false)
  const [platformOpen, setPlatformOpen] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
    setIsScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const toggleMenu = () => setIsOpen(!isOpen)

  return (
    <motion.nav
    className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
    isScrolled ? 'bg-black/80 backdrop-blur-md border-b border-white/10' : 'bg-transparent'
    }`}
    initial={{ y: -100 }}
    animate={{ y: 0 }}
    transition={{ duration: 0.5 }}
    >
    <div className="max-w-7xl mx-auto px-6">
    <div className="flex items-center justify-between h-20">
    {/* Logo */}
    <motion.div
    whileHover={{ scale: 1.05 }}
    transition={{ type: "spring", stiffness: 300 }}
    >
    <Link href="/" className="flex items-center">
    <Image src="/logo.png" alt="Netr.ai" width={120} height={60} className="h-10 w-auto" />
    </Link>
    </motion.div>

    {/* Desktop Navigation */}
    <div className="hidden md:flex items-center space-x-8">
    {/* Platform dropdown (audience-segmented entry points) */}
    <div
    className="relative"
    onMouseEnter={() => setPlatformOpen(true)}
    onMouseLeave={() => setPlatformOpen(false)}
    >
    <button className="flex items-center gap-1 text-white/80 hover:text-white transition-colors">
    Platform
    <ChevronDown className={`w-4 h-4 transition-transform ${platformOpen ? 'rotate-180' : ''}`} />
    </button>
    <AnimatePresence>
    {platformOpen && (
    <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: 8 }}
    transition={{ duration: 0.15 }}
    className="absolute left-0 top-full pt-3 w-72"
    >
    <div className="bg-black/95 backdrop-blur-md border border-white/10 rounded-xl p-2 shadow-2xl">
    {PLATFORM_LINKS.map((item) => {
    const Icon = item.icon
    return (
    <Link key={item.href} href={item.href} className="flex items-start gap-3 p-3 rounded-lg hover:bg-white/10 transition-colors">
    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/30 to-cyan-500/30 flex items-center justify-center shrink-0">
    <Icon className="w-4 h-4 text-cyan-300" />
    </div>
    <div>
    <div className="text-sm font-medium text-white">{item.label}</div>
    <div className="text-xs text-white/50">{item.desc}</div>
    </div>
    </Link>
    )
    })}
    </div>
    </motion.div>
    )}
    </AnimatePresence>
    </div>

    <motion.div whileHover={{ scale: 1.05 }}>
    <Link href="/about" className="text-white/80 hover:text-white transition-colors">
    About
    </Link>
    </motion.div>

    <motion.div whileHover={{ scale: 1.05 }}>
    <Link href="/contact" className="text-white/80 hover:text-white transition-colors">
    Contact
    </Link>
    </motion.div>

    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
    <Link href="/contact?inquiry=research">
    <Button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white">
    Join Our Journey
    </Button>
    </Link>
    </motion.div>
    </div>

    {/* Mobile menu button */}
    <motion.button
    className="md:hidden text-white"
    onClick={toggleMenu}
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    >
    {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
    </motion.button>
    </div>

    {/* Mobile Navigation */}
    <AnimatePresence>
    {isOpen && (
    <motion.div
    initial={{ opacity: 0, height: 0 }}
    animate={{ opacity: 1, height: "auto" }}
    exit={{ opacity: 0, height: 0 }}
    className="md:hidden bg-black/90 backdrop-blur-md border-t border-white/10"
    >
    <div className="py-4 space-y-4">
    <motion.div
    initial={{ x: -20, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay: 0.1 }}
    >
    <div className="text-white/50 text-xs uppercase tracking-wide mb-2">Platform</div>
    <div className="space-y-2 pl-2 border-l border-white/10">
    {PLATFORM_LINKS.map((item) => (
    <Link
    key={item.href}
    href={item.href}
    onClick={() => setIsOpen(false)}
    className="block text-white/80 hover:text-white transition-colors"
    >
    {item.label}
    </Link>
    ))}
    </div>
    </motion.div>
    <motion.div
    initial={{ x: -20, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay: 0.4 }}
    >
    <Link href="/about" className="block text-white/80 hover:text-white transition-colors">
    About
    </Link>
    </motion.div>
    <motion.div
    initial={{ x: -20, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay: 0.5 }}
    >
    <Link href="/contact" className="block text-white/80 hover:text-white transition-colors">
    Contact
    </Link>
    </motion.div>
    <motion.div
    initial={{ x: -20, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ delay: 0.6 }}
    >
    <Link href="/contact?inquiry=research">
    <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white">
    Join Our Journey
    </Button>
    </Link>
    </motion.div>
    </div>
    </motion.div>
    )}
    </AnimatePresence>
    </div>
    </motion.nav>
  )
}
