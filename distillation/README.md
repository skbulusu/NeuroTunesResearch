# NeuroTunes — Knowledge Distillation Experiment (reproducible)

This reproduces, on CPU, a real improvement to the NeuroTunes affective model
using knowledge distillation, without collecting any new real-world data. It
runs the same way it did in the original test environment (fixed seeds,
pinned dependencies).

```bash
chmod +x run_all.sh
./run_all.sh
```

Runtime is about 5–10 minutes, CPU-only. Outputs land in this folder and in
`results/`.

## What problem this solves

Two things had to be fixed before distillation could mean anything.

First, the original synthetic data had label leakage. In the old generator,
each target was a closed-form function of a single input (e.g.
`valence = (mood-5)/5`, so `corr(mood, valence) = 1.00`). A model trained on
that is just re-deriving a formula — it proves nothing, and a reviewer would
reject it. `generate_dataset_v2.py` fixes this: targets are now non-linear,
multi-feature, with interaction terms, a real session-number (habituation)
effect, and heteroscedastic noise that caps the best achievable R² around
0.7–0.8, roughly what you'd see with real self-report data. Max
feature-to-target correlation drops from 1.00 to about 0.80.

Second, we needed a fair evaluation target. We keep two copies of the
labels: the noisy observed targets (what you'd actually measure) and the
clean latent targets (the true signal). Models are scored by R² against the
clean latent signal — how much of the real effect a model recovers, not how
well it memorizes noise.

## The experiment (what `distill.py` does)

This is transfer distillation: pretrain on a large labeled pool, then
distill into the small model that actually gets deployed. That mirrors the
intended production setup — pretrain on large public affect datasets like
DEAM/PMEmo, then distill into the small NeuroTunes model.

| Model | Trained on | Size |
|---|---|---|
| Teacher (ensemble of 7 wide MLPs) | the full labeled pool — stands in for a data-rich source | 202,972 params |
| Student — hard labels (baseline) | only the few target labels (e.g. 100 rows) | 4,196 params |
| Student — distilled | the same few labels plus the teacher's soft predictions over the whole input pool | 4,196 params |

The ensemble teacher averages out independent noise, so its mean prediction
is a denoised estimate of the true signal. Distillation lets the tiny
deployable student absorb that denoised knowledge across regions of input
space its handful of labels never covered.

## Headline result (12 seeds, 100 labeled rows)

| Model | Params | R² vs true signal |
|---|---|---|
| Teacher ensemble | 202,972 | 0.991 |
| Student — hard labels (baseline) | 4,196 | 0.917 |
| Student — distilled | 4,196 | 0.987 |

Distillation lifts the deployable student from R² 0.917 to 0.987 (+0.070,
+7.6% relative), and it won in all 12/12 seeds. The distilled student
recovers 99.6% of the giant teacher's signal using about 2.1% of its
parameters.

### Gain is largest in the data-scarce regime

`results/label_sweep.txt` (8 seeds each):

| Labeled rows | Distillation gain (relative R²) |
|---|---|
| 50  | +14.4% |
| 100 | +7.6% |
| 200 | +3.7% |
| 400 | +1.7% |
| 800 | +0.8% |

The benefit shrinks smoothly as labels grow, which is what you'd expect from
a real data-efficiency effect rather than a fluke. See
`results/distillation_vs_labels.png`.

### Caveat

Plain self-distillation (teacher and student both trained on the same few
labels) gave no reliable improvement in testing (about +0.2% ± 0.9%, roughly
half the seeds). Distillation only helps here when the teacher genuinely
knows more than the student — i.e. it was trained on more data (transfer).
That's why this is framed as transfer distillation, and why any claim from
these results should be about data efficiency under scarcity, not a free
lunch from distillation alone. The null self-distillation result is included
for the same reason — it backs up that this is a real effect, not a fluke.

## Files

| File | Purpose |
|---|---|
| `generate_dataset_v2.py` | improved synthetic-data generator (fixes label leakage) |
| `distill.py` | teacher / student / distilled training + multi-seed evaluation |
| `run_all.sh` | one command to reproduce everything |
| `requirements.txt` | pinned deps (`scikit-learn==1.7.1` to match deployed `.pkl` preprocessors) |
| `results/` | main chart, label-sweep numbers + chart |

The audio loudness fix (`audio_postprocess.py`) isn't part of this bundle
anymore — it's production code now, living at `mlServer/audio_postprocess.py`
and imported directly by `mlServer/music_generator.py`. Background on it
below.

### Useful flags on `distill.py`

```
--train_n N     number of labeled target rows (data scarcity). 0 = all.
--unlabeled     transfer mode: data-rich teacher + distill over the full pool (the main one).
--seeds K       average over K seeds for a stable estimate.
--teachers K    ensemble size.
--alpha A       (non-transfer mode) blend of soft vs hard targets.
```

## Audio loudness fix (background only)

Unrelated to distillation, and already shipped in production — kept here
only for context. The rendered therapy tracks came out near-silent (RMS
about −57 dBFS, peak about −37 dBFS) because MIDI velocities are low
(20–40/127) and FluidSynth's default gain is 0.2.

`audio_postprocess.py` peak-normalizes rendered WAVs to −1 dBFS, with a
short fade to avoid clicks, using only stdlib `wave` and numpy — no new
dependencies. It now lives at `mlServer/audio_postprocess.py` and is called
by `mlServer/music_generator.py::_normalize_audio`. Verified on all 12
existing tracks: RMS went from −57 dBFS to −21 dBFS, peak to −1 dBFS.

```bash
# standalone: normalize every wav in a folder (writes *_norm.wav, originals untouched)
python mlServer/audio_postprocess.py output/ --target-dbfs -1.0
```
