#!/usr/bin/env bash
# run_all.sh — one command to reproduce the NeuroTunes distillation result on the Dell XPS.
#
# It (1) regenerates the improved synthetic dataset, (2) runs the flagship
# transfer-distillation experiment (data-rich teacher -> data-scarce student),
# and (3) runs the label-scarcity sweep that shows the gain shrinking as labels grow.
#
# Usage:
#   chmod +x run_all.sh
#   ./run_all.sh
#
# Everything is CPU-only and deterministic (fixed seeds). Total runtime ~5-10 min.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [0/3] Python deps (pinned; scikit-learn==1.7.1 matches the deployed .pkl preprocessors)"
python3 -m pip install -q -r requirements.txt

echo "==> [1/3] Generate improved synthetic dataset (fixes the label-leakage in v1)"
python3 generate_dataset_v2.py --n 4000 --seed 42

echo "==> [2/3] Flagship experiment: transfer distillation @ 100 labeled rows, 12 seeds"
# Teacher = ensemble trained on the full labeled pool (stand-in for a data-rich
# source such as public DEAM/PMEmo affect data). Student = small deployable model
# that only sees 100 target labels. --unlabeled distills over the whole input pool.
python3 distill.py --seed 42 --seeds 12 --teachers 7 --epochs 400 --train_n 100 --unlabeled

echo "==> [3/3] Label-scarcity sweep (how the distillation gain depends on #labels)"
: > results/label_sweep.txt
for n in 50 100 200 400 800; do
  echo -n "train_n=$n : " | tee -a results/label_sweep.txt
  python3 distill.py --seed 42 --seeds 8 --teachers 7 --epochs 400 --train_n "$n" --unlabeled \
    2>/dev/null | grep "Distillation gain" | tee -a results/label_sweep.txt
done

echo
echo "Done. See:"
echo "  distill_results.csv          (flagship table: teacher / hard / distilled)"
echo "  distill_results.png          (flagship bar chart, mean +/- std)"
echo "  results/label_sweep.txt      (gain vs number of labels)"
echo "  models_v2/student_*.pth      (saved student weights)"
