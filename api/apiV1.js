// ====================================================================
// server/apiV1.js  —  NeuroTunes public, versioned programmatic API (/api/v1)
// --------------------------------------------------------------------
// A stable, documented, machine-to-machine API for ML researchers and
// music therapists. Every data endpoint is protected by API-key auth +
// per-key rate limiting (see apiAuth.js). Responses use a consistent
// envelope ({ api_version, ... }) so clients can evolve safely.
//
// This router is ADDITIVE and independent of the legacy /api/neurotunes
// routes, which continue to serve the existing web client unchanged.
// ====================================================================

import express from 'express';
import axios from 'axios';
import path from 'path';
import { query as dbQuery, isDbHealthy } from './db.js';
import { requireApiKey, apiKeyRateLimiter, requireScope } from './apiAuth.js';
import { openApiSpec, swaggerHtml } from './openapi.js';

const router = express.Router();

// ---- ML server service discovery (env-based) ----
function mlBaseUrl() {
  const raw = process.env.ML_SERVER_URL || 'netraimlserver';
  return raw.startsWith('http') ? raw : `http://${raw}:5000`;
}

// Extract just the host (no scheme/port) from whatever ML_SERVER_URL holds,
// so the federation (:5001) and versioning (:5002) services on the same ML
// machine can be reached without extra config. Each can still be overridden
// explicitly via FEDERATION_URL / VERSIONING_URL.
function mlHost() {
  const raw = process.env.ML_SERVER_URL || 'netraimlserver';
  const noScheme = raw.replace(/^https?:\/\//, '');
  return noScheme.split(':')[0].split('/')[0];
}

function federationBaseUrl() {
  const raw = process.env.FEDERATION_URL;
  if (raw) return raw.startsWith('http') ? raw : `http://${raw}:5001`;
  return `http://${mlHost()}:5001`;
}

function versioningBaseUrl() {
  const raw = process.env.VERSIONING_URL;
  if (raw) return raw.startsWith('http') ? raw : `http://${raw}:5002`;
  return `http://${mlHost()}:5002`;
}

const API_VERSION = 'v1';

// Small helper to shape ML track objects into the stable v1 contract.
function shapeTracks(tracks = []) {
  return tracks.map((t) => ({
    track_id: t.track_id,
    log_id: t.log_id,
    tempo: t.tempo ?? (t.music_params && t.music_params.tempo),
    key: t.key ?? (t.music_params && t.music_params.key),
    mode: t.mode ?? (t.music_params && t.music_params.mode),
    midi_url: t.midi_filename ? `/api/${API_VERSION}/download/${t.midi_filename}` : null,
    audio_url: t.filename ? `/api/${API_VERSION}/download/${t.filename}` : null,
  }));
}

/**
 * Persist a generation session + its tracks to the DB for durable session history + feedback.
 * Best-effort: swallows errors so the API never breaks when the DB is unavailable.
 * @returns {Array} tracks with log_id populated (or the original tracks if persistence fails)
 */
async function persistGeneration(session_id, patientData, music_params, patient_state, tracks) {
  try {
    // 1. Insert the session record
    await dbQuery(
      `INSERT INTO neurotunes_music_sessions (session_id, user_name, session_name, created_at)
       VALUES (?, ?, ?, NOW())
       ON DUPLICATE KEY UPDATE session_id = session_id`,  // no-op if session already exists
      [session_id, patientData.user_name || null, patientData.session_name || null]
    );

    // 2. For each track, insert a generation_log row and collect the auto-increment log_id
    const tracksWithLogIds = [];
    for (const track of tracks) {
      const result = await dbQuery(
        `INSERT INTO neurotunes_generation_log
           (session_id, user_name, age, gender, primary_diagnosis, therapy_goal,
            current_mood, stress_level, sleep_quality, energy_level,
            patient_state, music_params, track_id, midi_filename, audio_filename,
            binaural_frequency, generation_timestamp)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())`,
        [
          session_id,
          patientData.user_name || null,
          patientData.age || null,
          patientData.gender || null,
          patientData.diagnosis || null,
          patientData.therapy_goal || null,
          patientData.current_mood || null,
          patientData.stress_level || null,
          patientData.sleep_quality || null,
          patientData.energy_level || null,
          JSON.stringify(patient_state),
          JSON.stringify(music_params),
          track.track_id || null,
          track.midi_filename || null,
          track.filename || null,
          track.binaural_frequency || null,
        ]
      );
      tracksWithLogIds.push({ ...track, log_id: result.insertId });
    }
    return tracksWithLogIds;
  } catch (err) {
    console.error('[persistGeneration] DB write failed (non-fatal):', err.message);
    // Return the original tracks with log_id still null so the API response is still valid
    return tracks;
  }
}

// ====================================================================
// Public (no auth): health + version
// ====================================================================
router.get('/health', async (req, res) => {
  let ml = 'unknown';
  try {
    const r = await axios.get(`${mlBaseUrl()}/health`, { timeout: 8000 });
    ml = r.data && r.data.status ? r.data.status : 'reachable';
  } catch (_e) {
    ml = 'unreachable';
  }
  const db = (await isDbHealthy()) ? 'healthy' : 'unreachable';
  res.json({ api_version: API_VERSION, status: 'ok', ml_server: ml, database: db });
});

router.get('/version', (req, res) => {
  res.json({ api_version: API_VERSION, name: 'NeuroTunes Research API' });
});

// ---- Interactive + machine-readable API docs (public) ----
router.get('/openapi.json', (req, res) => {
  res.json(openApiSpec);
});

router.get('/docs', (req, res) => {
  // Swagger UI loads its bundle/styles from the unpkg CDN and uses a small
  // inline bootstrap script (window.onload). The global Helmet CSP (see
  // server/app.js) does not allow either, which left this page blank. Apply a
  // permissive CSP scoped to THIS response only, so the rest of the site keeps
  // its strict policy.
  res.setHeader(
    'Content-Security-Policy',
    [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' https://unpkg.com",
      "style-src 'self' 'unsafe-inline' https://unpkg.com",
      "img-src 'self' data: https://unpkg.com",
      "font-src 'self' data: https://unpkg.com",
      "connect-src 'self'",
      "worker-src 'self' blob:",
    ].join('; ')
  );
  // Don't let Cloudflare/browsers cache this HTML, so CSP/spec changes to the
  // docs page take effect immediately without a manual cache purge.
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
  res.type('html').send(swaggerHtml('/api/v1/openapi.json'));
});

// ====================================================================
// Everything below requires a valid API key + is rate limited per key.
// ====================================================================
router.use(requireApiKey, apiKeyRateLimiter);

// Identify the calling key (useful for debugging integrations).
router.get('/me', (req, res) => {
  res.json({
    api_version: API_VERSION,
    key: {
      id: req.apiKey.id,
      name: req.apiKey.name,
      scopes: req.apiKey.scopes,
      rate_limit_per_min: req.apiKey.rate_limit_per_min,
    },
  });
});

// -------- Generate therapeutic music --------
router.post('/generate', requireScope('generate'), async (req, res) => {
  try {
    const patientData = { ...req.body };
    const r = await axios.post(`${mlBaseUrl()}/generate_music`, patientData, {
      timeout: 60000,
      headers: { 'Content-Type': 'application/json' },
    });
    const d = r.data;
    // Persist session + generation logs to DB (best-effort: failures are swallowed so generation never breaks)
    const tracksWithLogIds = await persistGeneration(d.session_id, patientData, d.music_params, d.patient_state, d.tracks);
    res.json({
      api_version: API_VERSION,
      session_id: d.session_id,
      patient_state: d.patient_state,
      music_params: d.music_params,
      tracks: shapeTracks(tracksWithLogIds),
      timestamp: d.timestamp,
    });
  } catch (error) {
    const status = error.response ? error.response.status : 502;
    res.status(status === 200 ? 502 : status).json({
      error: 'generation_failed',
      message: error.response ? (error.response.data.error || 'ML server error') : error.message,
    });
  }
});

// -------- Generate under verified IRB/consent (patent Claim 3) --------
router.post('/generate_irb', requireScope('generate'), async (req, res) => {
  try {
    // API contract accepts consent as a nested object:
    //   { ...patient, consent: { consent_verified, consent_reference } }
    // The ML server reads consent_verified/consent_reference at the top
    // level, so flatten them here before forwarding.
    const body = { ...req.body };
    const consent = body.consent && typeof body.consent === 'object' ? body.consent : {};
    const payload = {
      ...body,
      consent_verified: consent.consent_verified ?? body.consent_verified ?? false,
      consent_reference: consent.consent_reference ?? body.consent_reference,
    };
    delete payload.consent;
    const r = await axios.post(`${mlBaseUrl()}/generate_music_irb`, payload, {
      timeout: 60000,
      headers: { 'Content-Type': 'application/json' },
      // Let us forward the ML server's 403 (consent not verified) verbatim.
      validateStatus: (s) => s < 500,
    });
    if (r.status === 403) {
      return res.status(403).json({ api_version: API_VERSION, ...r.data });
    }
    const d = r.data;
    // Persist session + generation logs to DB (best-effort: failures are swallowed so generation never breaks)
    const tracksWithLogIds = await persistGeneration(d.session_id, payload, d.music_params, d.patient_state, d.tracks);
    res.json({
      api_version: API_VERSION,
      session_id: d.session_id,
      patient_state: d.patient_state,
      music_params: d.music_params,
      consent: d.consent,
      tracks: shapeTracks(tracksWithLogIds),
      timestamp: d.timestamp,
    });
  } catch (error) {
    const status = error.response ? error.response.status : 502;
    res.status(status).json({
      error: 'generation_failed',
      message: error.response ? (error.response.data.error || 'ML server error') : error.message,
    });
  }
});

// -------- Submit feedback for a generated track --------
// Writes RLHF feedback directly to the platform DB (same DB where the
// generation_log row was created by persistGeneration). This avoids a
// fragile cross-machine proxy to the ML server's own DB connection.
router.post('/feedback', requireScope('feedback'), async (req, res) => {
  try {
    const b = req.body || {};
    // Accept both the v1 contract (generation_log_id/overall_rating) and the
    // legacy field names (log_id/rating) for backward compatibility.
    const generationLogId = b.generation_log_id ?? b.log_id;
    const overallRating = b.overall_rating ?? b.rating;

    if (generationLogId == null || overallRating == null) {
      return res.status(400).json({
        api_version: API_VERSION,
        error: 'invalid_request',
        message: 'generation_log_id (or log_id) and overall_rating (or rating) are required',
      });
    }

    // Validate the referenced generation exists so we return a clear 404
    // instead of orphaning a feedback row.
    const genRows = await dbQuery(
      `SELECT log_id FROM neurotunes_generation_log WHERE log_id = ?`,
      [generationLogId]
    );
    if (!genRows || genRows.length === 0) {
      return res.status(404).json({
        api_version: API_VERSION,
        error: 'not_found',
        message: `No generation found with log_id ${generationLogId}`,
      });
    }

    const clampEnum = (v, allowed) => (allowed.includes(v) ? v : null);
    const moodChange = clampEnum(b.mood_change, ['much_better', 'better', 'same', 'worse', 'much_worse']);
    const energyChange = clampEnum(b.energy_change, ['much_higher', 'higher', 'same', 'lower', 'much_lower']);
    const stressChange = clampEnum(b.stress_change, ['much_less', 'less', 'same', 'more', 'much_more']);
    const symptomImprovement = clampEnum(b.symptom_improvement, ['significant', 'moderate', 'slight', 'none', 'worse']);

    const result = await dbQuery(
      `INSERT INTO neurotunes_feedback_log
         (generation_log_id, user_name, overall_rating, effectiveness_rating,
          enjoyment_rating, reported_feeling, mood_change, energy_change, stress_change,
          feedback_text, listen_duration_seconds, replay_count, skipped_early,
          symptom_improvement, would_use_again, feedback_time)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())`,
      [
        generationLogId,
        b.user_name || null,
        overallRating,
        b.effectiveness_rating ?? overallRating,
        b.enjoyment_rating ?? overallRating,
        b.reported_feeling ?? b.mood_after ?? null,
        moodChange,
        energyChange,
        stressChange,
        b.feedback_text ?? b.comments ?? null,
        b.listen_duration_seconds ?? null,
        b.replay_count ?? 0,
        b.skipped_early ? 1 : 0,
        symptomImprovement,
        b.would_use_again === undefined ? null : (b.would_use_again ? 1 : 0),
      ]
    );

    res.json({
      api_version: API_VERSION,
      status: 'success',
      message: 'Feedback recorded',
      feedback_id: result.insertId,
      generation_log_id: generationLogId,
    });
  } catch (error) {
    res.status(503).json({ api_version: API_VERSION, error: 'db_unavailable', message: error.message });
  }
});

// -------- List sessions (durable, from DB) --------
router.get('/sessions', requireScope('sessions'), async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit, 10) || 100, 500);
    const rows = await dbQuery(
      `SELECT s.session_id, s.user_name, s.session_name, s.created_at, s.completed_at,
              COUNT(g.log_id) AS track_count, MAX(g.therapy_goal) AS therapy_goal
         FROM neurotunes_music_sessions s
         LEFT JOIN neurotunes_generation_log g ON g.session_id = s.session_id
        GROUP BY s.session_id, s.user_name, s.session_name, s.created_at, s.completed_at
        ORDER BY s.created_at DESC
        LIMIT ?`,
      [limit]
    );
    res.json({
      api_version: API_VERSION,
      count: rows.length,
      sessions: rows.map((r) => ({
        session_id: r.session_id,
        user_name: r.user_name,
        session_name: r.session_name,
        created_at: r.created_at,
        completed_at: r.completed_at,
        therapy_goal: r.therapy_goal,
        track_count: Number(r.track_count) || 0,
      })),
    });
  } catch (error) {
    res.status(503).json({ error: 'db_unavailable', message: error.message });
  }
});

// -------- Get one session with its generations --------
router.get('/sessions/:sessionId', requireScope('sessions'), async (req, res) => {
  try {
    const { sessionId } = req.params;
    const sRows = await dbQuery(
      `SELECT session_id, user_name, session_name, created_at, completed_at, session_notes
         FROM neurotunes_music_sessions WHERE session_id = ?`,
      [sessionId]
    );
    if (!sRows || sRows.length === 0) {
      return res.status(404).json({ error: 'not_found', message: 'Session not found' });
    }
    const gens = await dbQuery(
      `SELECT log_id, track_id, age, gender, primary_diagnosis, therapy_goal,
              current_mood, stress_level, sleep_quality, energy_level,
              patient_state, music_params, midi_filename, audio_filename,
              binaural_frequency, generation_timestamp
         FROM neurotunes_generation_log WHERE session_id = ? ORDER BY log_id ASC`,
      [sessionId]
    );
    const parse = (v) => (v == null ? null : typeof v === 'object' ? v : (() => { try { return JSON.parse(v); } catch { return v; } })());
    res.json({
      api_version: API_VERSION,
      session: {
        ...sRows[0],
        generations: (gens || []).map((g) => ({
          log_id: g.log_id,
          track_id: g.track_id,
          patient_data: {
            age: g.age,
            gender: g.gender,
            diagnosis: g.primary_diagnosis,
            therapy_goal: g.therapy_goal,
            current_mood: g.current_mood,
            stress_level: g.stress_level,
            sleep_quality: g.sleep_quality,
            energy_level: g.energy_level,
          },
          music_params: parse(g.music_params),
          patient_state: parse(g.patient_state),
          therapy_goal: g.therapy_goal,
          midi_url: g.midi_filename ? `/api/${API_VERSION}/download/${g.midi_filename}` : null,
          audio_url: g.audio_filename ? `/api/${API_VERSION}/download/${g.audio_filename}` : null,
          binaural_frequency: g.binaural_frequency,
          generation_time: g.generation_timestamp,
        })),
      },
    });
  } catch (error) {
    res.status(503).json({ error: 'db_unavailable', message: error.message });
  }
});

// -------- Aggregate RLHF training data (research export) --------
router.get('/research/training-data', requireScope('read'), async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit, 10) || 1000, 5000);
    const rows = await dbQuery(
      `SELECT * FROM neurotunes_rlhf_training_data ORDER BY feedback_time DESC LIMIT ?`,
      [limit]
    );
    res.json({ api_version: API_VERSION, count: rows.length, records: rows });
  } catch (error) {
    res.status(503).json({ error: 'db_unavailable', message: error.message });
  }
});

// -------- Download a generated file (proxied from ML server) --------
router.get('/download/:filename', requireScope('read'), async (req, res) => {
  try {
    const { filename } = req.params;
    const r = await axios.get(`${mlBaseUrl()}/download/${filename}`, { responseType: 'stream' });
    const ext = path.extname(filename).toLowerCase();
    if (ext === '.mid') res.setHeader('Content-Type', 'audio/midi');
    else if (ext === '.wav') res.setHeader('Content-Type', 'audio/wav');
    else if (ext === '.mp3') res.setHeader('Content-Type', 'audio/mpeg');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    r.data.pipe(res);
  } catch (error) {
    res.status(404).json({ error: 'file_not_found', message: 'File not found' });
  }
});

// ====================================================================
// Research Observatory endpoints
// --------------------------------------------------------------------
// Read-only introspection into the federated-learning network and the
// model-version registry, for the Researcher console's "Research
// Observatory". These proxy the federation (:5001) and versioning
// (:5002) services. When a service is unreachable they return
// { available: false, reason } (HTTP 200) so the UI can degrade
// gracefully instead of erroring — we never fabricate metrics.
// ====================================================================

// -------- Federated-learning network status --------
router.get('/federation/status', requireScope('read'), async (req, res) => {
  try {
    const r = await axios.get(`${federationBaseUrl()}/federation/status`, { timeout: 8000 });
    res.json({ api_version: API_VERSION, available: true, ...r.data });
  } catch (error) {
    res.json({
      api_version: API_VERSION,
      available: false,
      reason: 'Federation coordinator unreachable',
      detail: error.code || error.message,
    });
  }
});

// -------- Model-version registry (champion + history) --------
router.get('/models', requireScope('read'), async (req, res) => {
  const base = versioningBaseUrl();
  try {
    const [latest, history] = await Promise.allSettled([
      axios.get(`${base}/version/latest`, { timeout: 8000 }),
      axios.get(`${base}/version/history`, { timeout: 8000 }),
    ]);
    if (latest.status === 'rejected' && history.status === 'rejected') {
      const err = latest.reason || history.reason;
      return res.json({
        api_version: API_VERSION,
        available: false,
        reason: 'Model-versioning service unreachable',
        detail: (err && (err.code || err.message)) || 'unknown',
      });
    }
    res.json({
      api_version: API_VERSION,
      available: true,
      latest: latest.status === 'fulfilled' ? latest.value.data : null,
      history: history.status === 'fulfilled' ? history.value.data : null,
    });
  } catch (error) {
    res.json({
      api_version: API_VERSION,
      available: false,
      reason: 'Model-versioning service unreachable',
      detail: error.code || error.message,
    });
  }
});

export default router;
