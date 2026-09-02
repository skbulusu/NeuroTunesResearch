# NeuroTunes Research API — Python SDK

A thin, dependency-light Python client for the versioned NeuroTunes Research
API (`/api/v1`). Built for ML researchers and music therapists who want to
generate physiologically-informed therapeutic music, run IRB/consent-gated
studies, submit RLHF feedback, and export de-identified training data from
scripts or notebooks.

## Install

The SDK is a single file (`neurotunes_sdk.py`). Copy it into your project, or
add this directory to your `PYTHONPATH`. Its only dependency is `requests`:

```bash
pip install -r requirements.txt   # installs: requests
```

## Authentication

Every data endpoint requires an API key sent in the `X-API-Key` header. Ask
your NeuroTunes administrator to mint one for you (server operators: see
`server/scripts/create_api_key.js`). Keys look like `nt_live_...` and are
**scoped** — a key may hold any of `generate`, `feedback`, `sessions`, `read`.

## Quick start

```python
from neurotunes_sdk import NeuroTunesClient, NeuroTunesError

nt = NeuroTunesClient("https://your-neurotunes-host", api_key="nt_live_...")

# Public — no key required
print(nt.version())   # {'api_version': 'v1', ...}
print(nt.health())    # {'api_version': 'v1', 'status': 'ok', ...}

# Generate therapeutic music (scope: generate)
result = nt.generate(age=34, therapy_goal="relaxation", stress_level=7)
for track in result["tracks"]:
    print(track["track_id"], track["audio_url"])
```

## IRB / consent-gated generation (patent Claim 3)

For studies with human subjects, use `generate_irb`. The server refuses to
generate anything unless `consent_verified=True`, and records the optional
`consent_reference` with the session:

```python
try:
    result = nt.generate_irb(
        patient={"age": 34, "therapy_goal": "sleep", "stress_level": 6},
        consent_verified=True,
        consent_reference="IRB-2026-0142",
    )
except NeuroTunesError as e:
    if e.status_code == 403:
        print("Consent was not verified:", e.message)
```

## Feedback (RLHF)

```python
nt.submit_feedback(
    generation_log_id=812,
    overall_rating=4,
    effectiveness_rating=5,
    reported_feeling="calmer",
)
```

## Reading sessions & exporting training data

```python
sessions = nt.list_sessions(limit=50)          # scope: sessions
detail   = nt.get_session(sessions["sessions"][0]["session_id"])
records  = nt.research_training_data(limit=1000)  # scope: read

# Download a generated file (scope: read)
nt.download_to("track.mid", "/tmp/track.mid")
```

## Error handling

Any non-2xx response raises `NeuroTunesError` with `.status_code`, `.error`
(machine code), `.message`, and `.payload` (full JSON body).

## Interactive reference

A live, interactive Swagger UI is served by the deployment itself at
`/api/v1/docs`, backed by the machine-readable spec at `/api/v1/openapi.json`.
