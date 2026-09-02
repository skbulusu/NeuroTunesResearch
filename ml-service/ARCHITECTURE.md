# mlServer — architecture & pipeline map

This document is the map of the `mlServer/` package after the file cleanup: what
every remaining file is, and the exact script order for **inference** (serving)
and **training/retraining**.

> Cleanup note: `app.py.org` (stale backup), `demo.py` and `demo_singlemask.py`
> (scratch BioGPT / ClinicalBERT experiments, unrelated to the music pipeline)
> and `generate_dataset.py` (legacy persona CSV generator, superseded by
> `research/dataset_v3/` and `synthetic_data_generator.py`) were removed. They
> were unreferenced anywhere in the repo and remain in git history if needed.

---

## 1. The system in one paragraph

A patient assessment comes in over HTTP → **EmotionNet** (`neurotunes_model.py`)
maps it to a therapeutic affect vector `[arousal, valence, focus, calm]` →
**MusicGenerator** (`music_generator.py`) renders that target into a clinical
MIDI/audio track → the track + metadata are returned and the interaction is
logged (`data_logger.py`). Feedback logged over time feeds the **RewardNet**
(`reward_model.py`) and the **retraining scheduler** (`retraining_scheduler.py`),
which periodically produces improved EmotionNet weights. Model weights live in
the separate private repo `netrai/neurotunes-weights`, mounted at runtime via
`WEIGHTS_PATH`.

---

## 2. File inventory (what each remaining file is)

### 2.1 Serving / inference runtime (the live Flask app)
| File | Role |
| --- | --- |
| `wsgi.py` | WSGI entrypoint — imports `app`. What gunicorn runs. |
| `app.py` | Flask app + all HTTP routes (`/generate_music`, `/generate_music_irb`, `/feedback`, `/health`, `/download/<f>`). Loads EmotionNet, MusicGenerator, DataLogger, SafetyBoundaries at startup. |
| `neurotunes_model.py` | **EmotionNet** loader/definition (29→64→32→4, tanh). Reads weights from `WEIGHTS_PATH` (falls back to in-repo `models/`). `model.predict(assessment) -> [arousal, valence, focus, calm]`. |
| `music_generator.py` | **MusicGenerator** — turns the affect vector into clinical music params (tempo/mode/register/dynamics/instruments/binaural) and renders MIDI. Largest module. |
| `audio_postprocess.py` | Post-render audio touch-ups (used only by `music_generator.py`). |
| `safety_boundaries.py` | Clinical safety guardrails applied to generated params (tempo/volume limits, contraindications). Used by `app.py` + tests. |
| `common_utils.py` | Shared helpers used by `app.py`. |
| `data_logger.py` | `DataLogger` — DB access layer. Persists sessions/feedback, exposes `get_rlhf_training_data()`. Used by app, reward model, scheduler, synthetic generator. |

### 2.2 Deployment / infra
| File | Role |
| --- | --- |
| `gunicorn.conf.py` | Gunicorn config (workers/timeouts). |
| `Dockerfile.netraiML` | Container image for the ML server. |
| `requirements.txt` | Python deps for the server. |
| `.gitignore` | Ignore rules (outputs, weights, caches). |

### 2.3 Learning loop (reward + automated retraining)
| File | Role |
| --- | --- |
| `reward_model.py` | **RewardNet** — RLHF reward model over logged feedback (imports `data_logger`). |
| `retraining_scheduler.py` | Scheduled retraining job: pulls RLHF data via `DataLogger`, retrains, runs clinical/safety validation before promoting weights. Imports `reward_model` + `data_logger`. |
| `synthetic_data_generator.py` | Dev-only: seeds realistic synthetic feedback into the DB (via `DataLogger`) so the loop can be exercised without real users. Standalone utility. |

### 2.4 Federated-learning subsystem (multi-site; not used by the single-node server)
| File | Role |
| --- | --- |
| `site_client.py` | Local federated-learning client for a healthcare site (differential privacy, secure comms). |
| `secure_aggregation.py` | Privacy-preserving secure aggregation protocol for combining site updates. |
| `rabbitmq_integration.py` | RabbitMQ messaging client used to coordinate federation services. |

> These three are a self-contained subsystem. Nothing in the core server imports
> them; they run as their own processes in a federated deployment. Kept
> intentionally — delete only if you drop federation entirely.

### 2.5 Tests
| File | Role |
| --- | --- |
| `test_suite/neurotunes_test_suite.py` | End-to-end / integration tests. |
| `test_suite/test_safety_and_validation.py` | Safety + validation tests (exercises `safety_boundaries`, `reward_model`, `retraining_scheduler`). |

### 2.6 Data / weights directories
| Path | Role |
| --- | --- |
| `models/` | In-repo **v1** weights fallback (`emotion_net.pth`, `preprocessor.pkl`, `columns.pkl`, reward artifacts). Used when `WEIGHTS_PATH` is unset. |
| `data/synthetic_patient_data.csv` | Baseline synthetic patient assessments. |
| `synthetic_features.csv`, `synthetic_targets.csv` | Legacy root-level synthetic tables (unreferenced; kept for now — candidates for future removal). |
| `output/` | Generated MIDI (git-ignored, disposable). |

### 2.7 `training/` — production EmotionNet (re)training
See `training/README.md` for full detail. Summary:
| File | Role |
| --- | --- |
| `../train_pipeline.sh` | **ONE-COMMAND** orchestrator (lives at `mlServer/train_pipeline.sh`): dataset-gen → subset → LLM labels → distill → verify. See §4.1. |
| `make_first_session_subset.py` | Collapse the rich v3 trajectory data to ONE row per patient → `data/patients_v3_first_session.csv` (the shared training table). |
| `llm_pseudolabel.py` | **Stage 0** — open-source LLM (Qwen2.5-7B) annotates each patient with a soft target affect → `llm_labels.csv`. |
| `distill_from_llm.py` | **Stage 1** — distill those LLM labels into the production EmotionNet. |
| `stage2_music2emo_critic.py` | **Stage 2** — independent Music2Emo critic checks the rendered audio actually sounds like the intended affect. |
| `build_emotion_net_v2.py` | Leakage-free retrain of EmotionNet → drop-in artifacts in `out_v2/`. |
| `verify_dropin.py` | Loads v1 vs new weights through the real `NeuroTunesModel` loader and diffs behaviour (proves drop-in compatibility). |
| `ab_generate.py` | A/B harness: generate MIDI under old vs new weights and compare. |
| `track_qa.py` | Objective MIDI QA (note density, parameter conformance, duration) — no therapist needed. |
| `setup_distill.sh` | Sets up the distillation environment. |

### 2.8 `research/dataset_v3/` — scalable dataset + research models
See `research/dataset_v3/README.md`. Summary: `scale_pipeline.sh` orchestrates
`gen_profiles.py` → `ensemble_label.py` → `make_datasets.py` →
`coverage_report.py` → `train_emotionnet_v3.py` + `rewardnet.py`, producing a
large trajectory-mode dataset and saved research model weights.

---

## 3. INFERENCE pipeline (what runs to serve a request)

```
gunicorn -c gunicorn.conf.py wsgi:app        # process manager
  └─ wsgi.py            imports app
       └─ app.py        startup: load EmotionNet, MusicGenerator, DataLogger, SafetyBoundaries

POST /generate_music  (or /generate_music_irb)
  1. app.py            parse patient assessment
  2. neurotunes_model  EmotionNet.predict()  -> [arousal, valence, focus, calm]
  3. music_generator   affect -> clinical params -> render MIDI
        └─ audio_postprocess   final audio touch-ups
  4. safety_boundaries validate/clip params against clinical limits
  5. app.py            return track + metadata (download via /download/<file>)
  6. data_logger       persist the session

POST /feedback
  1. app.py            receive rating
  2. data_logger       persist feedback  (fuels the learning loop below)
```

Run locally:
```bash
source /home/ubuntu/m2e_env/bin/activate
cd mlServer
gunicorn -c gunicorn.conf.py wsgi:app          # or: python app.py  (dev)
# point at specific weights:
WEIGHTS_PATH=/weights/v2 gunicorn -c gunicorn.conf.py wsgi:app
```

---

## 4. TRAINING (what runs to produce/improve weights)

> IMPORTANT — these are **independent** tracks, NOT one linear chain. They do not
> feed each other. Read each block on its own. §4.1 is how you produce the
> deployed model. §4.2 improves it later from real feedback. §4.3 is a separate
> research sandbox that does NOT touch production.

### 4.1 Production EmotionNet — `training/`  (this is the one that makes deployed weights)

#### ONE COMMAND (recommended) — `train_pipeline.sh`
Runs the whole thing on the SAME rich v3 population, no separate dataset:
```bash
cd mlServer
bash train_pipeline.sh                    # defaults: 3000/1000 patients
bash train_pipeline.sh 72000 24000 scaled # larger run
LLM_LIMIT=50 bash train_pipeline.sh       # fast smoke test (label only 50 patients)
```
It chains, picking the right conda/venv per step automatically:
```
[1] research/dataset_v3/scale_pipeline.sh     rich v3 dataset + research models   [m2e_env]
[2] make_first_session_subset.py              v3 trajectory -> 1 row/patient
                                              -> data/patients_v3_first_session.csv  [nt_v2_env]
[3] llm_pseudolabel.py                         Qwen2.5-7B labels each patient       [nt_v2_env]
[4] distill_from_llm.py                         distill -> PRODUCTION EmotionNet      [nt_v2_env]
                                              -> training/out_v3/
[5] verify_dropin.py                            load out_v3/ the production way        [nt_v2_env]
```
> TWO ENVS: dataset generation runs in `m2e_env`; LLM + distill + verify run in
> `nt_v2_env` (which pins **scikit-learn 1.7.1** for the production preprocessor
> and provides **llama-cpp-python**). The script selects them via `DATAGEN_ENV`
> / `TRAIN_ENV` — override if your paths differ.
>
> NOTE: because the v3 data covers more diagnoses than the old data, the deployed
> EmotionNet input width grows (was 29, becomes ~45). This is expected and good —
> the loader reads the width from the saved artifacts, so no app change is needed.

Then deploy (Step C below). The manual breakdown follows for when you want to run
one stage at a time.

#### Manual breakdown

**Step A — choose ONE target source and train (they are mutually exclusive; run one, never both):**

```
OPTION 1 (recommended, "Ver3"):  llm_pseudolabel.py  ->  distill_from_llm.py
    llm_pseudolabel.py   LLM (Qwen2.5-7B) reads each patient -> llm_labels.csv  (soft clinical targets)
    distill_from_llm.py  distills those LLM labels into EmotionNet             -> out_v3/

OPTION 2 (LLM-free, "Ver2"):     build_emotion_net_v2.py
    build_emotion_net_v2.py  trains against a designer-specified "clean latent"
                             formula (no LLM needed)                           -> out_v2/
```
Both OPTIONS read the SAME input `data/synthetic_patient_data.csv` and both emit
the SAME set of drop-in artifacts (`emotion_net.pth`, `preprocessor.pkl`,
`columns.pkl`, `METRICS.txt`) — Option 1 into `out_v3/`, Option 2 into `out_v2/`.
**Pick Option 1 for a clinically defensible model (paper); pick Option 2 for a
fast retrain with no LLM.**

**Step B — verify + QA the weights you just built (these DON'T train anything; they check):**
```
verify_dropin.py            load new weights the production way, diff vs v1
stage2_music2emo_critic.py  audio critic: does rendered audio SOUND like the target?  (optional)
track_qa.py                 objective MIDI QA: density / conformance / duration        (optional)
ab_generate.py              generate MIDI old vs new weights, compare                  (optional)
```

**Step C — deploy** (use whichever dir you built: `out_v3/` for Option 1, `out_v2/` for Option 2):
```
copy out_v3/  ->  netrai/neurotunes-weights/v3   ;   set WEIGHTS_PATH=/weights/v3
```

### 4.2 Continuous RLHF loop — root (runs AFTER deploy, from real logged feedback)
Separate from §4.1. Improves the model over time once real users are giving feedback.
```
data_logger.get_rlhf_training_data()   pull logged sessions + feedback
   -> reward_model.py                  train/update RewardNet
   -> retraining_scheduler.py          scheduled retrain + clinical/safety validation
                                       -> promote new weights (or roll back)
synthetic_data_generator.py            (dev only) seed synthetic feedback to exercise the loop
```

### 4.3 Research sandbox — `research/dataset_v3/`  (NOT production; safe to ignore)
A self-contained experiment. It builds its OWN large dataset and trains its OWN
research models. It does **not** produce the deployed weights and is **not** part
of §4.1 or §4.2. Ignore this entirely unless you are specifically doing dataset
research.
```
bash scale_pipeline.sh <patients_balanced> <patients_natural> <out_dir>
  gen_profiles.py --rich -> ensemble_label.py -> make_datasets.py
  -> coverage_report.py -> train_emotionnet_v3.py + rewardnet.py
  (writes dataset + research weights into <out_dir>/, git-ignored)
```

---

## 5. Weights: where they live
- Runtime resolves weights from `WEIGHTS_PATH` (mounted `netrai/neurotunes-weights`),
  falling back to the in-repo `models/` (v1) dir.
- `training/` and `research/dataset_v3/` produce new weight artifacts; deploying =
  placing them in the weights repo and pointing `WEIGHTS_PATH` at the new version.
  Rollback is a one-line env change + restart. No app code change for a weights swap.
