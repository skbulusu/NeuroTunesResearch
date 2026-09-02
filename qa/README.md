# QA — end-to-end verification scripts

Runnable checks that exercise the **live** NeuroTunes services (API + ML + DB) the
way a real client would. These are black-box smoke/acceptance tests, not unit tests
(unit/model tests live under `mlServer/` and `server/`).

| Script | What it verifies | How to run |
|--------|------------------|------------|
| `test_researcher_api.sh` | Full researcher API: auth (`/api/v1/me`), generation (`/api/v1/generate`), feedback, session detail, and downloaded-audio loudness — across 4 therapy goals. Fails non-zero on any broken step. | `./test_researcher_api.sh [BASE_URL] <API_KEY>` |

## Notes
- `BASE_URL` defaults to `https://www.netr.ai`; pass a different origin to test staging/local.
- An API key with `generate`, `feedback`, and `sessions` scopes is required.
- These scripts hit a running deployment — they do **not** stand anything up themselves.
