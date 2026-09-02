// ====================================================================
// server/apiAuth.js  —  API-key authentication + per-key rate limiting
// --------------------------------------------------------------------
// Zero-cost, self-hosted machine-to-machine auth for the public
// /api/v1 programmatic API. Keys are random strings; only their SHA-256
// hash is stored in the neurotunes_api_keys table. No external service,
// no paid dependency — express-rate-limit (already a dependency) provides
// per-key throttling with an in-memory store.
//
// Usage in a router:
//   import { requireApiKey, apiKeyRateLimiter } from './apiAuth.js';
//   router.use(requireApiKey, apiKeyRateLimiter);
// ====================================================================

import crypto from 'crypto';
import rateLimit from 'express-rate-limit';
import { query as dbQuery } from './db.js';

export const API_KEY_PREFIX = 'nt_live_';

/** SHA-256 hex hash of a full API key (what we store & look up by). */
export function hashApiKey(key) {
  return crypto.createHash('sha256').update(String(key)).digest('hex');
}

/**
 * Generate a new random API key.
 * Returns { key, hash, prefix }. Only `key` is ever shown to the user
 * (once); only `hash` + `prefix` are persisted.
 */
export function generateApiKey() {
  const secret = crypto.randomBytes(24).toString('hex'); // 48 hex chars
  const key = `${API_KEY_PREFIX}${secret}`;
  return {
    key,
    hash: hashApiKey(key),
    prefix: key.slice(0, 12), // e.g. "nt_live_a1b2"
  };
}

/** Extract the presented key from X-API-Key or Authorization: Bearer. */
function extractKey(req) {
  const headerKey = req.get('X-API-Key');
  if (headerKey) return headerKey.trim();
  const auth = req.get('Authorization');
  if (auth && auth.toLowerCase().startsWith('bearer ')) {
    return auth.slice(7).trim();
  }
  return null;
}

/**
 * Express middleware: require a valid, active API key.
 * On success attaches req.apiKey = { id, name, scopes[], rate_limit_per_min }.
 */
export async function requireApiKey(req, res, next) {
  const presented = extractKey(req);
  if (!presented) {
    return res.status(401).json({
      error: 'missing_api_key',
      message: 'Provide your API key via the "X-API-Key" header or "Authorization: Bearer <key>".',
    });
  }

  try {
    const rows = await dbQuery(
      `SELECT id, name, scopes, rate_limit_per_min, active
         FROM neurotunes_api_keys
        WHERE api_key_hash = ? LIMIT 1`,
      [hashApiKey(presented)]
    );

    if (!rows || rows.length === 0 || !rows[0].active) {
      return res.status(401).json({
        error: 'invalid_api_key',
        message: 'The provided API key is invalid, revoked, or inactive.',
      });
    }

    const row = rows[0];
    req.apiKey = {
      id: row.id,
      name: row.name,
      scopes: (row.scopes || '').split(',').map((s) => s.trim()).filter(Boolean),
      rate_limit_per_min: row.rate_limit_per_min || 60,
    };

    // Fire-and-forget usage accounting (never blocks the request).
    dbQuery(
      `UPDATE neurotunes_api_keys
          SET last_used_at = CURRENT_TIMESTAMP, request_count = request_count + 1
        WHERE id = ?`,
      [row.id]
    ).catch((e) => console.error('api key usage update failed:', e.message));

    return next();
  } catch (error) {
    console.error('API key verification error:', error.message);
    return res.status(503).json({
      error: 'auth_unavailable',
      message: 'Authentication service is temporarily unavailable.',
    });
  }
}

/**
 * Per-key rate limiter. The window is 1 minute and the max is read
 * dynamically from each key's rate_limit_per_min. Falls back to the client
 * IP as the bucket key if (somehow) no authenticated key is present.
 */
export const apiKeyRateLimiter = rateLimit({
  windowMs: 60 * 1000,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => (req.apiKey ? `key:${req.apiKey.id}` : `ip:${req.ip}`),
  max: (req) => (req.apiKey ? req.apiKey.rate_limit_per_min : 30),
  message: {
    error: 'rate_limit_exceeded',
    message: 'Rate limit exceeded for this API key. Slow down and retry shortly.',
  },
});

/**
 * Optional scope guard factory.
 *   router.post('/generate', requireScope('generate'), handler)
 */
export function requireScope(scope) {
  return (req, res, next) => {
    if (req.apiKey && req.apiKey.scopes.includes(scope)) return next();
    return res.status(403).json({
      error: 'insufficient_scope',
      message: `This API key is missing the required "${scope}" scope.`,
    });
  };
}

export default { requireApiKey, apiKeyRateLimiter, requireScope, generateApiKey, hashApiKey, API_KEY_PREFIX };
