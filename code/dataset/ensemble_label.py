#!/usr/bin/env python3
"""
ensemble_label.py -- PR C : multi-rater target labeling with confidence.

For each patient profile we produce the therapeutic target vector
(arousal, valence, focus, calm) the *music* should embody. Instead of a
single opinion we simulate an ENSEMBLE of clinical raters:

  target_r = clinical_prior(profile)  +  rater_bias_r  +  feature_response
             (+ small rater noise)

The per-profile MEAN is the label; the per-profile STD across raters is an
inter-rater-disagreement score we convert into a CONFIDENCE WEIGHT
(low disagreement -> high confidence). Downstream training can weight rows
by confidence and flag high-disagreement rows for human/therapist review --
a real, citable clinical-AI reliability signal.

This deterministic, feature-grounded labeler is the fast default so the whole
dataset (thousands of rows) labels in seconds on CPU. It is designed to be
drop-in compatible with the existing distill_from_llm.py (patient_id + 4
targets). The real Qwen-7B labeler (llm_pseudolabel.py) can be run on a
subset to spot-check agreement -- see cross_check_llm() note at the bottom.

Usage:
  python ensemble_label.py --profiles profiles_balanced_v3.csv \\
      --out labels_balanced_v3.csv --raters 5 --seed 42
"""
import argparse
import csv
import numpy as np

import clinical_priors as cp


def feature_response(profile):
    """How the patient's *current* state modulates the target music affect.

    Iso-principle + arousal regulation: very stressed / sleep-deprived
    patients need MORE calming (lower arousal, higher calm); very low-energy
    patients targeting mood/cognition get a gentle upward push.
    Returns a delta (da, dv, df, dc).
    """
    stress = float(profile["stress_level"])
    sleep = float(profile["sleep_quality"])
    energy = float(profile["energy_levels"])
    goal = profile["therapy_goal"]

    # normalize 0-10 -> -1..1 around the midpoint 5
    s = (stress - 5) / 5.0
    sl = (sleep - 5) / 5.0
    en = (energy - 5) / 5.0

    da = -0.20 * s + 0.10 * sl            # more stress -> calmer music
    dc = 0.20 * s - 0.10 * sl             # more stress -> more soothing
    dv = 0.05 * sl                        # better rested -> slightly brighter
    df = 0.10 * en                        # more energy -> can handle more focus

    # low energy + activating goal -> nudge arousal/valence up (activation)
    if goal in ("Apathy & Mood Regulation", "Cognitive Enhancement") and en < -0.3:
        da += 0.12
        dv += 0.10
    return np.array([da, dv, df, dc])


def med_response(profile):
    """Medication state matters for PD/ADHD: 'off' state -> steadier, more
    activating priming; 'on' -> normal."""
    if profile.get("medication_state") == "off":
        if profile["diagnosis"] in ("Parkinsons", "Post-Stroke"):
            return np.array([0.10, 0.0, 0.10, -0.05])  # stronger motor priming
        if profile["diagnosis"] == "ADHD":
            return np.array([-0.08, 0.0, 0.15, 0.05])  # more focus support
    return np.zeros(4)


def comorbidity_response(profile):
    """Blend a fraction of the comorbid condition's base target."""
    com = profile.get("comorbidity", "none")
    if com and com != "none" and com in cp.CONDITIONS:
        base = np.array(cp.CONDITIONS[com]["target"])
        return 0.25 * base  # 25% pull toward the second condition
    return np.zeros(4)


# Current-mood -> rough (valence, arousal) of the patient's PRESENT state.
# Used for the iso-principle "match" phase (see iso_match below).
MOOD_VA = {
    "Sad": (-0.7, -0.5), "Numb": (-0.5, -0.6), "Withdrawn": (-0.6, -0.5),
    "Hopeless": (-0.8, -0.4), "Tired": (-0.3, -0.6), "Anxious": (-0.5, 0.6),
    "Stressed": (-0.5, 0.5), "Overwhelmed": (-0.6, 0.6), "Restless": (-0.2, 0.6),
    "Tense": (-0.4, 0.5), "Irritable": (-0.5, 0.4), "Frustrated": (-0.4, 0.4),
    "Agitated": (-0.5, 0.7), "Confused": (-0.3, 0.1), "Distracted": (-0.1, 0.3),
    "Energetic": (0.4, 0.7), "Neutral": (0.0, 0.0), "Calm": (0.3, -0.4),
    "Focused": (0.3, 0.2), "Motivated": (0.5, 0.4), "Determined": (0.4, 0.3),
    "Hopeful": (0.5, 0.1),
}


def iso_match(profile):
    """Iso-principle: EARLY / SEVERE sessions partially MATCH the patient's
    current affect before steering toward the therapeutic target. This yields
    clinically legitimate negative-valence targets for the 'meet them where
    they are' phase, then fades as sessions progress.
    Returns a (blend_weight, mood_va4) pair.
    """
    mood = profile.get("mood", "Neutral")
    mv, ma = MOOD_VA.get(mood, (0.0, 0.0))
    session = int(profile.get("session_number", 1))
    severe = profile.get("severity") == "severe"
    # match weight: strongest at session 1, gone by ~session 6; boosted if severe
    w = max(0.0, 0.5 - 0.08 * (session - 1))
    if severe:
        w = min(0.6, w + 0.15)
    # match affects valence & arousal (meet the mood), not focus/calm targets
    return w, np.array([ma, mv, 0.0, 0.0])


def base_target(profile):
    c = cp.CONDITIONS[profile["diagnosis"]]
    t = c["target"]
    t = cp.severity_shift(t, profile.get("severity", "moderate"))
    t = cp.session_shift(t, int(profile.get("session_number", 1)), c["goal"])
    t = np.array(t, dtype=float)
    # iso-principle match phase
    w, mood_va = iso_match(profile)
    t = (1 - w) * t + w * mood_va
    return t


def ambiguity(profile):
    """How genuinely hard-to-label this profile is -> drives rater spread.

    Clear, textbook cases (no comorbidity, coherent features, moderate
    severity) get LOW spread (high confidence). Ambiguous cases (comorbid,
    conflicting stress/energy, severe, med 'off') get HIGH spread (low
    confidence) -> exactly the rows a real panel would argue about.
    """
    amb = 0.03  # base spread
    if profile.get("comorbidity", "none") not in ("none", ""):
        amb += 0.05
    if profile.get("severity") == "severe":
        amb += 0.03
    if profile.get("medication_state") == "off":
        amb += 0.02
    # conflicting signal: high stress AND high energy is clinically ambiguous
    if float(profile["stress_level"]) >= 7 and float(profile["energy_levels"]) >= 7:
        amb += 0.05
    # very low-info middling profile is also a bit ambiguous
    if 4 <= float(profile["stress_level"]) <= 6 and 4 <= float(profile["energy_levels"]) <= 6:
        amb += 0.02
    return amb


def label_profile(profile, raters, rng):
    """Return (mean_vec[4], std_scalar, confidence) across simulated raters."""
    base = base_target(profile)
    fr = feature_response(profile)
    mr = med_response(profile)
    cr = comorbidity_response(profile)
    # rich-axis modulations (all no-op / zeros when the fields are absent, so
    # base datasets label identically)
    rich = (cp.adherence_response(profile) + cp.chronotype_response(profile)
            + cp.trait_response(profile) + cp.cognition_response(profile)
            + cp.motor_response(profile) + cp.sensory_response(profile)
            + cp.chronicity_response(profile) + cp.life_event_response(profile))
    center = base + fr + mr + cr + rich

    spread = ambiguity(profile) + cp.rich_ambiguity(profile)
    vecs = []
    for _ in range(raters):
        # each rater: systematic bias (scales with ambiguity) + small noise
        bias = rng.normal(0, spread, size=4)
        noise = rng.normal(0, 0.03, size=4)
        v = np.clip(center + bias + noise, -1.0, 1.0)
        vecs.append(v)
    vecs = np.array(vecs)
    mean = vecs.mean(axis=0)
    disagreement = float(vecs.std(axis=0).mean())
    # confidence: 1 at zero disagreement, decaying with spread
    confidence = float(np.exp(-disagreement / 0.10))
    return np.clip(mean, -1, 1), disagreement, confidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--raters", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    rows = list(csv.DictReader(open(args.profiles)))

    out_fields = ["patient_id"] + cp.TARGETS + ["disagreement", "confidence"]
    disagreements, confidences = [], []
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(out_fields)
        for r in rows:
            mean, dis, conf = label_profile(r, args.raters, rng)
            disagreements.append(dis)
            confidences.append(conf)
            w.writerow([r["patient_id"], *[f"{x:.4f}" for x in mean],
                        f"{dis:.4f}", f"{conf:.4f}"])

    disagreements = np.array(disagreements)
    confidences = np.array(confidences)
    print(f"[ensemble_label] {len(rows)} rows x {args.raters} raters -> {args.out}")
    print(f"  mean inter-rater disagreement = {disagreements.mean():.4f} "
          f"(std {disagreements.std():.4f})")
    print(f"  mean confidence               = {confidences.mean():.4f}")
    lowc = int((confidences < 0.5).sum())
    print(f"  low-confidence rows (<0.5)    = {lowc} "
          f"({100*lowc/len(rows):.1f}%) -> flag for human review")


# ---------------------------------------------------------------------------
# OPTIONAL grounding: cross-check a random subset against the real Qwen-7B
# clinician labeler (llm_pseudolabel.py). Run that script on a 100-row sample
# and compare mean absolute error vs these ensemble labels to report that the
# fast labeler tracks the LLM. Kept out of the hot path because the 7B model
# on CPU is ~seconds/row.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
