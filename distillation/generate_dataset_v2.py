"""
generate_dataset_v2.py  —  NeuroTunes improved synthetic data generator.

Why this exists
---------------
The original generator produced targets that were near-perfect linear functions
of a single input each (e.g. valence = (mood-5)/5, so corr(mood,valence)=1.00).
A model trained on that is just re-deriving the label formula; it proves nothing
and a reviewer will reject it.

This version fixes the DATA STORY so a learned model can genuinely beat a linear
baseline, and so distillation has something real to denoise:

  1. NON-LINEAR, MULTI-FEATURE targets   -> saturating (tanh) responses and
     cross-feature INTERACTIONS (e.g. stress x energy, age x diagnosis).
  2. A REAL session_number effect         -> a saturating habituation/therapy
     response curve, so "adapts over time" has signal behind it.
  3. IRREDUCIBLE NOISE (heteroscedastic)  -> caps the best achievable R^2 at
     ~0.7-0.8, mimicking real self-report variance. This is what makes an
     ensemble teacher (which averages out variance) worth distilling from.

Outputs (compatible column names with the original pipeline):
  data/synthetic_patient_data_v2.csv  (raw features + latent targets + noisy targets)
  synthetic_features_v2.csv           (model inputs)
  synthetic_targets_v2.csv            (noisy observed targets: arousal,valence,focus,energy_state)
  synthetic_targets_clean_v2.csv      (noise-free latent targets = the Bayes-optimal signal)

Run:  python generate_dataset_v2.py --n 4000 --seed 42
"""
import argparse
import os
import numpy as np
import pandas as pd

PERSONAS = {
    "The Overwhelmed Student": {
        "therapy_goal": "Relaxation", "diagnosis": "Anxiety", "age_range": (18, 25),
        "stress_range": (7, 10), "sleep_range": (2, 5), "energy_range": (3, 6),
        "mood_options": ["Stressed", "Anxious", "Overwhelmed", "Tired"],
    },
    "The Stroke Survivor": {
        "therapy_goal": "Gait & Motor Priming", "diagnosis": "Post-Stroke", "age_range": (55, 80),
        "stress_range": (4, 8), "sleep_range": (4, 7), "energy_range": (2, 5),
        "mood_options": ["Frustrated", "Hopeful", "Tired", "Determined"],
    },
    "The Withdrawn Veteran": {
        "therapy_goal": "Apathy & Mood Regulation", "diagnosis": "Depression", "age_range": (30, 60),
        "stress_range": (6, 9), "sleep_range": (3, 6), "energy_range": (1, 4),
        "mood_options": ["Numb", "Withdrawn", "Irritable", "Sad"],
    },
    "The Healthy but Stressed Professional": {
        "therapy_goal": "Cognitive Enhancement", "diagnosis": "Healthy", "age_range": (28, 50),
        "stress_range": (5, 8), "sleep_range": (5, 8), "energy_range": (5, 9),
        "mood_options": ["Focused", "Stressed", "Neutral", "Motivated"],
    },
}

# Mood -> latent pleasantness on a -1..+1 scale (many moods map to nearby values,
# so mood alone can NOT reconstruct valence; sleep/energy/diagnosis also matter).
MOOD_VALENCE = {
    "Stressed": -0.5, "Anxious": -0.6, "Overwhelmed": -0.7, "Tired": -0.3,
    "Frustrated": -0.4, "Hopeful": 0.6, "Determined": 0.7, "Numb": -0.5,
    "Withdrawn": -0.6, "Irritable": -0.4, "Sad": -0.7, "Focused": 0.5,
    "Neutral": 0.0, "Motivated": 0.8,
}
# Diagnosis modifiers (small, non-trivial nudges across several targets).
DIAG_MOD = {
    "Anxiety":     {"arousal": +0.15, "focus": -0.10},
    "Post-Stroke": {"focus": -0.15, "energy_state": -0.10},
    "Depression":  {"valence": -0.15, "energy_state": -0.15},
    "Healthy":     {"focus": +0.10},
}


def _norm(x, lo, hi):
    """Scale a raw value in [lo,hi] to roughly [-1,1]."""
    return 2 * (x - lo) / (hi - lo) - 1


def latent_targets(row):
    """The 'true' physiology: non-linear, interacting, but deterministic (noise added later)."""
    age = _norm(row["age"], 18, 85)
    stress = _norm(row["stress_level"], 1, 10)
    sleep = _norm(row["sleep_quality"], 1, 10)
    energy = _norm(row["energy_levels"], 1, 10)
    mood = MOOD_VALENCE.get(row["mood"], 0.0)
    sess = row["session_number"]

    # Saturating habituation: therapy response grows then plateaus over sessions.
    habit = np.tanh(sess / 12.0)  # 0 -> ~1 across ~30 sessions

    # AROUSAL: saturating stress response, boosted by energy, damped by age;
    # key INTERACTION: high stress AND high energy compound (agitation).
    arousal = (0.8 * np.tanh(1.6 * stress)
               + 0.35 * energy
               - 0.25 * age
               + 0.30 * stress * energy)       # interaction term

    # VALENCE: mood is the biggest driver but NOT the only one; sleep and energy
    # lift it, and the therapy habituation improves it over time.
    valence = (0.6 * mood
               + 0.30 * sleep
               + 0.20 * energy
               + 0.25 * habit)

    # FOCUS: driven by sleep and (inverse) stress with an INTERACTION -
    # poor sleep makes stress hurt focus much more; age slightly helps (experience).
    focus = (0.7 * sleep
             - 0.5 * np.tanh(1.4 * stress)
             - 0.4 * stress * (1 - (sleep + 1) / 2)   # bad-sleep x stress interaction
             + 0.15 * age
             + 0.20 * habit)

    # ENERGY_STATE: energy + sleep + mood, lifted by habituation.
    energy_state = (0.7 * energy
                    + 0.35 * sleep
                    + 0.25 * mood
                    + 0.20 * habit)

    out = {"arousal": arousal, "valence": valence, "focus": focus, "energy_state": energy_state}
    for k, v in DIAG_MOD.get(row["diagnosis"], {}).items():
        out[k] += v
    # squash to a bounded, comparable range
    return {k: float(np.tanh(0.9 * v)) for k, v in out.items()}


def generate(n_total=4000, seed=42):
    rng = np.random.default_rng(seed)
    per = max(1, n_total // len(PERSONAS))
    rows = []
    pid = 1
    for name, p in PERSONAS.items():
        for _ in range(per):
            rows.append({
                "patient_id": f"SYNTH_{pid}",
                "age": int(rng.integers(*p["age_range"])),
                "gender": rng.choice(["Male", "Female", "Other"]),
                "diagnosis": p["diagnosis"],
                "therapy_goal": p["therapy_goal"],
                "stress_level": int(np.clip(rng.integers(*p["stress_range"]) + rng.normal(0, 0.6), 1, 10)),
                "sleep_quality": int(np.clip(rng.integers(*p["sleep_range"]) + rng.normal(0, 0.6), 1, 10)),
                "energy_levels": int(np.clip(rng.integers(*p["energy_range"]) + rng.normal(0, 0.6), 1, 10)),
                "mood": rng.choice(p["mood_options"]),
                "session_number": int(rng.integers(1, 40)),
            })
            pid += 1
    df = pd.DataFrame(rows)

    clean = df.apply(latent_targets, axis=1, result_type="expand")

    # Heteroscedastic irreducible noise: caps best-achievable R^2 well below 1.0.
    # Noise is larger when self-report is less reliable (high stress, poor sleep).
    unreliability = 0.5 + 0.5 * _norm(df["stress_level"].values, 1, 10) \
                    - 0.3 * _norm(df["sleep_quality"].values, 1, 10)
    unreliability = np.clip(unreliability, 0.2, 1.2)
    noisy = clean.copy()
    for col in noisy.columns:
        sigma = 0.28 * unreliability
        noisy[col] = np.clip(clean[col].values + rng.normal(0, sigma), -1, 1)

    feats = df[["age", "gender", "diagnosis", "therapy_goal",
                "stress_level", "sleep_quality", "energy_levels", "mood", "session_number"]]
    return df, feats, noisy, clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.outdir, "data"), exist_ok=True)
    df, feats, noisy, clean = generate(args.n, args.seed)

    full = pd.concat([df, clean.add_prefix("latent_"), noisy.add_prefix("obs_")], axis=1)
    full.to_csv(os.path.join(args.outdir, "data", "synthetic_patient_data_v2.csv"), index=False)
    feats.to_csv(os.path.join(args.outdir, "synthetic_features_v2.csv"), index=False)
    noisy.to_csv(os.path.join(args.outdir, "synthetic_targets_v2.csv"), index=False)
    clean.to_csv(os.path.join(args.outdir, "synthetic_targets_clean_v2.csv"), index=False)

    # Report the correlation structure so the improvement over v1 is visible.
    fe = feats.copy()
    for c in fe.columns:
        if fe[c].dtype == object:
            fe[c] = fe[c].astype("category").cat.codes
    corr = pd.concat([fe, noisy], axis=1).corr(numeric_only=True) \
        .loc[list(feats.columns), list(noisy.columns)]
    print(f"Generated {len(df)} rows (seed={args.seed}).")
    print("\nFeature -> observed-target correlations (should NO LONGER contain 1.00):")
    print(corr.round(2).to_string())
    maxabs = corr.abs().max().max()
    print(f"\nMax |correlation| = {maxabs:.2f}  (v1 was 1.00 -> label leakage; <0.9 is healthy)")


if __name__ == "__main__":
    main()
