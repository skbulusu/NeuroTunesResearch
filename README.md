# NeuroTunes

This repository accompanies our submission to NeurIPS GenAI4Health 2026
(Demonstration track). NeuroTunes is a research/education platform and
not a medical device. We don't make any clinical efficacy claims.

## Overview

Before any human study or IRB protocol, we wanted a way to build, run, and
stress-test a therapeutic-music pipeline end-to-end -- not just as an offline
model, but as a real platform three kinds of users can actually touch. This
repo has the pieces that make both the platform and its evaluation
reproducible:

- a consent-gated API serving three personas (patient, clinician, researcher)
  through one request path: assessment -> EmotionNet -> deterministic
  renderer -> safety validator -> delivered audio
- a synthetic longitudinal patient-cohort generator (14 conditions, explicit
  realism axes like medication adherence and response archetype)
- an open-weight LLM used as a deterministic clinical annotator, paired with
  a simulated multi-rater uncertainty model that flags low-confidence labels
- EmotionNet, the small deployable model trained on those labels
- a distillation ablation
- an independent, MERT-based audio critic (Music2Emo) that sits in the
  promote/rollback gate for retraining
- a Python SDK and versioned REST API for researchers

Trained weights aren't included in this repo. All weights are closed, see
`NOTICE` / `MODEL_CARD.md`.

## Layout

- `code/dataset/`
- `code/training/`
- `code/train_pipeline.sh`
- `distillation/`
- `results/`
- `ml-service/` -- EmotionNet, music generator, safety validator, RewardNet
- `api/` -- Express API gateway (`/api/v1`)
- `web/` -- Next.js client (patient / clinician / researcher UI)
- `clinical/` -- Clinical Console backend
- `federation/`, `versioning/` -- simulated secure-aggregation/DP layer and
  the model registry behind the champion/challenger promotion gate
- `shared/` -- utilities used across the Python services
- `sdk/` -- Python research SDK
- `db/` -- database schema
- `deploy/` -- docker-compose files, Caddy config
- `qa/` -- API smoke test

## Reproducibility

### Setup

```bash
git clone https://github.com/skbulusu/NeuroTunesDemoTrack.git
cd NeuroTunesDemoTrack
pip install -r code/requirements.txt
```

### Pipeline

```bash
cd code
bash train_pipeline.sh --help          # see all flags
# small CPU smoke run:
bash train_pipeline.sh --patients-balanced 300 --patients-natural 100 \
  --out smoke --seed 42 --cpu-threads 0
```

### Distillation

```bash
cd distillation
pip install -r requirements.txt
./run_all.sh
```

### Individual pieces (self-contained)

```bash
cd code/dataset
python gen_profiles.py          # cohort generation
python ensemble_label.py        # LLM-ensemble labeling + confidence
python make_datasets.py         # balanced + natural-prevalence splits
python coverage_report.py       # dataset QA report
python train_emotionnet_v3.py   # EmotionNet R² on held-out data
python rewardnet.py             # RLHF reward-model scaffold
```

### Running the platform

```bash
docker compose -f deploy/docker-compose-core.yml up -d --build
docker compose -f deploy/docker-compose-ml.yml up -d --build
```

Open `http://localhost:3000`. Mint yourself a local API key with
`node api/scripts/create_api_key.js "demo key"`, then use it in the
researcher console or with the SDK. `qa/test_researcher_api.sh` is a
scripted smoke test against a running instance.

## License

Apache-2.0, see `LICENSE`. The methods here are the subject of a pending
U.S. patent application — see `NOTICE`. Trained weights are closed. See
`MODEL_CARD.md`.
