"use client"

// ====================================================================
// NeuroTunes Researcher Console  —  /solutions/neurotunes/platform/researcher
// --------------------------------------------------------------------
// A programmatic API console for ML researchers. Lets a researcher paste
// an API key, verify it against the live /api/v1 service, browse the
// available endpoints, jump to the interactive OpenAPI (Swagger) docs,
// and open the Research Observatory (federated-network + model-version
// introspection). Calls are proxied through /api/v1/* (see
// app/api/v1/[...path]/route.ts). Additive Next.js route; matches the
// existing dark Tailwind/shadcn theme.
// ====================================================================

import { useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  FlaskConical, KeyRound, CheckCircle2, XCircle, BookOpen, ArrowLeft,
  Mail, Activity, ShieldCheck, GitBranch, RefreshCw, AlertTriangle,
} from "lucide-react"
import Link from "next/link"
import Navigation from "../../../../../components/navigation"

type Endpoint = { method: string; path: string; scope: string; desc: string }

const ENDPOINTS: Endpoint[] = [
  { method: "GET", path: "/api/v1/health", scope: "public", desc: "Service + ML + DB health" },
  { method: "GET", path: "/api/v1/me", scope: "any key", desc: "Identify the calling key" },
  { method: "POST", path: "/api/v1/generate", scope: "generate", desc: "Generate therapeutic music" },
  { method: "POST", path: "/api/v1/generate_irb", scope: "generate", desc: "Generate under verified IRB/consent" },
  { method: "POST", path: "/api/v1/feedback", scope: "feedback", desc: "Submit feedback for a track" },
  { method: "GET", path: "/api/v1/sessions", scope: "sessions", desc: "List durable sessions" },
  { method: "GET", path: "/api/v1/research/training-data", scope: "read", desc: "Export RLHF training data" },
  { method: "GET", path: "/api/v1/federation/status", scope: "read", desc: "Federated-network status" },
  { method: "GET", path: "/api/v1/models", scope: "read", desc: "Model-version registry" },
]

type Obs = {
  loading: boolean
  error: string | null
  federation: any | null
  models: any | null
}

export default function ResearcherConsolePage() {
  const [apiKey, setApiKey] = useState("")
  const [status, setStatus] = useState<null | { ok: boolean; text: string }>(null)
  const [loading, setLoading] = useState(false)
  const [obs, setObs] = useState<Obs>({ loading: false, error: null, federation: null, models: null })

  async function verifyKey() {
    setLoading(true)
    setStatus(null)
    try {
      const res = await fetch("/api/v1/me", {
        headers: apiKey ? { "X-API-Key": apiKey } : undefined,
      })
      const data = await res.json()
      if (res.ok) {
        setStatus({
          ok: true,
          text: `Key OK — "${data?.key?.name ?? "unnamed"}" · scopes: ${data?.key?.scopes ?? "?"} · ${data?.key?.rate_limit_per_min ?? "?"} req/min`,
        })
      } else {
        setStatus({ ok: false, text: data?.message || data?.error || "Key rejected" })
      }
    } catch (e: any) {
      setStatus({ ok: false, text: e?.message || "Request failed" })
    } finally {
      setLoading(false)
    }
  }

  async function loadObservatory() {
    if (!apiKey) {
      setObs({ loading: false, error: "Enter and verify an API key first — Observatory data requires the `read` scope.", federation: null, models: null })
      return
    }
    setObs({ loading: true, error: null, federation: null, models: null })
    try {
      const headers = { "X-API-Key": apiKey }
      const [fRes, mRes] = await Promise.all([
        fetch("/api/v1/federation/status", { headers }),
        fetch("/api/v1/models", { headers }),
      ])
      if (fRes.status === 403 || mRes.status === 403) {
        setObs({ loading: false, error: "This key is missing the `read` scope required for Observatory data.", federation: null, models: null })
        return
      }
      if (!fRes.ok && !mRes.ok) {
        setObs({ loading: false, error: "Could not reach the Observatory endpoints with this key.", federation: null, models: null })
        return
      }
      const federation = await fRes.json().catch(() => null)
      const models = await mRes.json().catch(() => null)
      setObs({ loading: false, error: null, federation, models })
    } catch (e: any) {
      setObs({ loading: false, error: e?.message || "Request failed", federation: null, models: null })
    }
  }

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      <Navigation />

      <div className="max-w-5xl mx-auto px-6 pt-28 pb-20 relative z-10">
        <Link href="/solutions/neurotunes/platform" className="inline-flex items-center text-gray-400 hover:text-white mb-6 text-sm">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to platform
        </Link>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-purple-500/30 to-cyan-500/30 flex items-center justify-center">
              <FlaskConical className="w-6 h-6 text-cyan-300" />
            </div>
            <h1 className="text-3xl font-bold">Researcher API Console</h1>
          </div>
          <p className="text-gray-400 max-w-2xl">
            Authenticate with an API key to use the versioned, machine-to-machine
            <span className="text-cyan-300"> /api/v1 </span> API, and open the Research
            Observatory below. Keys are free for academic &amp; clinical researchers and
            are issued on request.
          </p>
        </motion.div>

        {/* Request a key */}
        <Card className="mt-8 bg-gradient-to-r from-purple-500/10 to-cyan-500/10 border-white/10">
          <CardContent className="p-6 flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex-grow">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-cyan-300" /> Need an API key?
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                Keys are issued to verified academic &amp; clinical researchers. Request one and
                we&apos;ll set you up with the scopes your project needs.
              </p>
            </div>
            <Link href="/contact?inquiry=api-key">
              <Button className="bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 whitespace-nowrap">
                <Mail className="w-4 h-4 mr-2" /> Request a key
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Key verification */}
        <Card className="mt-6 bg-white/5 border-white/10">
          <CardContent className="p-6">
            <label className="flex items-center gap-2 text-sm text-gray-300 mb-3">
              <KeyRound className="w-4 h-4" /> Your API key
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="nt_live_..."
                className="flex-grow rounded-md bg-black/60 border border-white/15 px-3 py-2 text-sm font-mono focus:outline-none focus:border-cyan-400"
              />
              <Button
                onClick={verifyKey}
                disabled={loading || !apiKey}
                className="bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500"
              >
                {loading ? "Verifying…" : "Verify key"}
              </Button>
            </div>
            {status && (
              <div className={`mt-4 flex items-start gap-2 text-sm ${status.ok ? "text-emerald-300" : "text-red-300"}`}>
                {status.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5" /> : <XCircle className="w-4 h-4 mt-0.5" />}
                <span>{status.text}</span>
              </div>
            )}
            <p className="mt-3 text-xs text-gray-500">
              The key is sent only to this platform over the <code>X-API-Key</code> header and is never stored in the browser.
            </p>
          </CardContent>
        </Card>

        {/* Research Observatory */}
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-300" />
              <h2 className="text-xl font-semibold">Research Observatory</h2>
            </div>
            <Button
              onClick={loadObservatory}
              disabled={obs.loading}
              variant="outline"
              className="border-white/20 text-gray-200 hover:bg-white/10"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${obs.loading ? "animate-spin" : ""}`} />
              {obs.loading ? "Loading…" : "Load live data"}
            </Button>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            Live introspection into the federated-learning network and the model-version
            registry. Requires a key with the <code>read</code> scope. Data is fetched from
            the running federation &amp; versioning services — nothing is simulated.
          </p>

          {obs.error && (
            <div className="flex items-start gap-2 text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-md px-4 py-3 mb-4">
              <AlertTriangle className="w-4 h-4 mt-0.5" /> <span>{obs.error}</span>
            </div>
          )}

          {!obs.error && !obs.federation && !obs.models && !obs.loading && (
            <div className="text-sm text-gray-500 bg-white/5 border border-white/10 rounded-md px-4 py-6 text-center">
              Enter your API key above, then click <span className="text-gray-300">Load live data</span> to view the federated network &amp; model registry.
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-4">
            {/* Federation panel */}
            {obs.federation && (
              <Card className="bg-white/5 border-white/10">
                <CardContent className="p-6">
                  <h3 className="text-base font-semibold flex items-center gap-2 mb-4">
                    <GitBranch className="w-4 h-4 text-cyan-300" /> Federated Network
                  </h3>
                  {obs.federation.available === false ? (
                    <UnavailableNote reason={obs.federation.reason} detail={obs.federation.detail} />
                  ) : (
                    <FederationView data={obs.federation} />
                  )}
                </CardContent>
              </Card>
            )}

            {/* Models panel */}
            {obs.models && (
              <Card className="bg-white/5 border-white/10">
                <CardContent className="p-6">
                  <h3 className="text-base font-semibold flex items-center gap-2 mb-4">
                    <ShieldCheck className="w-4 h-4 text-cyan-300" /> Model Registry
                  </h3>
                  {obs.models.available === false ? (
                    <UnavailableNote reason={obs.models.reason} detail={obs.models.detail} />
                  ) : (
                    <ModelsView data={obs.models} />
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Endpoints */}
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Endpoints</h2>
            <a href="/api/v1/docs" target="_blank" rel="noopener noreferrer">
              <Button variant="outline" className="border-white/20 text-gray-200 hover:bg-white/10">
                <BookOpen className="w-4 h-4 mr-2" /> Open interactive docs
              </Button>
            </a>
          </div>
          <div className="space-y-2">
            {ENDPOINTS.map((e) => (
              <div
                key={e.method + e.path}
                className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 rounded-md bg-white/5 border border-white/10 px-4 py-3"
              >
                <Badge
                  className={`w-fit ${e.method === "GET" ? "bg-emerald-600/30 text-emerald-300" : "bg-purple-600/30 text-purple-200"}`}
                >
                  {e.method}
                </Badge>
                <code className="text-sm text-cyan-200 font-mono">{e.path}</code>
                <span className="text-xs text-gray-400 flex-grow">{e.desc}</span>
                <Badge variant="outline" className="w-fit border-white/15 text-gray-400 text-xs">
                  scope: {e.scope}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Quickstart */}
        <Card className="mt-8 bg-white/5 border-white/10">
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-3">Quickstart (Python SDK)</h3>
            <p className="text-sm text-gray-400 mb-3">
              Install the official SDK straight from the repository, then generate music in a
              few lines. Browse the source on{" "}
              <a
                href="https://github.com/netrai/web/tree/master/sdk/python"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-300 hover:underline"
              >
                GitHub (sdk/python)
              </a>
              .
            </p>
            <pre className="text-xs sm:text-sm bg-black/60 border border-white/10 rounded-md p-4 overflow-x-auto text-gray-200">
{`pip install "git+https://github.com/netrai/web.git#subdirectory=sdk/python"

from neurotunes_sdk import NeuroTunesClient
client = NeuroTunesClient("https://your-host", api_key="nt_live_...")

print(client.health())
result = client.generate(age=34, therapy_goal="relaxation", stress_level=7)
print(result["tracks"])`}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ---- Observatory sub-views -----------------------------------------

function UnavailableNote({ reason, detail }: { reason?: string; detail?: string }) {
  return (
    <div className="text-sm text-gray-400">
      <div className="flex items-center gap-2 text-amber-300 mb-1">
        <AlertTriangle className="w-4 h-4" /> Service offline
      </div>
      <p>{reason || "This service is currently unreachable."}</p>
      {detail && <p className="text-xs text-gray-600 mt-1">({detail})</p>}
      <p className="text-xs text-gray-500 mt-2">
        The ML machine (federation :5001 / versioning :5002) may not be running. Live
        metrics will appear here once it is online.
      </p>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-black/40 border border-white/10 px-3 py-3 text-center">
      <div className="text-xl font-bold text-white">{value ?? "—"}</div>
      <div className="text-[11px] uppercase tracking-wide text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function FederationView({ data }: { data: any }) {
  const round = data.current_round || {}
  const global = data.global_model || {}
  const sites = data.sites || data.site_metrics || null
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Registered sites" value={data.registered_sites} />
        <Stat label="Active sites" value={data.active_sites} />
        <Stat label="Privacy budget ε" value={data.privacy_budget_remaining ?? data.privacy_epsilon} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Global model" value={global.version ?? global.model_version} />
        <Stat label="Total rounds" value={global.total_rounds ?? data.total_rounds} />
      </div>
      {round && (round.round_id || round.status) && (
        <div className="text-sm text-gray-300 bg-black/30 border border-white/10 rounded-md px-3 py-2">
          <span className="text-gray-500">Current round:</span>{" "}
          {round.round_id ? <code className="text-cyan-200">{round.round_id}</code> : "—"}{" "}
          {round.status && <Badge className="ml-2 bg-emerald-600/30 text-emerald-300">{round.status}</Badge>}
        </div>
      )}
      {sites && Array.isArray(sites) && sites.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Per-site efficacy</div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500">
                <th className="text-left font-medium py-1">Site</th>
                <th className="text-left font-medium py-1">Sessions</th>
                <th className="text-left font-medium py-1">Reward</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {sites.map((s: any, i: number) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-1">{s.site_id ?? s.id ?? `Site ${i + 1}`}</td>
                  <td className="py-1">{s.sessions ?? s.sample_count ?? "—"}</td>
                  <td className="py-1">{s.reward ?? s.clinical_improvement ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ModelsView({ data }: { data: any }) {
  const latest = data.latest || {}
  const history = Array.isArray(data.history) ? data.history : (data.history?.versions || [])
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Champion version" value={latest.version_number ?? latest.version ?? latest.version_id} />
        <Stat
          label="Reward R²"
          value={
            latest.performance_metrics?.r2 ??
            latest.performance_metrics?.accuracy ??
            latest.r2 ??
            "—"
          }
        />
      </div>
      {history && history.length > 0 ? (
        <div>
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Version history</div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500">
                <th className="text-left font-medium py-1">Version</th>
                <th className="text-left font-medium py-1">Status</th>
                <th className="text-left font-medium py-1">Created</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {history.slice(0, 8).map((v: any, i: number) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-1">{v.version_number ?? v.version ?? v.version_id ?? `v${i + 1}`}</td>
                  <td className="py-1">{v.status ?? "—"}</td>
                  <td className="py-1">{(v.created_at ?? v.created ?? "").toString().slice(0, 10) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs text-gray-500">No version history returned yet.</p>
      )}
    </div>
  )
}
