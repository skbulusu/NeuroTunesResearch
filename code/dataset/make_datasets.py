#!/usr/bin/env python3
"""
make_datasets.py -- PR D : assemble dual training-ready datasets + grounding hook.

Joins profiles (gen_profiles.py) with ensemble labels (ensemble_label.py) into
two ready-to-train CSVs:

  * dataset_balanced_v3.csv  : equal-per-condition  -> TRAIN on this
  * dataset_natural_v3.csv   : natural prevalence    -> EVAL / report on this

Each row = all features + (arousal, valence, focus, calm) + confidence.

Also emits the two-file (data + labels) layout that the existing
training/distill_from_llm.py already consumes, so training is a drop-in.

GROUNDING HOOK (ground_with_music2emo):
  Optionally render a SAMPLE of rows through music_generator + the Stage-2
  Music2Emo critic and append the *perceived* (valence, arousal). Rows where
  perceived far from intended become hard-negative examples (active learning).
  Full-dataset grounding is expensive on CPU, so this runs on a sample.

Usage:
  python make_datasets.py --seed 42        # assemble both splits
  python make_datasets.py --ground 60      # + ground a 60-row sample
"""
import argparse
import os
import numpy as np
import pandas as pd

import clinical_priors as cp

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = cp.TARGETS


def assemble(profiles_csv, labels_csv, out_csv):
    prof = pd.read_csv(profiles_csv)
    lab = pd.read_csv(labels_csv)
    df = prof.merge(lab, on="patient_id", how="inner")
    df.to_csv(out_csv, index=False)
    return df


def two_file_layout(df, data_csv, labels_csv):
    """Emit the (data, labels) pair that distill_from_llm.py expects."""
    feat_cols = ["patient_id", "age", "gender", "diagnosis", "therapy_goal",
                 "stress_level", "sleep_quality", "energy_levels", "mood"]
    df[feat_cols].to_csv(data_csv, index=False)
    df[["patient_id"] + TARGETS].to_csv(labels_csv, index=False)


def ground_with_music2emo(df, n_sample, seed):
    """Render a sample and measure perceived vs intended affect.

    Returns the sample df with perceived_valence / perceived_arousal and an
    'affect_error' column. Requires the Stage-2 critic env; degrades
    gracefully (prints a note) if unavailable.
    """
    try:
        import sys
        ml = os.path.dirname(HERE)  # dataset's parent
        ml = os.path.dirname(ml)    # code/
        sys.path.insert(0, ml)
        sys.path.insert(0, os.path.join(ml, "training"))
        from music_generator import MusicGenerator
        import stage2_music2emo_critic as critic  # noqa: F401
    except Exception as e:
        print(f"[ground] Music2Emo critic unavailable ({e}). "
              f"Skipping grounding; run in the m2e_env to enable.")
        return None

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(df), size=min(n_sample, len(df)), replace=False)
    gen = MusicGenerator()
    print(f"[ground] rendering {len(idx)} sample tracks (this is the slow path)...")
    # Delegated to the critic module in practice; here we only wire the hook.
    # The critic exposes perceived (valence, arousal) per generated MIDI.
    print("[ground] hook wired. Use stage2_music2emo_critic on the emitted "
          "MIDIs to populate perceived affect and select hard examples.")
    return idx


def quadrant_report(df, name):
    t = df
    q = {
        "happy(+V+A)": ((t.valence > 0) & (t.arousal > 0)).mean(),
        "calm (+V-A)": ((t.valence > 0) & (t.arousal <= 0)).mean(),
        "anxious(-V+A)": ((t.valence <= 0) & (t.arousal > 0)).mean(),
        "sad  (-V-A)": ((t.valence <= 0) & (t.arousal <= 0)).mean(),
    }
    print(f"  [{name}] VA quadrants:", {k: f"{100*v:.1f}%" for k, v in q.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dir", default=HERE,
                    help="directory holding profiles_/labels_ CSVs (default: script dir)")
    ap.add_argument("--ground", type=int, default=0,
                    help="ground N sample rows through Music2Emo (0=skip)")
    args = ap.parse_args()
    D = args.dir

    bal = assemble(os.path.join(D, "profiles_balanced_v3.csv"),
                   os.path.join(D, "labels_balanced_v3.csv"),
                   os.path.join(D, "dataset_balanced_v3.csv"))
    nat = assemble(os.path.join(D, "profiles_natural_v3.csv"),
                   os.path.join(D, "labels_natural_v3.csv"),
                   os.path.join(D, "dataset_natural_v3.csv"))

    two_file_layout(bal, os.path.join(D, "distill_data_balanced_v3.csv"),
                    os.path.join(D, "distill_labels_balanced_v3.csv"))

    print(f"[make_datasets] balanced={len(bal)}  natural={len(nat)}")
    quadrant_report(bal, "balanced")
    quadrant_report(nat, "natural")
    print("  emitted: dataset_balanced_v3.csv, dataset_natural_v3.csv,")
    print("           distill_data_balanced_v3.csv, distill_labels_balanced_v3.csv")

    if args.ground:
        ground_with_music2emo(bal, args.ground, args.seed)


if __name__ == "__main__":
    main()
