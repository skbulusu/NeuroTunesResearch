"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Play, Pause, Download, Music, Brain, Loader2, Volume2 } from 'lucide-react'

export function NeuroTunesDemo() {
  const [prompt, setPrompt] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [generatedTrack, setGeneratedTrack] = useState<{
    title: string
    duration: string
    audioUrl: string
    description: string
  } | null>(null)

  const handleGenerate = async () => {
    if (!prompt.trim()) return

    setIsGenerating(true)

    // Simulate API call
    setTimeout(() => {
      setGeneratedTrack({
        title: `AI Generated: ${prompt.slice(0, 30)}...`,
        duration: "2:34",
        audioUrl: "/demo-track.mp3", // This would be the actual generated audio
        description: `Therapeutic music generated based on: "${prompt}"`
      })
      setIsGenerating(false)
    }, 3000)
  }

  const togglePlayback = () => {
    setIsPlaying(!isPlaying)
    // Here you would implement actual audio playback
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      <Card className="bg-gradient-to-br from-green-900/20 to-blue-900/20 border-green-500/30 backdrop-blur-sm">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-400 to-blue-400 flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <CardTitle className="text-2xl text-white">NeuroTunes AI Demo</CardTitle>
              <CardDescription className="text-green-300">
                Generate therapeutic music with AI
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Input Section */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Describe the type of therapeutic music you want to generate
              </label>
              <Textarea
                placeholder="e.g., Calming music for anxiety relief with gentle piano and nature sounds..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="bg-white/5 border-white/20 text-white placeholder:text-gray-400 focus:border-green-400 focus:ring-green-400/20"
                rows={3}
              />
            </div>

            <Button
              onClick={handleGenerate}
              disabled={!prompt.trim() || isGenerating}
              className="w-full bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 text-white"
              size="lg"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating Music...
                </>
              ) : (
                <>
                  <Music className="mr-2 h-4 w-4" />
                  Generate Therapeutic Music
                </>
              )}
            </Button>
          </div>

          {/* Generation Progress */}
          {isGenerating && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 rounded-lg p-6 border border-white/10"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-green-400 to-blue-400 flex items-center justify-center">
                  <Brain className="w-4 h-4 text-white animate-pulse" />
                </div>
                <div>
                  <div className="text-white font-medium">AI Processing</div>
                  <div className="text-gray-400 text-sm">Analyzing therapeutic requirements...</div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Progress</span>
                  <span className="text-green-400">Processing...</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <motion.div
                    className="bg-gradient-to-r from-green-400 to-blue-400 h-2 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 3, ease: "easeInOut" }}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* Generated Track */}
          {generatedTrack && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 rounded-lg p-6 border border-white/10"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-white font-semibold text-lg mb-1">
                    {generatedTrack.title}
                  </h3>
                  <p className="text-gray-400 text-sm mb-2">
                    {generatedTrack.description}
                  </p>
                  <div className="flex items-center gap-4">
                    <Badge variant="secondary" className="bg-green-500/20 text-green-300">
                      <Volume2 className="w-3 h-3 mr-1" />
                      {generatedTrack.duration}
                    </Badge>
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-300">
                      Therapeutic
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Audio Controls */}
              <div className="flex items-center gap-3">
                <Button
                  onClick={togglePlayback}
                  className="bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </Button>

                <div className="flex-1 bg-gray-700 rounded-full h-2 relative">
                  <div className="bg-gradient-to-r from-green-400 to-blue-400 h-2 rounded-full w-1/3" />
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/30 text-white hover:bg-white/10"
                >
                  <Download className="w-4 h-4 mr-1" />
                  Download
                </Button>
              </div>

              {/* Demo Notice */}
              <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <p className="text-yellow-300 text-sm">
                  <strong>Demo Mode:</strong> This is a demonstration of the NeuroTunes interface. 
                  In the full version, AI would generate actual therapeutic music based on your input.
                </p>
              </div>
            </motion.div>
          )}

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            <div className="text-center p-4">
              <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-3">
                <Brain className="w-6 h-6 text-green-400" />
              </div>
              <h4 className="text-white font-medium mb-1">AI-Powered</h4>
              <p className="text-gray-400 text-sm">Advanced neural networks create personalized therapeutic music</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center mx-auto mb-3">
                <Music className="w-6 h-6 text-blue-400" />
              </div>
              <h4 className="text-white font-medium mb-1">Therapeutic</h4>
              <p className="text-gray-400 text-sm">Scientifically designed for neurological rehabilitation</p>
            </div>

            <div className="text-center p-4">
              <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto mb-3">
                <Volume2 className="w-6 h-6 text-purple-400" />
              </div>
              <h4 className="text-white font-medium mb-1">Personalized</h4>
              <p className="text-gray-400 text-sm">Tailored to individual patient needs and conditions</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}