// ====================================================================
// server/openapi.js  —  OpenAPI 3.0 description of the NeuroTunes /api/v1
// --------------------------------------------------------------------
// Exported as a plain JS object so we need NO YAML parser or extra build
// dependency. Served at GET /api/v1/openapi.json and rendered by a
// CDN-hosted Swagger UI at GET /api/v1/docs (see apiV1.js). Keeping the
// spec here (single source of truth) means the interactive docs, the
// Python SDK, and the router stay in agreement.
// ====================================================================

export const openApiSpec = {
  openapi: '3.0.3',
  info: {
    title: 'NeuroTunes Research API',
    version: '1.0.0',
    description:
      'Programmatic, versioned access to the NeuroTunes therapeutic-music '
      + 'engine for ML researchers and music therapists. Generate '
      + 'physiologically-informed music, run IRB/consent-gated studies, '
      + 'submit RLHF feedback, and export de-identified training data.\n\n'
      + '**Authentication:** every data endpoint requires an API key passed '
      + 'in the `X-API-Key` header. Request a key from your NeuroTunes '
      + 'administrator (see `server/scripts/create_api_key.js`). Each key is '
      + 'scoped (`generate`, `feedback`, `sessions`, `read`) and rate limited '
      + 'per minute.',
    license: { name: 'Open Source' },
  },
  servers: [
    { url: '/api/v1', description: 'This deployment' },
  ],
  tags: [
    { name: 'Status', description: 'Public health & version (no key required)' },
    { name: 'Generation', description: 'Generate therapeutic music' },
    { name: 'Feedback', description: 'Submit RLHF feedback' },
    { name: 'Sessions', description: 'Read persisted therapy sessions' },
    { name: 'Research', description: 'Export aggregate training data' },
    { name: 'Observatory', description: 'Federated-network & model-version introspection' },
  ],
  components: {
    securitySchemes: {
      ApiKeyAuth: { type: 'apiKey', in: 'header', name: 'X-API-Key' },
    },
    schemas: {
      PatientData: {
        type: 'object',
        description: 'Physiological / self-report inputs for one generation.',
        properties: {
          age: { type: 'integer', example: 34 },
          gender: { type: 'string', example: 'female' },
          diagnosis: { type: 'string', example: 'generalized anxiety' },
          therapy_goal: {
            type: 'string',
            example: 'relaxation',
            description: 'e.g. relaxation, focus, sleep, mood_lift, energy',
          },
          stress_level: { type: 'integer', minimum: 1, maximum: 10, example: 7 },
          sleep_quality: { type: 'integer', minimum: 1, maximum: 10, example: 4 },
          energy_levels: { type: 'integer', minimum: 1, maximum: 10, example: 5 },
          mood: { type: 'string', example: 'anxious' },
        },
      },
      Consent: {
        type: 'object',
        required: ['consent_verified'],
        description: 'IRB / informed-consent attestation (patent Claim 3).',
        properties: {
          consent_verified: {
            type: 'boolean',
            example: true,
            description: 'Must be true or the request is rejected with 403.',
          },
          consent_reference: {
            type: 'string',
            example: 'IRB-2026-0142',
            description: 'Optional study / consent identifier stored with the session.',
          },
        },
      },
      Track: {
        type: 'object',
        properties: {
          track_id: { type: 'string' },
          log_id: { type: 'integer' },
          tempo: { type: 'number' },
          key: { type: 'string' },
          mode: { type: 'string' },
          midi_url: { type: 'string', nullable: true },
          audio_url: { type: 'string', nullable: true },
        },
      },
      GenerationResult: {
        type: 'object',
        properties: {
          api_version: { type: 'string', example: 'v1' },
          session_id: { type: 'string' },
          patient_state: { type: 'object', additionalProperties: true },
          music_params: { type: 'object', additionalProperties: true },
          tracks: { type: 'array', items: { $ref: '#/components/schemas/Track' } },
          timestamp: { type: 'string' },
        },
      },
      Error: {
        type: 'object',
        properties: {
          error: { type: 'string', example: 'unauthorized' },
          message: { type: 'string' },
        },
      },
    },
  },
  security: [{ ApiKeyAuth: [] }],
  paths: {
    '/version': {
      get: {
        tags: ['Status'], summary: 'API name & version', security: [],
        responses: { 200: { description: 'OK' } },
      },
    },
    '/health': {
      get: {
        tags: ['Status'], summary: 'Health of API, ML server and database', security: [],
        responses: { 200: { description: 'OK' } },
      },
    },
    '/me': {
      get: {
        tags: ['Status'], summary: 'Describe the calling API key (id, name, scopes)',
        responses: {
          200: { description: 'Key info' },
          401: { description: 'Missing/invalid key', content: { 'application/json': { schema: { $ref: '#/components/schemas/Error' } } } },
        },
      },
    },
    '/generate': {
      post: {
        tags: ['Generation'], summary: 'Generate therapeutic music',
        description: 'Requires the `generate` scope. Proxies to the ML engine and returns generated tracks.',
        requestBody: {
          required: true,
          content: { 'application/json': { schema: { $ref: '#/components/schemas/PatientData' } } },
        },
        responses: {
          200: { description: 'Tracks generated', content: { 'application/json': { schema: { $ref: '#/components/schemas/GenerationResult' } } } },
          401: { description: 'Missing/invalid key' },
          403: { description: 'Insufficient scope' },
          502: { description: 'ML server error' },
        },
      },
    },
    '/generate_irb': {
      post: {
        tags: ['Generation'],
        summary: 'Generate under verified IRB / informed consent (patent Claim 3)',
        description: 'Requires the `generate` scope AND `consent.consent_verified = true`. '
          + 'If consent is not verified the request is rejected with 403 and no music is generated.',
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: {
                allOf: [
                  { $ref: '#/components/schemas/PatientData' },
                  { type: 'object', properties: { consent: { $ref: '#/components/schemas/Consent' } }, required: ['consent'] },
                ],
              },
            },
          },
        },
        responses: {
          200: { description: 'Tracks generated with consent recorded' },
          401: { description: 'Missing/invalid key' },
          403: { description: 'Consent not verified or insufficient scope' },
          502: { description: 'ML server error' },
        },
      },
    },
    '/feedback': {
      post: {
        tags: ['Feedback'], summary: 'Submit RLHF feedback for a generated track',
        description: 'Requires the `feedback` scope.',
        requestBody: {
          required: true,
          content: {
            'application/json': {
              schema: {
                type: 'object',
                properties: {
                  generation_log_id: { type: 'integer', example: 812 },
                  overall_rating: { type: 'integer', minimum: 1, maximum: 5, example: 4 },
                  effectiveness_rating: { type: 'integer', minimum: 1, maximum: 5 },
                  enjoyment_rating: { type: 'integer', minimum: 1, maximum: 5 },
                  reported_feeling: { type: 'string' },
                },
              },
            },
          },
        },
        responses: { 200: { description: 'Recorded' }, 401: { description: 'Missing/invalid key' }, 403: { description: 'Insufficient scope' } },
      },
    },
    '/sessions': {
      get: {
        tags: ['Sessions'], summary: 'List persisted therapy sessions',
        description: 'Requires the `sessions` scope.',
        parameters: [{ name: 'limit', in: 'query', schema: { type: 'integer', default: 100, maximum: 500 } }],
        responses: { 200: { description: 'Session list' }, 401: { description: 'Missing/invalid key' }, 403: { description: 'Insufficient scope' }, 503: { description: 'Database unavailable' } },
      },
    },
    '/sessions/{sessionId}': {
      get: {
        tags: ['Sessions'], summary: 'Get one session with its generations',
        description: 'Requires the `sessions` scope.',
        parameters: [{ name: 'sessionId', in: 'path', required: true, schema: { type: 'string' } }],
        responses: { 200: { description: 'Session detail' }, 401: { description: 'Missing/invalid key' }, 404: { description: 'Not found' }, 503: { description: 'Database unavailable' } },
      },
    },
    '/research/training-data': {
      get: {
        tags: ['Research'], summary: 'Export aggregate RLHF training data',
        description: 'Requires the `read` scope. Returns de-identified feedback+generation rows from the RLHF training view.',
        parameters: [{ name: 'limit', in: 'query', schema: { type: 'integer', default: 1000, maximum: 5000 } }],
        responses: { 200: { description: 'Training records' }, 401: { description: 'Missing/invalid key' }, 403: { description: 'Insufficient scope' }, 503: { description: 'Database unavailable' } },
      },
    },
    '/download/{filename}': {
      get: {
        tags: ['Research'], summary: 'Download a generated MIDI/audio file',
        description: 'Requires the `read` scope.',
        parameters: [{ name: 'filename', in: 'path', required: true, schema: { type: 'string' } }],
        responses: { 200: { description: 'File stream' }, 401: { description: 'Missing/invalid key' }, 404: { description: 'File not found' } },
      },
    },
    '/federation/status': {
      get: {
        tags: ['Observatory'], summary: 'Federated-learning network status',
        description: 'Requires the `read` scope. Proxies the federation coordinator: registered/active sites, current round, global model, per-site clinical metrics and remaining privacy budget. If the coordinator is unreachable, returns `{ available: false, reason }` with HTTP 200 (never fabricated data).',
        responses: { 200: { description: 'Federation status (or availability=false)' }, 401: { description: 'Missing/invalid key' }, 403: { description: 'Insufficient scope' } },
      },
    },
    '/models': {
      get: {
        tags: ['Observatory'], summary: 'Model-version registry (champion + history)',
        description: 'Requires the `read` scope. Proxies the model-versioning service for the latest (champion) model and version history with performance/clinical metrics. If the service is unreachable, returns `{ available: false, reason }` with HTTP 200.',
        responses: { 200: { description: 'Model versions (or availability=false)' }, 401: { description: 'Missing/invalid key' }, 403: { description: 'Insufficient scope' } },
      },
    },
  },
};

// Swagger UI served from CDN (no extra npm dependency, no build change).
export function swaggerHtml(specUrl) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NeuroTunes Research API — Reference</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css" />
  <style>
    body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .topbar { display: none; }
    .nt-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff; padding: 22px 28px;
    }
    .nt-header h1 { margin: 0; font-size: 22px; }
    .nt-header p { margin: 6px 0 0; opacity: 0.92; font-size: 14px; }
  </style>
</head>
<body>
  <div class="nt-header">
    <h1>NeuroTunes Research API</h1>
    <p>Interactive reference &middot; authenticate with your <code>X-API-Key</code> using the “Authorize” button.</p>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js" crossorigin></script>
  <script>
    window.onload = function () {
      window.ui = SwaggerUIBundle({
        url: '${specUrl}',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
        layout: 'BaseLayout',
      });
    };
  </script>
</body>
</html>`;
}
