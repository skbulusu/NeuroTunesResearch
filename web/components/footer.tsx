"use client"

import { motion } from "framer-motion"
import Link from "next/link"
import Image from "next/image"
import { Github, Twitter, Linkedin, Mail } from 'lucide-react'

export default function Footer() {
  return (
    <motion.footer 
      className="bg-black/50 backdrop-blur-sm border-t border-white/10 text-white py-16 relative z-10"
      initial={{ opacity: 0.8 }}
      whileInView={{ opacity: 1 }}
      transition={{ duration: 1 }}
      viewport={{ once: false, amount: 0.3 }}
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Logo and Description */}
          <motion.div 
            className="md:col-span-1"
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <motion.div whileHover={{ scale: 1.05 }}>
              <Image src="/logo.png" alt="Netr.ai" width={120} height={60} className="h-10 w-auto mb-4" />
            </motion.div>
            <p className="text-white/70 text-sm leading-relaxed mb-4">
              Pioneering AI-powered music therapy and neurological healthcare. Transforming complex challenges into intelligent, accessible technologies.
            </p>
            <div className="flex space-x-4">
              <motion.a 
                href="https://github.com/netrai" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-white/60 hover:text-white transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <Github className="w-5 h-5" />
              </motion.a>
              <motion.a 
                href="#" 
                className="text-white/60 hover:text-white transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <Twitter className="w-5 h-5" />
              </motion.a>
              <motion.a 
                href="#" 
                className="text-white/60 hover:text-white transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <Linkedin className="w-5 h-5" />
              </motion.a>
              <motion.a 
                href="mailto:info@netr.ai" 
                className="text-white/60 hover:text-white transition-colors"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <Mail className="w-5 h-5" />
              </motion.a>
            </div>
          </motion.div>

          {/* Solutions */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            viewport={{ once: true }}
          >
            <h4 className="font-semibold mb-4">Platform</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/solutions/neurotunes/platform" className="text-white/70 hover:text-white transition-colors">
                    Overview &amp; Roadmap
                  </Link>
                </motion.div>
              </li>
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/solutions/neurotunes/app?mode=clinical" className="text-white/70 hover:text-white transition-colors">
                    For Clinicians
                  </Link>
                </motion.div>
              </li>
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/solutions/neurotunes/platform/researcher" className="text-white/70 hover:text-white transition-colors">
                    For Researchers
                  </Link>
                </motion.div>
              </li>
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/solutions/neurotunes/app" className="text-white/70 hover:text-white transition-colors">
                    For Users
                  </Link>
                </motion.div>
              </li>
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <a href="https://github.com/netrai/web" target="_blank" rel="noopener noreferrer" className="text-white/70 hover:text-white transition-colors">
                    View on GitHub
                  </a>
                </motion.div>
              </li>
            </ul>
          </motion.div>

          {/* Company */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            viewport={{ once: true }}
          >
            <h4 className="font-semibold mb-4">Company</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/about" className="text-white/70 hover:text-white transition-colors">
                    About Us
                  </Link>
                </motion.div>
              </li>
              <li>
                <motion.div whileHover={{ x: 5 }}>
                  <Link href="/contact" className="text-white/70 hover:text-white transition-colors">
                    Contact
                  </Link>
                </motion.div>
              </li>
            </ul>
          </motion.div>

        </div>

        {/* Bottom Bar */}
        <motion.div 
          className="border-t border-white/10 mt-12 pt-8 flex flex-col md:flex-row justify-between items-center"
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          viewport={{ once: true }}
        >
          <p className="text-white/60 text-sm">
            © 2026 Netr.ai · NeuroTunes Patent Pending · Open source, closed weights (Apache-2.0)
          </p>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <motion.div whileHover={{ y: -2 }}>
              <Link href="#" className="text-white/60 hover:text-white transition-colors text-sm">
                Privacy Policy
              </Link>
            </motion.div>
            <motion.div whileHover={{ y: -2 }}>
              <Link href="#" className="text-white/60 hover:text-white transition-colors text-sm">
                Terms of Service
              </Link>
            </motion.div>
            <motion.div whileHover={{ y: -2 }}>
              <Link href="#" className="text-white/60 hover:text-white transition-colors text-sm">
                Cookie Policy
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </motion.footer>
  )
}
