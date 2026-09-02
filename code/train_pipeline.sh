#!/usr/bin/env bash
# =============================================================================
# train_pipeline.sh -- ONE command, the WHOLE production training pipeline.
#
# It runs, in order:
#   [1] DATASET GENERATION (rich v3)      dataset/scale_pipeline.sh
#         gen_profiles --rich --mode trajectory -> ensemble_label -> make_datasets
#         -> coverage_report -> train_emotionnet_v3 + rewardnet   (research models)
#   [2] FIRST-SESSION SUBSET              make_first_session_subset.py
#         collapse the v3 trajectory data to ONE row per patient
#         -> data/patients_v3_first_session.csv
#   [3] LLM PSEUDO-LABELS                 llm_pseudolabel.py
#         Qwen2.5-7B labels each patient with a target affect -> llm_labels.csv
#   [4] DISTILL -> PRODUCTION EmotionNet  distill_from_llm.py
#         distills the LLM labels into the deployed EmotionNet -> training/out_v3/
#   [5] VERIFY DROP-IN                    verify_dropin.py
#         loads out_v3/ the production way and diffs behaviour vs v1
#
# Everything trains on the SAME rich v3 population -- no separate dataset.
# =============================================================================
set -euo pipefail

# ---- defaults ------------------------------------------------------------
PB=3000                # patients_balanced (training set size)
PN=1000                # patients_natural (eval set size)
OUT="scaled"           # output directory under dataset/
SEED=42                # reproducibility master seed (controls ALL rng)
SESSIONS_MIN=3         # min sessions per patient trajectory
SESSIONS_MAX=25        # max sessions per patient trajectory
LLM_LIMIT=0            # 0 = label all patients; >0 = label first N only
LLM_MODEL=""           # LLM .gguf path; empty = auto-detect or llm_pseudolabel.py default
GPU_LAYERS=0           # 0 = CPU; -1 = offload all layers; 20-33 = partial (RTX 2060/3050)
CPU_THREADS=0          # 0 = auto (50% of cores, min 1); >0 = use exactly that many CPU threads
SKIP_DATAGEN=0         # 1 = skip step [1], reuse existing dataset
DATAGEN_ENV="${DATAGEN_ENV:-$HOME/m2e_env}"
TRAIN_ENV="${TRAIN_ENV:-$HOME/nt_v2_env}"

# ---- help ----------------------------------------------------------------
show_help() {
  cat << 'EOF'
train_pipeline.sh -- ONE command, the WHOLE production training pipeline.

USAGE:
  bash train_pipeline.sh [OPTIONS]
  bash train_pipeline.sh [patients_balanced] [patients_natural] [out_dir]  # legacy positional

OPTIONS:
  --patients-balanced N   Training patients (default: 3000)
  --patients-natural N    Eval patients (default: 1000)
  --out DIR              Output directory under dataset/ (default: scaled)
  --seed N               Reproducibility seed (controls ALL rng; default: 42)
  --sessions-min N       Min sessions per patient trajectory (default: 3)
  --sessions-max N       Max sessions per patient trajectory (default: 25)
  --llm-limit N          Label only first N patients; 0=all (default: 0)
  --llm-model PATH       LLM .gguf file path (default: auto-detect or llm_pseudolabel.py default)
  --gpu-layers N         GPU layers for LLM: 0=CPU, -1=all, 20-33=partial (default: 0)
  --cpu-threads N        CPU threads for ALL stages (LLM sampling, datagen, distill).
                         0=auto (50% of cores, keeps machine usable); >0=exact count
                         (default: 0). Use this if training makes your desktop unusable.
  --skip-datagen         Reuse existing dataset, skip step [1]
  --datagen-env PATH     Python env for dataset gen (default: /home/ubuntu/m2e_env)
  --train-env PATH       Python env for training (default: /home/ubuntu/nt_v2_env)
  -h, --help            Show this help

EXAMPLES:
  # Default (~205K rows, CPU LLM)
  bash train_pipeline.sh

  # 1M dataset, GPU-accelerated LLM (label 25K patients on RTX 3050)
  bash train_pipeline.sh --patients-balanced 72000 --patients-natural 24000 \
    --llm-limit 25000 --gpu-layers -1 --out scaled_1m \
    --llm-model ~/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf

  # Resume: label 15K more (total 40K), reuse dataset
  bash train_pipeline.sh --skip-datagen --llm-limit 40000 --gpu-layers -1 --out scaled_1m

  # Resume but keep the desktop usable (use only half the CPU cores):
  bash train_pipeline.sh --skip-datagen --out seed42 --seed 42 --gpu-layers -1 \
    --llm-limit 25000 --cpu-threads 0 \
    --llm-model ~/models_llm/Qwen2.5-7B-Instruct-Q4_K_M.gguf

  # Robustness check with different seed (for NeurIPS paper)
  bash train_pipeline.sh --seed 999 --out seed999

MULTI-SEED ROBUSTNESS (for research papers):
  Run 3–5 independent populations with DIFFERENT --out dirs per seed:
    bash train_pipeline.sh --seed 42 --out seed42 --llm-limit 25000 --gpu-layers -1
    bash train_pipeline.sh --seed 123 --out seed123 --llm-limit 25000 --gpu-layers -1
    bash train_pipeline.sh --seed 999 --out seed999 --llm-limit 25000 --gpu-layers -1
  
  Each seed generates isolated datasets + labels + models:
    dataset/seed42/    training/llm_labels_seed42.csv    training/out_v3_seed42/
    dataset/seed123/   training/llm_labels_seed123.csv   training/out_v3_seed123/
    dataset/seed999/   training/llm_labels_seed999.csv   training/out_v3_seed999/
  
  Report: mean ± std across seeds (e.g., "R² = 0.85 ± 0.02 over 3 seeds")
  DO NOT reuse same --out across seeds (overwrites dataset, mixes labels!)

SEED CONTROLS (same seed = bit-identical outputs on same hardware):
  - Which 72K patients get generated (ages, diagnoses, archetypes)
  - Session-to-session mood/stress trajectories for each patient
  - Ensemble raters' label noise
  - Train/val/test splits
  - Model weight initialization

TWO PYTHON ENVS (picked automatically per step):
  DATAGEN_ENV  dataset generation (step 1); needs sklearn 1.6.1
  TRAIN_ENV    LLM + distill + verify (steps 2-5); needs sklearn 1.7.1 + llama-cpp-python

OUTPUT STRUCTURE (for --out=scaled):
  dataset/scaled/          ← step 1 dataset (~1.3M rows for 72K+24K)
  data/patients_v3_first_session.csv   ← step 2 (96K patients, one row each)
  training/llm_labels_scaled.csv       ← step 3 (N rows, where N = llm_limit or 96K)
  training/out_v3_scaled/              ← step 4 production weights
  
  Different --out values create isolated dirs (for multi-seed robustness)
EOF
}

# ---- parse args ----------------------------------------------------------
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    --patients-balanced)
      PB="$2"
      shift 2
      ;;
    --patients-natural)
      PN="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    --seed)
      SEED="$2"
      shift 2
      ;;
    --sessions-min)
      SESSIONS_MIN="$2"
      shift 2
      ;;
    --sessions-max)
      SESSIONS_MAX="$2"
      shift 2
      ;;
    --llm-limit)
      LLM_LIMIT="$2"
      shift 2
      ;;
    --llm-model)
      LLM_MODEL="$2"
      shift 2
      ;;
    --gpu-layers)
      GPU_LAYERS="$2"
      shift 2
      ;;
    --cpu-threads)
      CPU_THREADS="$2"
      shift 2
      ;;
    --skip-datagen)
      SKIP_DATAGEN=1
      shift
      ;;
    --datagen-env)
      DATAGEN_ENV="$2"
      shift 2
      ;;
    --train-env)
      TRAIN_ENV="$2"
      shift 2
      ;;
    -*)
      echo "ERROR: unknown flag: $1" >&2
      echo "Run with --help for usage." >&2
      exit 1
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

# backward compat: positional args override defaults
[[ ${#POSITIONAL[@]} -ge 1 ]] && PB="${POSITIONAL[0]}"
[[ ${#POSITIONAL[@]} -ge 2 ]] && PN="${POSITIONAL[1]}"
[[ ${#POSITIONAL[@]} -ge 3 ]] && OUT="${POSITIONAL[2]}"

ML="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"      # code/
DV3="$ML/dataset"
TR="$ML/training"
SUBSET="$ML/data/patients_v3_first_session.csv"
PROFILES="$DV3/$OUT/profiles_balanced_v3.csv"
LLM_LABELS="$TR/llm_labels_${OUT}.csv"          # per-seed label file
DISTILL_OUT="$TR/out_v3_${OUT}"                 # per-seed production weights

TRAIN_PY="$TRAIN_ENV/bin/python"
[[ -x "$TRAIN_PY" ]] || { echo "ERROR: TRAIN_ENV python not found: $TRAIN_PY"; exit 1; }

# ---- CPU thread budget (keep the machine usable during training) ---------
NCORES="$(nproc 2>/dev/null || echo 4)"
if [[ "$CPU_THREADS" == "0" ]]; then
  # auto: 50% of cores, at least 1
  EFF_THREADS=$(( NCORES / 2 ))
  [[ "$EFF_THREADS" -lt 1 ]] && EFF_THREADS=1
else
  EFF_THREADS="$CPU_THREADS"
fi
# Cap thread-pool libraries used by numpy/sklearn/torch in EVERY stage so no
# single step can grab all cores and freeze the desktop.
export OMP_NUM_THREADS="$EFF_THREADS"
export OPENBLAS_NUM_THREADS="$EFF_THREADS"
export MKL_NUM_THREADS="$EFF_THREADS"
export NUMEXPR_NUM_THREADS="$EFF_THREADS"
export VECLIB_MAXIMUM_THREADS="$EFF_THREADS"
export TORCH_NUM_THREADS="$EFF_THREADS"
echo "CPU thread budget: $EFF_THREADS of $NCORES cores  (--cpu-threads=$CPU_THREADS)"

echo "############################################################"
echo "# [1/5] DATASET GENERATION (rich v3)  ->  $DV3/$OUT/   [env: $DATAGEN_ENV]"
echo "############################################################"
if [[ "$SKIP_DATAGEN" == "1" ]]; then
  echo "SKIP_DATAGEN -> reusing existing $PROFILES"
else
  # scale_pipeline.sh calls bare `python`, so run it inside the datagen env.
  ( source "$DATAGEN_ENV/bin/activate" && \
    SESSIONS_MIN="$SESSIONS_MIN" SESSIONS_MAX="$SESSIONS_MAX" \
    bash "$DV3/scale_pipeline.sh" "$PB" "$PN" "$OUT" "$SEED" )
fi
[[ -f "$PROFILES" ]] || { echo "ERROR: expected profiles not found: $PROFILES"; exit 1; }

echo
echo "############################################################"
echo "# [2/5] FIRST-SESSION SUBSET  ->  $SUBSET   [env: $TRAIN_ENV]"
echo "############################################################"
"$TRAIN_PY" "$TR/make_first_session_subset.py" --profiles "$PROFILES" --out "$SUBSET"

echo
echo "############################################################"
echo "# [3/5] LLM PSEUDO-LABELS  (Qwen2.5-7B)  ->  $LLM_LABELS   [env: $TRAIN_ENV]"
echo "############################################################"
LIMIT_ARG=()
[[ "$LLM_LIMIT" != "0" ]] && LIMIT_ARG=(--limit "$LLM_LIMIT") && \
  echo "NOTE: LLM_LIMIT=$LLM_LIMIT (labeling only the first $LLM_LIMIT patients)"
[[ "$GPU_LAYERS" != "0" ]] && echo "NOTE: GPU_LAYERS=$GPU_LAYERS (GPU offload enabled)"
MODEL_ARG=()
[[ -n "$LLM_MODEL" ]] && MODEL_ARG=(--model "$LLM_MODEL") && \
  echo "NOTE: LLM_MODEL=$LLM_MODEL"
echo "NOTE: CPU threads for LLM sampling = $EFF_THREADS"
"$TRAIN_PY" "$TR/llm_pseudolabel.py" --data "$SUBSET" --out "$LLM_LABELS" \
  --seed "$SEED" --n_gpu_layers "$GPU_LAYERS" --n_threads "$EFF_THREADS" \
  "${MODEL_ARG[@]}" "${LIMIT_ARG[@]}"

echo
echo "############################################################"
echo "# [4/5] DISTILL -> PRODUCTION EmotionNet  ->  $DISTILL_OUT/   [env: $TRAIN_ENV]"
echo "############################################################"
"$TRAIN_PY" "$TR/distill_from_llm.py" --data "$SUBSET" \
  --labels "$LLM_LABELS" --out "$DISTILL_OUT" --seed "$SEED"

echo
echo "############################################################"
echo "# [5/5] VERIFY DROP-IN  ($DISTILL_OUT/ vs v1, production loader)   [env: $TRAIN_ENV]"
echo "############################################################"
"$TRAIN_PY" "$TR/verify_dropin.py" --new "$DISTILL_OUT"

echo
echo "== DONE. Production EmotionNet weights in: $DISTILL_OUT/ =="
echo "   Dataset:  $DV3/$OUT/"
echo "   Labels:   $LLM_LABELS"
echo "   Weights:  $DISTILL_OUT/"
echo
echo "   Deploy: copy $DISTILL_OUT/ -> <private-weights-repo>/v3_${OUT}"
echo "           then set WEIGHTS_PATH=/weights/v3_${OUT}"
