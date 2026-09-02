# dataset — enriched training data + RLHF reward model

Enriches the NeuroTunes synthetic dataset from **4 conditions / 800 rows** to
**14 conditions / 7,200 rows**, adds ensemble labels with confidence, dual
(balanced + natural-prevalence) datasets, an EmotionNet training/generalization
proof, and an RLHF reward model trained from preferences.

## Pipeline (run in order)
```bash
source /home/ubuntu/m2e_env/bin/activate   # torch(cpu), sklearn, pandas
cd code/dataset

python gen_profiles.py          # PR A+B: 14 conditions + severity/comorbidity/time/med
python ensemble_label.py        # PR C : multi-rater mean + disagreement + confidence
python make_datasets.py         # PR D : balanced + natural sets, distill files, M2E hook
python coverage_report.py       # QA   -> coverage_report.txt
python train_emotionnet_v3.py   # proof: R^2 on held-out natural set
python rewardnet.py             # RLHF : reward model from simulated prefs (+ real hook)
```

## Files
| file | role |
|---|---|
| `clinical_priors.py` | single source of truth: 14 conditions + axes + helpers |
| `gen_profiles.py` | PR A/B — profile generation |
| `ensemble_label.py` | PR C — ensemble labeling + confidence + iso-principle |
| `make_datasets.py` | PR D — dataset assembly + Music2Emo grounding hook |
| `coverage_report.py` | QA representativeness report |
| `train_emotionnet_v3.py` | EmotionNet generalization proof (R²) |
| `rewardnet.py` | RLHF reward model + `real_feedback.csv` hook |
| `*_v3.csv` | generated datasets (balanced + natural + distill-compatible) |
| `*_results.txt`, `coverage_report.txt` | captured run outputs |

## Key results (see `../../../NeuroTunes_Dataset_v3_QA_and_RLHF` report)
- 14/14 conditions; 7,200 sessions; arousal axis balanced ~49/51.
- EmotionNet R² **0.968** on the never-seen natural-prevalence set.
- RewardNet preference ranking accuracy **0.84** (test).

## Scaling to 200K–1M (trajectory mode)
The default pipeline makes a 7.2K snapshot set. To scale **without duplicating
rows**, use **trajectory mode**: each patient becomes a longitudinal *course of
care* (3–25 sessions) whose state drifts session-to-session (stress eases, sleep
improves, mood climbs, with setbacks + noise). Every row is a distinct
`(patient, session)` and carries within-patient temporal signal.

```bash
source /home/ubuntu/m2e_env/bin/activate
cd code/dataset

bash scale_pipeline.sh                        # ~205K balanced + ~85K eval (~2.5 min)
bash scale_pipeline.sh 72000 24000 scaled_1m  # ~1.0M balanced (~12–15 min)
```
`scale_pipeline.sh` takes **3 optional args**: `patients_balanced`,
`patients_natural`, `out_dir`. So `72000 24000 scaled_1m` = 72k balanced
patients (~1.0M sessions) + 24k eval patients, written to `scaled_1m/`.
Outputs land in that dir (gitignored — reproducible from the script, so the repo
stays lean).

### Rich patient realism (`--rich`, on by default in `scale_pipeline.sh`)
Scaling now generates **distinct, clinically-textured people**, not resampled
draws from one distribution. Each patient carries:
- a **responder archetype** (rapid / gradual / non-responder / relapsing-remitting)
  that shapes their whole course — recovery, plateau, relapse, or early dropout;
- **comorbidity co-occurrence** drawn from a clinical matrix (e.g. Anxiety+Depression,
  PTSD+Insomnia), including multimorbid patients, plus a `comorbidity_count`;
- **medication adherence** (adherent / partial / non-adherent) that scales
  responsiveness and how often they present in an `off`-med state;
- **chronotype** interacting with session `time_of_day` (off-peak sessions perform worse);
- **illness duration / chronicity**, **baseline cognition**, **motor function**,
  **sensory sensitivity**, **trait anxiety**, **social support**, **music engagement**;
- **acute life events** per session (temporary setbacks) and **engagement-driven
  attrition** (disengaged patients drop out earlier → realistic session counts).

All of these **feed the labels** (via `clinical_priors.py` response functions),
so they carry real signal instead of being noise columns, and the trainers
**auto-detect** the extra columns. Single-mode (the committed 7.2K) is untouched
and still reproduces byte-identically.

Verified on a rich set: **0.00% duplicate feature-rows**, EmotionNet held-out
**R² ≈ 0.92**, RewardNet test accuracy **≈ 0.86**. (R² is a bit below the 0.968
of the simpler set *by design* — richer patients are a genuinely harder, more
realistic mapping with more variance to explain, not a regression.)

### Trained model weights (new)
The trainers now **save the model, its preprocessor and metadata** into the
output dir, so you get usable artifacts — not just metrics:
- `emotionnet_v3.pt` + `emotionnet_v3_preprocess.joblib` + `emotionnet_v3_meta.json`
- `rewardnet_v3.pt` + `rewardnet_v3_preprocess.joblib` + `rewardnet_v3_meta.json`

Load one:
```python
import torch, joblib, json
from train_emotionnet_v3 import EmotionNet
meta = json.load(open("scaled/emotionnet_v3_meta.json"))
pre  = joblib.load("scaled/emotionnet_v3_preprocess.joblib")   # sklearn ColumnTransformer
net  = EmotionNet(meta["input_dim"]); net.load_state_dict(torch.load("scaled/emotionnet_v3.pt")); net.eval()
# X = pre.transform(profiles_df); net(torch.tensor(X.astype('float32')))
```
Weights are gitignored (reproducible). Pass `--no-save` to skip saving.

Do **not** rerun `training/setup_distill.sh` to scale — that is the separate
Qwen-7B LLM-distillation + Music2Emo track (CPU-prohibitive). The fast ensemble
labeler here is what scales. See `../../../NeuroTunes_Dataset_v3_Scaling` note.

## To enable real RLHF
Export the platform's listener/therapist feedback as `real_feedback.csv`
(profile columns + `pref_*` / `rej_*` affect columns) into this folder and
re-run `python rewardnet.py` — the same code fine-tunes on real preferences.

> Labels are literature-informed heuristics and preferences are simulated until
> real feedback is supplied. Not a clinical-validation claim (no IRB/outcomes).
