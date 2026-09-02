# NeuroTunes 

> **Open source, closed weights.** The code in this repository is released under
> Apache-2.0. The **trained model weights are not published here.** This card
> documents the models, how they are trained and evaluated, and how weights are
> supplied to a running deployment.
>
> **NeuroTunes — Patent Pending.** This is a **research platform for
> educational and research use only. It is not a medical device and does not
> provide medical advice, diagnosis, or treatment.**

---

## 1. Overview

NeuroTunes generates personalized, physiologically-informed therapeutic music
from a short description of a person's current state (e.g. mood, stress, energy,
therapy goal). It is built for two audiences: clinicians / music therapists
running consent-gated studies, and ML researchers who want a programmatic,
reproducible platform.

The system is composed of three trained components plus a deterministic music
renderer:

| Component | File | Role |
|---|---|---|
| **EmotionNet** | `mlServer/neurotunes_model.py` | Maps a preprocessed profile to a 4-dim affective state `[arousal, valence, focus, energy]`, then to clinical music parameters. |
| **RewardNet** | `mlServer/reward_model.py` | RLHF reward model trained on user/clinician feedback; drives periodic retraining. |
| **Federated / site models** | `mlServer/site_client.py`, `federation/` | Local site models aggregated by a federated coordinator with secure aggregation + differential privacy. |
| **Music generator** | `mlServer/music_generator.py` | Deterministic renderer: binaural-beat encoding + parameterized synthesis (not a learned generative audio model). |

## 2. Intended use

- **In scope:** research and education; generating candidate therapeutic audio
  for study; collecting RLHF feedback; federated / multi-site ML research;
  reproducible experiments via the `/api/v1` API and Python SDK.
- **Out of scope / prohibited:** clinical diagnosis or treatment; unsupervised
  use as a medical intervention; any use implying regulatory clearance. There is
  no FDA/CE clearance and none is claimed.

## 3. Architecture (shapes are fixed in code)

- **EmotionNet:** MLP `input → 64 → 32 → 4`, ReLU hidden, `tanh` output
  (bounded affective descriptors).
- **RewardNet:** MLP `input → 128 → 64 → 32 → 1`, ReLU + dropout (0.3).
- **Distillation (research):** a compact student is distilled from a larger
  teacher — teacher ≈ **202,972** parameters → student ≈ **4,196** parameters
  (see `research-papers/distillation/distill.py`).

## 4. Training data

- **Public affective-music / physiological datasets** used for pretraining and
  transfer: DEAM, PMEmo, EmoMusic, DEAP, combined with pretrained audio
  embeddings (MERT / CLAP / OpenL3).
- **Synthetic profile data** (`data/synthetic_patient_data.csv`) for the
  bootstrap EmotionNet when no trained artifact is present.
- **RLHF feedback** collected through the platform (de-identified) via the
  `rlhf_training_data` view; retraining requires a minimum of **50** feedback
  records before a run is eligible.

> **Data-leakage note (honest):** an earlier synthetic generator produced a
> degenerate target correlation (|corr| ≈ 1.00). This was fixed by
> `research-papers/distillation/generate_dataset_v2.py`, which reduces max feature/target
> correlation to ≈ 0.80. Reported metrics use the corrected data.

## 5. Evaluation 

- **Reward model:** held-out **R²** and **MSE** plus **5-fold cross-validation**
  (mean ± std) are computed by `reward_model.py` and persisted to
  `reward_metrics.json`.
- **Promotion gating (champion/challenger):** a retrained challenger is promoted
  only if its held-out R² ≥ champion R² − tolerance; otherwise the champion is
  restored (rollback).
- **Distillation result:** student trained on hard labels reached R² ≈ **0.917**;
  a distilled student reached R² ≈ **0.987**. This **+7.6% gain was obtained only
  via transfer / pretraining on public data** — plain self-distillation showed no
  gain. Reported as a research result, not a clinical claim.
- **Federated privacy:** secure aggregation (HE + Shamir) and differential
  privacy (ε = 1.0, δ = 1e-5) are implemented and verified **single-node /
  simulated**. Real cross-site empirical validation is **future work** and
  requires partner institutions.

Numbers above are reproducible from the code and the `research-papers/distillation/`
scripts; they are **not** to be read as validated clinical efficacy.

## 6. Safety & limitations

- A parameter **safety validator** (`mlServer/safety_boundaries.py`) hard-clamps
  tempo, binaural frequency, duration, and unit-interval descriptors, and emits
  recommended-range warnings, before any track is returned.
- A basic **IRB / informed-consent gate** (`verify_consent()` +
  `/generate_music_irb`) records a protocol reference with consent-gated
  sessions. In production research deployments this is required; the public demo
  console makes it optional so the platform is easy to try.
- Limitations: small models; synthetic-data bootstrap; no validated clinical
  outcomes; music renderer is parametric (not a learned audio generator);
  condition-specific adapters are not yet trained (see `docs/ROADMAP.md`).

## 7. Weights

Weights are **not** committed to this public repository. They are maintained
separately and supplied to a deployment at runtime.

- **Storage:** a private weights repository (not distributed in this release) holds the
  trained artifacts. Weights are distributed as **release assets** or via
  **Git LFS** — never as raw blobs in the public repo's history.
- **Expected artifacts** (per weights directory):
  `emotion_net.pth`, `preprocessor.pkl`, `columns.pkl`,
  `reward_model.pth`, `reward_scaler.pkl`, `reward_encoders.pkl`,
  `reward_columns.pkl`, `reward_metrics.json`.
- **Wiring into a deployment:**
  - Set **`WEIGHTS_PATH`** to the in-container directory the ML server should
    load from (consumed by `neurotunes_model.py` and `reward_model.py`).
    Defaults: `models` (EmotionNet) / `/app/models` (RewardNet) when unset.
  - Or set **`WEIGHTS_DIR`** (host path) in `docker-compose-ml.yml` to mount
    restored weights onto the default `/app/models` volume.
  - Example:
    ```bash
    # restore weights from the private repo (release asset or LFS), then:
    export WEIGHTS_DIR=/srv/neurotunes-weights
    docker compose -f docker-compose-ml.yml up -d
    ```
- If no weights are present, EmotionNet bootstraps a fresh model from synthetic
  data so the platform still runs; RewardNet is trained on the first eligible
  retraining run.

## 8. License

- **Code:** Apache-2.0 (see `LICENSE`, `NOTICE`).
- **Weights:** closed; access by arrangement with the author.
- **Patent:** Patent Pending (U.S. provisional application on file).
