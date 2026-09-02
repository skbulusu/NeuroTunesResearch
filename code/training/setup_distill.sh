#!/usr/bin/env bash
# =============================================================================
# setup_distill.sh — reproducible setup for the 2-stage model-improvement pipeline
#
#   Stage 1  llm_pseudolabel.py        : open-source LLM  -> soft therapeutic
#            distill_from_llm.py         labels -> distilled into production EmotionNet
#   Stage 2  stage2_music2emo_critic.py : Music2Emo objective critic (intended vs
#                                         perceived valence/arousal correlation)
#
# Targets, in order of preference:
#   (A) Dell XPS  RTX 2060 6GB   — GPU offload, fastest single box you own
#   (B) AWS       g5.xlarge (A10G 24GB) or g4dn.xlarge (T4 16GB) — if runtime matters
#   (C) CPU only  — works everywhere, slow (documented for completeness / the sandbox)
#
# Everything is deterministic (seed=42). Run from code/training/.
# Usage:  bash setup_distill.sh {cpu|cuda}     (default: cpu)
# =============================================================================
set -euo pipefail
MODE="${1:-cpu}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLSERVER="$(dirname "$HERE")"
MODEL_DIR="${MODEL_DIR:-$HOME/models_llm}"
MODEL_FILE="$MODEL_DIR/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
VENV="${VENV:-$HOME/nt_v2_env}"
M2E_REPO="${M2E_REPO:-$HOME/music2emo_repo}"

echo "== mode: $MODE  venv: $VENV =="

# ----------------------------------------------------------------------------
# 0. Python venv + base deps (Stage 1 distillation side)
# ----------------------------------------------------------------------------
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel setuptools
pip install "scikit-learn==1.7.1" pandas numpy joblib pretty_midi mido scipy huggingface_hub
# torch: pick the build that matches your box
if [ "$MODE" = "cuda" ]; then
  pip install torch --index-url https://download.pytorch.org/whl/cu121
else
  pip install torch --index-url https://download.pytorch.org/whl/cpu
fi

# ----------------------------------------------------------------------------
# 1. llama-cpp-python  (the LLM runtime for Stage 1 labeling)
#
#    IMPORTANT sandbox/CPU note: some virtualised Intel CPUs advertise AMX but
#    TRAP on it, and the PyPI wheel's runtime dispatch hits that -> SIGILL.
#    Building from source pinned to a safe ISA avoids it. Use cascadelake
#    (AVX-512, no AMX) on such CPUs; plain -march=native is fine on real HW.
# ----------------------------------------------------------------------------
if [ "$MODE" = "cuda" ]; then
  # RTX 2060 / A10G / T4 — CUDA offload. This is the fast path.
  CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir --force-reinstall llama-cpp-python
else
  # CPU. If you get "Illegal instruction", swap cascadelake for a safer arch
  # (e.g. haswell). On a normal desktop CPU you can use -march=native instead.
  CMAKE_ARGS="-DGGML_NATIVE=OFF -DCMAKE_C_FLAGS=-march=cascadelake -DCMAKE_CXX_FLAGS=-march=cascadelake" \
    pip install --no-cache-dir --force-reinstall llama-cpp-python
fi

# ----------------------------------------------------------------------------
# 2. Download the open-source teacher LLM  (Qwen2.5-7B-Instruct, Apache-2.0)
#    Q4_K_M ~4.7 GB; fits an RTX 2060 6GB with ~28 layers offloaded.
# ----------------------------------------------------------------------------
mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL_FILE" ]; then
  python - <<PY
from huggingface_hub import hf_hub_download
import shutil, os
p = hf_hub_download("bartowski/Qwen2.5-7B-Instruct-GGUF",
                    "Qwen2.5-7B-Instruct-Q4_K_M.gguf")
os.makedirs("$MODEL_DIR", exist_ok=True)
shutil.copy(p, "$MODEL_FILE")
print("model at", "$MODEL_FILE")
PY
fi

# ----------------------------------------------------------------------------
# 3. STAGE 1 — LLM pseudo-labels over the patient assessments
#    Throughput (Qwen-7B-Q4, measured / estimated):
#      CPU  ~8 cores  : ~50 s/row  -> 2000 rows ~= 28 h   (subset only!)
#      RTX 2060 (28L) : ~2-4 s/row -> 2000 rows ~= 1.5-2 h   <-- recommended
#      A10G / T4      : ~1-2 s/row -> 2000 rows ~= 30-60 min
#    On CPU, label a stratified SUBSET (see make_subset below), not all 2000.
# ----------------------------------------------------------------------------
if [ "$MODE" = "cuda" ]; then
  NGL=28   # RTX 2060 6GB; use -1 on a 24GB card to offload everything
  DATA="$MLSERVER/data/synthetic_patient_data.csv"     # full 2000 rows
else
  NGL=0
  DATA="$HERE/subset_stratified.csv"                   # stratified subset
  # build a balanced subset (80 per diagnosis x therapy_goal) if missing:
  [ -f "$DATA" ] || python - <<PY
import pandas as pd
df = pd.read_csv("$MLSERVER/data/synthetic_patient_data.csv")
sub = df.groupby(["diagnosis","therapy_goal"], group_keys=False).sample(n=80, random_state=42)
sub.sample(frac=1.0, random_state=42).reset_index(drop=True).to_csv("$DATA", index=False)
print("wrote", "$DATA", len(sub), "rows")
PY
fi

python llm_pseudolabel.py \
  --model "$MODEL_FILE" \
  --data "$DATA" \
  --out "$HERE/llm_labels.csv" \
  --n_gpu_layers "$NGL" \
  --n_threads "$(nproc)" \
  --seed 42

# ----------------------------------------------------------------------------
# 4. STAGE 1 — distill the LLM labels into the production EmotionNet
#    Writes drop-in Ver3 artifacts to out_v3/ (emotion_net.pth, preprocessor.pkl,
#    columns.pkl, METRICS.txt). Deploy by pointing WEIGHTS_PATH at out_v3/.
# ----------------------------------------------------------------------------
python distill_from_llm.py \
  --data "$MLSERVER/data/synthetic_patient_data.csv" \
  --labels "$HERE/llm_labels.csv" \
  --out "$HERE/out_v3" \
  --seed 42

echo
echo "== Stage 1 complete. Ver3 artifacts in $HERE/out_v3/ =="
echo

# ----------------------------------------------------------------------------
# 5. STAGE 2 — Music2Emo objective critic  (separate env: torch 2.3.1)
#    Correlates intended vs perceived valence/arousal over a generation grid.
# ----------------------------------------------------------------------------
M2E_VENV="${M2E_VENV:-$HOME/m2e_env}"
if [ ! -d "$M2E_REPO" ]; then
  git clone https://github.com/AMAAI-Lab/Music2Emotion.git "$M2E_REPO"
fi
python3 -m venv "$M2E_VENV"
# shellcheck disable=SC1091
source "$M2E_VENV/bin/activate"
pip install --upgrade pip "setuptools<81" wheel
if [ "$MODE" = "cuda" ]; then
  pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
else
  pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
fi
pip install numpy==1.26.4 transformers==4.44.0 librosa==0.10.2.post1 nnAudio==0.3.1 \
  music21==9.3.0 pretty_midi==0.2.10 omegaconf==2.3.0 hydra-core==1.3.2 \
  torchmetrics==1.4.1 pytorch_lightning==2.4.0 scikit_learn==1.6.1 \
  huggingface_hub==0.28.1 numba==0.60.0 llvmlite==0.43.0 chordparser==0.4.2 \
  pandas==2.2.3 tqdm==4.66.5 PyYAML==6.0.1 mir_eval gradio==5.15.0 fire torch_optimizer spotipy
# FluidSynth renders the generated MIDI -> WAV for the critic:
#   Ubuntu/Debian:  sudo apt-get install -y fluidsynth fluid-soundfont-gm
command -v fluidsynth >/dev/null || echo "WARNING: install fluidsynth (see line above)"

python "$HERE/stage2_music2emo_critic.py" \
  --m2e_repo "$M2E_REPO" \
  --out "$HERE/out_stage2" \
  --grid 4

echo
echo "== Stage 2 complete. Correlation + per-track results in $HERE/out_stage2/ =="
echo "== Pipeline done. =="
