#!/usr/bin/env python3
"""
make_first_session_subset.py — collapse the rich v3 *trajectory* dataset into a
patient-level table (exactly ONE row per patient) for production EmotionNet
training.

Why this exists
---------------
`dataset/` generates data in TRAJECTORY mode: each patient has many
session rows (session_number 1..N) so the dataset scales without duplication.
But the production training scripts (llm_pseudolabel.py -> distill_from_llm.py)
label ONE therapeutic target per patient_id. Feeding them multi-session rows
would create several conflicting labels for the same patient.

This script takes the first session (session_number == 1, i.e. the patient's
baseline assessment) of each patient, so the LLM/distill path trains on the SAME
rich v3 population — no separate dataset, no schema surprises. The core columns
the production preprocessor uses (age, gender, diagnosis, therapy_goal,
stress_level, sleep_quality, energy_levels, mood) are all present; the extra rich
columns are carried along harmlessly and simply ignored by the preprocessor.
"""
import argparse
import os
import sys
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)

# The 8 core columns the production preprocessor consumes (+ patient_id key).
CORE = ["patient_id", "age", "gender", "diagnosis", "therapy_goal",
        "stress_level", "sleep_quality", "energy_levels", "mood"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True,
                    help="v3 trajectory profiles CSV (e.g. scaled/profiles_balanced_v3.csv)")
    ap.add_argument("--out",
                    default=os.path.join(_MLSERVER, "data", "patients_v3_first_session.csv"),
                    help="output patient-level CSV (one row per patient)")
    args = ap.parse_args()

    if not os.path.exists(args.profiles):
        sys.exit(f"profiles not found: {args.profiles}")

    df = pd.read_csv(args.profiles)

    missing = [c for c in CORE if c not in df.columns]
    if missing:
        sys.exit(f"profiles missing required columns: {missing}")

    if "session_number" in df.columns:
        # baseline session per patient
        sub = df[df["session_number"] == df.groupby("patient_id")["session_number"].transform("min")]
        sub = sub.drop_duplicates(subset="patient_id", keep="first")
    else:
        # already patient-level
        sub = df.drop_duplicates(subset="patient_id", keep="first")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    sub.to_csv(args.out, index=False)
    print(f"first-session subset: {len(sub)} unique patients "
          f"(from {len(df)} trajectory rows) -> {os.path.relpath(args.out, _MLSERVER)}")


if __name__ == "__main__":
    main()
