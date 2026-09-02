# EmotionNet training & drop-in retraining

This directory holds the scripts that (re)train the **production** `EmotionNet`
used by `mlServer` to map a patient assessment to an affective state vector
`[arousal, valence, focus, calm]`, which then drives music synthesis.

The **weights themselves are NOT stored in this repo.** They live in the
separate private weights repository (not included in this release) and are mounted into the
mlServer container at runtime via the `WEIGHTS_PATH` env var (see
`neurotunes_model.py`). This keeps large binary artifacts and model versioning
out of the application code history and makes rollback a one-line env change.

## Scripts

| Script | Purpose |
| --- | --- |
| `build_emotion_net_v2.py` | Retrain EmotionNet leakage-free and emit drop-in artifacts (`out_v2/`). |
| `verify_dropin.py` | Load v1 and Ver2 through the real `NeuroTunesModel` loader and diff their behaviour on sample patients. Proves Ver2 unpickles and loads the production way. |
| `ab_generate.py` | Dev A/B harness: generate MIDI for the same patients under (A) v1-unwired = current prod, (B) v2-unwired, (C) v2-wired, and analyse mode/tempo/key/in-scale ratio. |

`out_v2/` and `ab_out/` are generated outputs and are git-ignored.

## Why Ver2 exists (the two bugs it fixes)

1. **Leaky / degenerate training target (v1).** The original targets were
   near-deterministic functions of single input features (max feature→target
   correlation ≈ 1.0), and the `focus`/`calm` axes were built from binary
   thresholds that were actively *miscalibrated* — so on a held-out clean
   latent signal the old target scored a **negative** R². Ver2 defines a
   multi-feature, non-linear, interaction-rich clean latent target (max
   feature→latent correlation **0.786**, i.e. no single-feature leakage), adds
   heteroscedastic observation noise, trains a 7-model teacher ensemble on the
   noisy observations, and **distills** it into the production
   `EmotionNet` (29→64→32→4, tanh).

2. **The model was disconnected from synthesis.** In `app.py`, both
   `/generate_music` and `/generate_music_irb` computed `state_vector =
   model.predict(...)` but then built `therapeutic_targets` from request
   fields (`data.get('arousal', 0.5)`, …) that researchers never send — i.e.
   constants for every request. The model output was returned only as
   metadata. **Retraining alone changes nothing** until the model is wired in.
   The wiring change makes `therapeutic_targets` default to the predicted
   `state_vector` (explicit request fields still override).

   > Note: the generator consumes `arousal/valence/focus/energy_state`. It has
   > no `calm` slot, so `energy_state` defaults to the model's **arousal**
   > axis. `calm (≈ -arousal)` is currently unused by the synth. Flagged as a
   > deliberate semantic choice — revisit if the generator grows a calm axis.

## Metrics (held-out 20%, R² vs clean latent)

```
v1 degenerate targets : -0.979
teacher ensemble      : +0.965
student hard labels   : +0.952
student DISTILLED     : +0.974   (DEPLOYED Ver2)
distillation gain     : +0.021
gain over old signal  : +1.952
```

The "clean latent" is a designer-specified synthetic signal (there is no human
affect ground truth in the synthetic patient data); R² is measured against it.

## Reproducing

Preprocessors are pickled with **scikit-learn 1.7.1** — you MUST train in an
environment pinned to that version or the artifacts will not load in
production. torch, pandas, numpy, joblib, pretty_midi, mido are also required.

```bash
python build_emotion_net_v2.py     # writes out_v2/{emotion_net.pth,preprocessor.pkl,columns.pkl,METRICS.txt}
python verify_dropin.py            # loads v1 vs Ver2 via NeuroTunesModel
python ab_generate.py              # writes ab_out/ MIDIs + prints analysis
```

## Deploying Ver2 (weights repo workflow)

The weights repo is versioned by directory:

```
neurotunes-weights/
  v1/   # the current production weights (emotion_net.pth, preprocessor.pkl, columns.pkl, ...)
  v2/   # the new drop-in artifacts from out_v2/
```

To roll Ver2 out, point the mlServer at `v2/`:

```yaml
# docker-compose-ml.yml (mlServer service)
environment:
  - WEIGHTS_PATH=/weights/v2
volumes:
  - ~/projects/<private-weights-repo>:/weights:ro
```

Rollback is instant: set `WEIGHTS_PATH=/weights/v1` and restart the service.
No application code change is involved in a weights swap.
