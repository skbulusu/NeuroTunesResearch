"use client"

// ====================================================================
// NeuroTunes Platform — Overview  —  /solutions/neurotunes/platform
// --------------------------------------------------------------------
// The open research platform's overview + role-based entry point. It
// (1) explains what the platform is and who it's for, (2) routes each
// visitor to the interface built for them (user, clinician / music
// therapist, or ML researcher), (3) summarizes platform capabilities,
// and (4) shows an honest roadmap/status snapshot (mirrors
// docs/ROADMAP.md) with links to the source on GitHub and Hugging Face.
// Additive Next.js route — matches the existing dark Tailwind/shadcn
// theme (Navigation + Card + Button + Badge).
// ====================================================================

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Headphones, Stethoscope, FlaskConical, ArrowRight, Github,
  Waves, ShieldCheck, GitBranch, LineChart, KeyRound, BookOpen,
  CheckCircle2, CircleDot, Circle, ExternalLink,
} from "lucide-react"
import Link from "next/link"
import Navigation from "../../../../components/navigation"

// External source links (code is open; weights are closed).
const GITHUB_URL = "https://github.com/netrai/web"
const HUGGINGFACE_URL = "https://huggingface.co/netrai"

const PERSONAS = [
  {
    key: "user",
    icon: Headphones,
    title: "For Users",
    to: "/solutions/neurotunes/app",
    blurb:
      "Generate personalized therapeutic music from how you feel right now, listen, and rate what helps. Simple, guided, and private. Anyone is welcome to try the research experience — it is not a medical device or treatment.",
    cta: "Open the experience",
  },
  {
    key: "therapist",
    icon: Stethoscope,
    title: "For Clinicians & Music Therapists",
    to: "/solutions/neurotunes/app?mode=clinical",
    blurb:
      "Clinical controls with an IRB / informed-consent panel. Record a protocol reference in the audit trail and generate consent-verified sessions for studies. In this demo the IRB reference is optional; a production research deployment requires it.",
    cta: "Open clinical console",
  },
  {
    key: "researcher",
    icon: FlaskConical,
    title: "For ML Researchers",
    to: "/solutions/neurotunes/platform/researcher",
    blurb:
      "A programmatic API console: authenticate with an API key, generate music, export de-identified RLHF training data, explore the interactive OpenAPI reference, and inspect the federated network in the Research Observatory.",
    cta: "Open research console",
  },
]

const CAPABILITIES = [
  {
    icon: Waves,
    title: "Physiologically-informed generation",
    desc: "Emotion → clinical-parameter mapping with binaural-beat encoding, bounded by an explicit parameter safety validator.",
  },
  {
    icon: LineChart,
    title: "Periodic RLHF",
    desc: "Feedback-driven reward model with held-out R² + k-fold cross-validation and champion/challenger promotion gating.",
  },
  {
    icon: GitBranch,
    title: "Federated architecture",
    desc: "Federated coordinator with secure aggregation (HE + Shamir) and differential privacy (ε = 1.0) for multi-site training.",
  },
  {
    icon: ShieldCheck,
    title: "Consent-aware by design",
    desc: "A basic IRB / informed-consent gate (verify_consent) records a protocol reference alongside consent-gated sessions.",
  },
  {
    icon: KeyRound,
    title: "Versioned public API",
    desc: "Scoped, rate-limited API keys over a stable /api/v1 surface — built for machine-to-machine research use.",
  },
  {
    icon: BookOpen,
    title: "Open & reproducible",
    desc: "Open-source code, an OpenAPI spec, interactive Swagger docs, and a Python SDK. Model weights are closed.",
  },
]

type RoadmapStatus = "done" | "partial" | "future"
type RoadmapItem = { status: RoadmapStatus; title: string; detail: string }

// Mirrors docs/ROADMAP.md (kept in sync manually; the file is the source of truth).
const ROADMAP: RoadmapItem[] = [
  { status: "done", title: "Periodic RLHF retraining", detail: "Weekly batch retraining with a 50+ feedback threshold and t-test significance gating." },
  { status: "done", title: "Reward model R² + k-fold CV", detail: "Held-out R²/MSE and 5-fold cross-validation persisted to reward_metrics.json." },
  { status: "done", title: "Champion / challenger promotion", detail: "A challenger is promoted only if its held-out R² ≥ champion − tolerance, else rollback." },
  { status: "done", title: "Parameter safety boundaries", detail: "Hard clamps + recommended-range warnings wired into both generation endpoints." },
  { status: "done", title: "Federated coordinator + secure aggregation", detail: "Coordinator, HE + Shamir secure aggregation, and differential privacy (ε = 1.0)." },
  { status: "done", title: "Model versioning + distributed rollback", detail: "Version registry with manual/approval-gated distributed rollback and risk assessment." },
  { status: "partial", title: "Treatment-outcome tracking", detail: "Clinical efficacy scoring exists; a longitudinal per-user outcome dashboard does not yet." },
  { status: "future", title: "Condition-specific adapters + embeddings", detail: "The flagship open ML item: shared backbone + per-condition adapters for cross-condition learning." },
  { status: "future", title: "Multi-site empirical federated validation", detail: "Infrastructure is built; validation across ≥2 real sites is future work with partner institutions." },
  { status: "future", title: "Edge / on-device sentiment analysis", detail: "A privacy feature (client-side sentiment); not present today." },
]

const STATUS_META: Record<RoadmapStatus, { label: string; icon: any; cls: string }> = {
  done: { label: "Done", icon: CheckCircle2, cls: "text-emerald-300" },
  partial: { label: "Partial", icon: CircleDot, cls: "text-amber-300" },
  future: { label: "Planned", icon: Circle, cls: "text-gray-500" },
}

export default function PlatformOverviewPage() {
  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      <Navigation />

      <div className="max-w-6xl mx-auto px-6 pt-28 pb-20 relative z-10">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-6"
        >
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
            The Open Platform for AI Music Therapy Research
          </h1>
          <p className="mt-4 text-lg text-gray-300 max-w-2xl mx-auto">
            NeuroTunes generates personalized, physiologically-informed therapeutic music — and
            gives clinicians and ML researchers the tools to study it, improve it, and build on it.
          </p>
          <p className="mt-3 text-sm text-gray-400">
            NeuroTunes&trade; — Patent Pending · Open source, closed weights
          </p>
        </motion.div>

        <div className="flex flex-wrap justify-center gap-3 mb-8">
          <Badge variant="outline" className="border-amber-500/50 text-amber-300 bg-amber-500/10">
            Research Platform — Educational &amp; Research Use Only — Not a Medical Device
          </Badge>
          <Badge variant="outline" className="border-yellow-500/50 text-yellow-300 bg-yellow-500/10">
            Patent Pending
          </Badge>
          <Badge variant="outline" className="border-cyan-500/50 text-cyan-300 bg-cyan-500/10">
            Open source · closed weights
          </Badge>
        </div>

        {/* Source links */}
        <div className="flex flex-wrap justify-center gap-3 mb-14">
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10">
              <Github className="w-4 h-4 mr-2" /> View on GitHub
            </Button>
          </a>
          <a href={HUGGINGFACE_URL} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10">
              <ExternalLink className="w-4 h-4 mr-2" /> Explore on Hugging Face
            </Button>
          </a>
        </div>

        {/* Personas */}
        <h2 className="text-2xl font-bold text-center mb-2">Choose your interface</h2>
        <p className="text-center text-gray-400 mb-8 max-w-2xl mx-auto text-sm">
          The same platform, three tailored entry points.
        </p>
        <div className="grid gap-6 md:grid-cols-3 mb-20">
          {PERSONAS.map((p, i) => {
            const Icon = p.icon
            return (
              <motion.div
                key={p.key}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 * i }}
              >
                <Card className="h-full bg-white/5 border-white/10 backdrop-blur-sm hover:border-purple-400/50 transition-colors">
                  <CardContent className="p-6 flex flex-col h-full">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500/30 to-cyan-500/30 flex items-center justify-center mb-4">
                      <Icon className="w-6 h-6 text-cyan-300" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">{p.title}</h3>
                    <p className="text-gray-400 text-sm flex-grow">{p.blurb}</p>
                    <Link href={p.to} className="mt-6">
                      <Button className="w-full bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500">
                        {p.cta}
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>

        {/* Capabilities */}
        <h2 className="text-2xl font-bold text-center mb-2">What the platform provides</h2>
        <p className="text-center text-gray-400 mb-8 max-w-2xl mx-auto text-sm">
          Everything below is implemented in the open-source code today.
        </p>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-20">
          {CAPABILITIES.map((c, i) => {
            const Icon = c.icon
            return (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: 0.05 * i }}
              >
                <Card className="h-full bg-white/5 border-white/10">
                  <CardContent className="p-5">
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className="w-5 h-5 text-cyan-300" />
                      <h3 className="font-semibold">{c.title}</h3>
                    </div>
                    <p className="text-sm text-gray-400">{c.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>

        {/* Roadmap & status */}
        <div className="flex items-center justify-between mb-2 flex-wrap gap-3">
          <h2 className="text-2xl font-bold">Roadmap &amp; status</h2>
          <a
            href={`${GITHUB_URL}/blob/master/docs/ROADMAP.md`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10">
              <BookOpen className="w-4 h-4 mr-2" /> Read the full roadmap
            </Button>
          </a>
        </div>
        <p className="text-gray-400 mb-6 max-w-2xl text-sm">
          An honest snapshot of what is built versus what is future work. We do not claim
          clinical-grade completeness that has not been validated.
        </p>
        <div className="flex flex-wrap gap-4 mb-5 text-xs text-gray-400">
          <span className="inline-flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> Done</span>
          <span className="inline-flex items-center gap-1"><CircleDot className="w-3.5 h-3.5 text-amber-300" /> Partial</span>
          <span className="inline-flex items-center gap-1"><Circle className="w-3.5 h-3.5 text-gray-500" /> Planned</span>
        </div>
        <div className="space-y-2">
          {ROADMAP.map((r) => {
            const meta = STATUS_META[r.status]
            const Icon = meta.icon
            return (
              <div
                key={r.title}
                className="flex items-start gap-3 rounded-md bg-white/5 border border-white/10 px-4 py-3"
              >
                <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${meta.cls}`} />
                <div className="flex-grow">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{r.title}</span>
                    <Badge variant="outline" className={`text-[10px] border-white/15 ${meta.cls}`}>
                      {meta.label}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{r.detail}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
