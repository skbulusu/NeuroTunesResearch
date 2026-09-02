#!/usr/bin/env python3
"""Verify freshly built weights load EXACTLY like production and behave sanely.

Loads via the real NeuroTunesModel class with WEIGHTS_PATH pointing first at the
in-repo v1 `models/` dir, then at the freshly built weights dir (--new, default
out_v3/), and compares the predicted state vectors + resulting clinical music
params for identical patients.
"""
import argparse
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)
sys.path.insert(0, _MLSERVER)

PATIENTS = [
    dict(age=24, gender="Female", diagnosis="Anxiety", therapy_goal="Relaxation",
         stress_level=8, sleep_quality=3, energy_levels=3, mood="Stressed"),
    dict(age=67, gender="Male", diagnosis="Post-Stroke", therapy_goal="Gait & Motor Priming",
         stress_level=4, sleep_quality=6, energy_levels=5, mood="Determined"),
    dict(age=35, gender="Other", diagnosis="Depression", therapy_goal="Apathy & Mood Regulation",
         stress_level=6, sleep_quality=4, energy_levels=2, mood="Numb"),
    dict(age=29, gender="Female", diagnosis="Healthy", therapy_goal="Cognitive Enhancement",
         stress_level=3, sleep_quality=7, energy_levels=7, mood="Focused"),
]


def load(weights_dir):
    os.environ["WEIGHTS_PATH"] = weights_dir
    # force a fresh import each time so MODEL_DIR re-reads the env var
    for m in list(sys.modules):
        if m == "neurotunes_model":
            del sys.modules[m]
    import neurotunes_model  # noqa
    return neurotunes_model.NeuroTunesModel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default=os.path.join(_HERE, "out_v3"),
                    help="freshly built weights dir to verify (default out_v3/ from "
                         "distill_from_llm.py; use out_v2/ for build_emotion_net_v2.py).")
    args = ap.parse_args()

    v1_dir = os.path.join(_MLSERVER, "models")
    new_dir = args.new
    tag = os.path.basename(new_dir.rstrip("/")) or "new"

    print("=== Loading v1 (current production models/) ===")
    m1 = load(v1_dir)
    print(f"=== Loading NEW ({tag}/) — must unpickle as neurotunes_model.EmotionNet ===")
    m2 = load(new_dir)

    print("\n=== state vector [arousal, valence, focus, calm] + music params ===")
    for p in PATIENTS:
        s1 = np.round(m1.predict(None, original_patient_data=p), 3)
        s2 = np.round(m2.predict(None, original_patient_data=p), 3)
        c1 = m1.map_to_clinical_params(s1, p["therapy_goal"])
        c2 = m2.map_to_clinical_params(s2, p["therapy_goal"])
        print(f"\nPatient: {p['diagnosis']}/{p['therapy_goal']} stress={p['stress_level']} "
              f"sleep={p['sleep_quality']} energy={p['energy_levels']} mood={p['mood']}")
        print(f"  v1  state={s1}  -> tempo={round(c1['tempo'],1)} mode={c1['mode']} "
              f"complexity={round(c1['complexity'],2)}")
        print(f"  NEW state={s2}  -> tempo={round(c2['tempo'],1)} mode={c2['mode']} "
              f"complexity={round(c2['complexity'],2)}")

    print("\nBoth loaded via WEIGHTS_PATH the production way (torch.load weights_only=False).")


if __name__ == "__main__":
    main()
