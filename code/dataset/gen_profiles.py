#!/usr/bin/env python3
"""
gen_profiles.py -- PR A + PR B (+ scaling) : rich, diverse patient-profile generator.

PR A: expand from 4 conditions to ALL 14 conditions the platform targets.
PR B: add first-class clinical axes (severity, comorbidity, time_of_day,
      medication_state) and balance the valence/arousal plane.

SCALING (new): two generation modes ---------------------------------------
  * single      : one snapshot row per synthetic patient (the original v3 mode).
  * trajectory  : each patient is a *course of care* of several sessions, whose
                  state DRIFTS session-to-session (stress eases, sleep improves,
                  mood lifts, with setbacks + noise). This is how we scale to
                  200K-1M rows WITHOUT duplicating: every row is a distinct
                  (patient, session) with within-patient temporal structure --
                  genuinely new signal, not copies of the same distribution.

Produces TWO profile sets (PR D uses both):
  * balanced          : ~equal N per condition  -> best for TRAINING
  * natural           : mirrors rough real prevalence -> best for HONEST EVAL

Reproducible (fixed seed). Feature priors live in clinical_priors.py.

Usage:
  # original small snapshot set (default, reproduces the committed v3 CSVs):
  python gen_profiles.py --n_balanced 4200 --n_natural 3000

  # scaled longitudinal set (~200K): 14 conditions x ~1050 patients x ~14 sessions
  python gen_profiles.py --mode trajectory --patients_balanced 14700 \\
      --patients_natural 6000 --out scaled

  # ~1M: bump patients ~5x (e.g. 72000 balanced / 24000 natural)
"""
import argparse
import csv
import os
import numpy as np

import clinical_priors as cp

FEATURE_FIELDS = [
    "patient_id", "age", "gender", "diagnosis", "therapy_goal",
    "stress_level", "sleep_quality", "energy_levels", "mood",
    "session_number", "severity", "comorbidity", "time_of_day",
    "medication_state",
]

# extra per-patient / per-session columns emitted only in --rich mode
RICH_FIELDS = [
    "archetype", "illness_duration_years", "medication_adherence",
    "comorbidity_count", "chronotype", "social_support",
    "baseline_cognition", "motor_function", "sensory_sensitivity",
    "trait_anxiety", "music_engagement", "life_event",
]


def _tri(rng, lo, hi, mode):
    return int(round(rng.triangular(lo, mode, hi)))


def _score(rng, mean, sd):
    return int(np.clip(round(rng.normal(mean, sd)), 0, 10))


def _clip10(x):
    return int(np.clip(round(x), 0, 10))


# --------------------------------------------------------------------------
# SINGLE-SNAPSHOT MODE  (original v3 behaviour -- kept identical / reproducible)
# --------------------------------------------------------------------------
def sample_profile(rng, cond_name, pid):
    """Sample one realistic profile for a given condition (single snapshot)."""
    c = cp.CONDITIONS[cond_name]
    age = _tri(rng, *c["age"])
    gender = rng.choice(cp.GENDERS, p=[0.48, 0.48, 0.04])
    stress = _score(rng, *c["stress"])
    sleep = _score(rng, *c["sleep"])
    energy = _score(rng, *c["energy"])
    mood = rng.choice(c["moods"])
    session = int(rng.integers(1, 21))
    severity = rng.choice(cp.SEVERITIES, p=[0.35, 0.45, 0.20])
    time_of_day = rng.choice(cp.TIMES_OF_DAY)
    med_state = (rng.choice(cp.MED_STATES, p=[0.20, 0.60, 0.20])
                 if c["med_relevant"] else "none")

    comorbidity = "none"
    if rng.random() < 0.22:
        others = [k for k in cp.CONDITIONS if k != cond_name and k != "Healthy"]
        comorbidity = rng.choice(others)

    return {
        "patient_id": pid,
        "age": age, "gender": gender, "diagnosis": cond_name,
        "therapy_goal": c["goal"], "stress_level": stress,
        "sleep_quality": sleep, "energy_levels": energy, "mood": mood,
        "session_number": session, "severity": severity,
        "comorbidity": comorbidity, "time_of_day": time_of_day,
        "medication_state": med_state,
    }


# --------------------------------------------------------------------------
# TRAJECTORY MODE  (longitudinal course of care -> scale + real temporal signal)
# --------------------------------------------------------------------------
# moods roughly ordered worse -> better; therapy drifts the index upward.
MOOD_LADDER_BY_GOAL = {
    "Relaxation": ["Overwhelmed", "Stressed", "Tense", "Anxious", "Irritable",
                   "Neutral", "Calm", "Hopeful"],
    "Apathy & Mood Regulation": ["Hopeless", "Numb", "Withdrawn", "Sad", "Tired",
                                 "Neutral", "Hopeful", "Motivated"],
    "Cognitive Enhancement": ["Distracted", "Confused", "Tired", "Neutral",
                              "Focused", "Motivated", "Determined"],
    "Gait & Motor Priming": ["Tired", "Frustrated", "Neutral", "Determined",
                             "Motivated", "Energetic"],
}
_DEFAULT_LADDER = ["Overwhelmed", "Stressed", "Anxious", "Neutral", "Calm",
                   "Hopeful", "Motivated"]


def _ladder_for(goal, cond_moods):
    lad = MOOD_LADDER_BY_GOAL.get(goal, _DEFAULT_LADDER)
    # keep only moods the model/MOOD maps know about; fall back to condition moods
    return lad if lad else list(cond_moods)


def sample_patient_static(rng, cond_name, pid):
    """Fixed attributes for a patient across their whole course of care."""
    c = cp.CONDITIONS[cond_name]
    age = _tri(rng, *c["age"])
    gender = rng.choice(cp.GENDERS, p=[0.48, 0.48, 0.04])
    severity = rng.choice(cp.SEVERITIES, p=[0.35, 0.45, 0.20])
    comorbidity = "none"
    if rng.random() < 0.22:
        others = [k for k in cp.CONDITIONS if k != cond_name and k != "Healthy"]
        comorbidity = rng.choice(others)
    return dict(pid=pid, cond=cond_name, goal=c["goal"], age=age, gender=gender,
                severity=severity, comorbidity=comorbidity,
                med_relevant=c["med_relevant"], c=c)


def sample_trajectory(rng, st, sessions_min=3, sessions_max=25):
    """Generate a longitudinal list of session rows for one patient.

    State drifts across the course of care: stress eases, sleep improves,
    energy normalises, mood climbs its ladder -- each with noise and the
    occasional setback, so no two sessions (or patients) are identical.
    """
    c = st["c"]
    k = int(rng.integers(sessions_min, sessions_max + 1))
    # baseline state at intake (session 1)
    stress = _score(rng, *c["stress"])
    sleep = _score(rng, *c["sleep"])
    energy = _score(rng, *c["energy"])
    ladder = _ladder_for(st["goal"], c["moods"])
    # where on the mood ladder this patient starts (worse if severe)
    sev_off = {"mild": 1, "moderate": 0, "severe": -1}[st["severity"]]
    mpos = int(np.clip(rng.integers(0, max(1, len(ladder) // 2)) + (1 - sev_off),
                       0, len(ladder) - 1))

    # per-patient responsiveness to therapy (how fast they improve)
    resp = rng.uniform(0.15, 0.55)
    rows = []
    for s in range(1, k + 1):
        # therapeutic drift toward healthier values + noise + rare setback
        setback = rng.random() < 0.12
        step = -resp if not setback else resp * 0.8
        stress = _clip10(stress + step + rng.normal(0, 0.9))
        sleep = _clip10(sleep - step * 0.8 + rng.normal(0, 0.9))
        energy = _clip10(energy + (0.0 if st["goal"] == "Relaxation" else -step * 0.6)
                         + rng.normal(0, 0.9))
        # mood climbs the ladder with progress, occasionally slips
        if not setback and rng.random() < 0.45:
            mpos = min(len(ladder) - 1, mpos + 1)
        elif setback and rng.random() < 0.5:
            mpos = max(0, mpos - 1)
        mood = ladder[mpos]

        time_of_day = rng.choice(cp.TIMES_OF_DAY)
        med_state = (rng.choice(cp.MED_STATES, p=[0.15, 0.65, 0.20])
                     if st["med_relevant"] else "none")

        rows.append({
            "patient_id": f"{st['pid']}_s{s:02d}",
            "age": st["age"], "gender": st["gender"], "diagnosis": st["cond"],
            "therapy_goal": st["goal"], "stress_level": stress,
            "sleep_quality": sleep, "energy_levels": energy, "mood": mood,
            "session_number": s, "severity": st["severity"],
            "comorbidity": st["comorbidity"], "time_of_day": time_of_day,
            "medication_state": med_state,
        })
    return rows


# --------------------------------------------------------------------------
# RICH MODE  (distinct, clinically-textured people + archetype-driven courses)
# --------------------------------------------------------------------------
def _tri_f(rng, band):
    lo, hi, mode = band
    return float(rng.triangular(lo, mode, hi))


def _sample_comorbidity(rng, cond_name):
    """Draw comorbidities from the clinical co-occurrence matrix.

    Returns (primary_comorbidity_str, count). ~38% of patients carry at least
    one comorbidity; a smaller subset carry two (complex/multimorbid)."""
    table = cp.COMORBIDITY_MATRIX.get(cond_name, {})
    if not table or rng.random() >= 0.38:
        return "none", 0
    conds = list(table.keys())
    w = np.array([table[c] for c in conds], dtype=float)
    w = w / w.sum()
    first = conds[int(rng.choice(len(conds), p=w))]
    count = 1
    # ~30% of comorbid patients are multimorbid (2 conditions)
    if len(conds) > 1 and rng.random() < 0.30:
        count = 2
    return first, count


def sample_patient_static_rich(rng, cond_name, pid):
    """Fixed, person-defining attributes for a rich patient (whole course)."""
    c = cp.CONDITIONS[cond_name]
    age = _tri(rng, *c["age"])
    gender = rng.choice(cp.GENDERS, p=[0.48, 0.48, 0.04])
    severity = rng.choice(cp.SEVERITIES, p=[0.35, 0.45, 0.20])

    # responder archetype -> shape of the whole trajectory
    arch_names = list(cp.ARCHETYPES.keys())
    arch_p = np.array([cp.ARCHETYPES[a]["p"] for a in arch_names])
    arch_p = arch_p / arch_p.sum()
    archetype = arch_names[int(rng.choice(len(arch_names), p=arch_p))]

    comorbidity, com_count = _sample_comorbidity(rng, cond_name)

    med_relevant = c["med_relevant"]
    adherence = (rng.choice(cp.ADHERENCE_LEVELS, p=cp.ADHERENCE_P)
                 if med_relevant else "n/a")
    chronotype = rng.choice(cp.CHRONOTYPES, p=cp.CHRONOTYPE_P)
    support = rng.choice(cp.SUPPORT_LEVELS, p=cp.SUPPORT_P)

    duration = round(_tri_f(rng, cp.DURATION_YEARS.get(cond_name, cp._DUR_DEFAULT)), 1)
    cognition = _clip10(_tri_f(rng, cp.COGNITION_BAND.get(cond_name, cp._COG_DEFAULT)))
    motor = _clip10(_tri_f(rng, cp.MOTOR_BAND.get(cond_name, cp._MOTOR_DEFAULT)))
    sensory = _clip10(_tri_f(rng, cp.SENSORY_BAND.get(cond_name, cp._SENS_DEFAULT)))
    trait_anx = _clip10(_tri_f(rng, cp.TRAIT_ANX_BAND.get(cond_name, cp._TRAIT_DEFAULT)))
    # engagement: lower for severe / non-responders, higher with support
    eng_base = rng.normal(6.0, 2.0)
    eng_base += {"low": -1.0, "moderate": 0.0, "high": 1.0}[support]
    eng_base += {"rapid_responder": 1.0, "gradual_responder": 0.3,
                 "non_responder": -1.2, "relapsing_remitting": -0.3}[archetype]
    music_engagement = _clip10(eng_base)

    return dict(pid=pid, cond=cond_name, goal=c["goal"], age=age, gender=gender,
                severity=severity, comorbidity=comorbidity, com_count=com_count,
                med_relevant=med_relevant, adherence=adherence,
                chronotype=chronotype, support=support, duration=duration,
                cognition=cognition, motor=motor, sensory=sensory,
                trait_anx=trait_anx, engagement=music_engagement,
                archetype=archetype, c=c)


def sample_trajectory_rich(rng, st, sessions_min=3, sessions_max=25):
    """Longitudinal course of care whose SHAPE is driven by the patient's
    archetype, adherence, support and engagement -- so two patients with the
    same diagnosis can follow very different arcs (recover, plateau, relapse,
    or drop out early)."""
    c = st["c"]
    arch = cp.ARCHETYPES[st["archetype"]]

    # responsiveness modulated by adherence, support and chronicity
    resp = rng.uniform(*arch["resp"])
    if st["adherence"] in cp.ADHERENCE_RESP:
        resp *= cp.ADHERENCE_RESP[st["adherence"]]
    resp *= cp.SUPPORT_RESP[st["support"]]
    if st["duration"] >= 10:          # chronic -> slower change
        resp *= 0.85
    setback_p = arch["setback_p"]
    if st["support"] == "low":
        setback_p += 0.05
    osc = arch["oscillate"]

    # planned course length, then engagement-driven early dropout (attrition)
    k_plan = int(rng.integers(sessions_min, sessions_max + 1))
    dropout_p = arch["dropout_p"] + max(0.0, (5.0 - st["engagement"]) * 0.012)

    ladder = _ladder_for(st["goal"], c["moods"])
    sev_off = {"mild": 1, "moderate": 0, "severe": -1}[st["severity"]]
    mpos = int(np.clip(rng.integers(0, max(1, len(ladder) // 2)) + (1 - sev_off),
                       0, len(ladder) - 1))
    stress = _score(rng, *c["stress"])
    sleep = _score(rng, *c["sleep"])
    energy = _score(rng, *c["energy"])

    rows = []
    for s in range(1, k_plan + 1):
        # improvement flattens after the archetype's plateau point
        plateau = 1.0 if s <= arch["plateau_at"] * k_plan else 0.35
        setback = rng.random() < setback_p
        # acute life stressor this session (rarer with strong support)
        life_event = int(rng.random() < (0.10 if st["support"] != "high" else 0.05))
        eff = -resp * plateau if not setback else resp * 0.8
        if life_event:
            eff += resp * 0.6  # a stressor pushes state the wrong way

        noise = 0.9 * (1.0 + 0.25 * osc)
        stress = _clip10(stress + eff + rng.normal(0, noise))
        sleep = _clip10(sleep - eff * 0.8 + rng.normal(0, noise))
        energy = _clip10(energy + (0.0 if st["goal"] == "Relaxation" else -eff * 0.6)
                         + rng.normal(0, noise))

        improve_p = 0.45 * plateau
        if not setback and not life_event and rng.random() < improve_p:
            mpos = min(len(ladder) - 1, mpos + 1)
        elif (setback or life_event) and rng.random() < 0.5:
            mpos = max(0, mpos - 1)
        mood = ladder[mpos]

        # session time: usually the patient's best time, sometimes not
        if rng.random() < 0.6:
            time_of_day = cp.CHRONO_BEST_TIME[st["chronotype"]]
        else:
            time_of_day = rng.choice(cp.TIMES_OF_DAY)

        if st["med_relevant"]:
            off_p = cp.ADHERENCE_OFF_P.get(st["adherence"], 0.20)
            med_state = "off" if rng.random() < off_p else "on"
        else:
            med_state = "none"

        rows.append({
            "patient_id": f"{st['pid']}_s{s:02d}",
            "age": st["age"], "gender": st["gender"], "diagnosis": st["cond"],
            "therapy_goal": st["goal"], "stress_level": stress,
            "sleep_quality": sleep, "energy_levels": energy, "mood": mood,
            "session_number": s, "severity": st["severity"],
            "comorbidity": st["comorbidity"], "time_of_day": time_of_day,
            "medication_state": med_state,
            # --- rich columns ---
            "archetype": st["archetype"],
            "illness_duration_years": st["duration"],
            "medication_adherence": st["adherence"],
            "comorbidity_count": st["com_count"],
            "chronotype": st["chronotype"], "social_support": st["support"],
            "baseline_cognition": st["cognition"], "motor_function": st["motor"],
            "sensory_sensitivity": st["sensory"], "trait_anxiety": st["trait_anx"],
            "music_engagement": st["engagement"], "life_event": life_event,
        })

        # early dropout: end the course once we have the 3-session minimum
        if s >= sessions_min and rng.random() < dropout_p:
            break
    return rows


# --------------------------------------------------------------------------
# set builders
# --------------------------------------------------------------------------
def gen_balanced(rng, n_total, start_id=100000):
    conds = list(cp.CONDITIONS.keys())
    per = n_total // len(conds)
    rows, pid = [], start_id
    for cond in conds:
        for _ in range(per):
            rows.append(sample_profile(rng, cond, f"v3b_{pid}")); pid += 1
    rng.shuffle(rows)
    return rows


def gen_natural(rng, n_total, start_id=200000):
    conds = list(cp.CONDITIONS.keys())
    w = np.array([cp.CONDITIONS[c]["prevalence"] for c in conds], dtype=float)
    w = w / w.sum()
    rows, pid = [], start_id
    picks = rng.choice(len(conds), size=n_total, p=w)
    for idx in picks:
        rows.append(sample_profile(rng, conds[idx], f"v3n_{pid}")); pid += 1
    return rows


def gen_balanced_traj(rng, n_patients, s_min, s_max, start_id=500000, rich=False):
    conds = list(cp.CONDITIONS.keys())
    per = n_patients // len(conds)
    rows, pid = [], start_id
    static_fn = sample_patient_static_rich if rich else sample_patient_static
    traj_fn = sample_trajectory_rich if rich else sample_trajectory
    for cond in conds:
        for _ in range(per):
            st = static_fn(rng, cond, f"v3B_{pid}"); pid += 1
            rows.extend(traj_fn(rng, st, s_min, s_max))
    rng.shuffle(rows)
    return rows


def gen_natural_traj(rng, n_patients, s_min, s_max, start_id=800000, rich=False):
    conds = list(cp.CONDITIONS.keys())
    w = np.array([cp.CONDITIONS[c]["prevalence"] for c in conds], dtype=float)
    w = w / w.sum()
    picks = rng.choice(len(conds), size=n_patients, p=w)
    rows, pid = [], start_id
    static_fn = sample_patient_static_rich if rich else sample_patient_static
    traj_fn = sample_trajectory_rich if rich else sample_trajectory
    for idx in picks:
        st = static_fn(rng, conds[idx], f"v3N_{pid}"); pid += 1
        rows.extend(traj_fn(rng, st, s_min, s_max))
    return rows


def write_csv(path, rows, fieldnames=FEATURE_FIELDS):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["single", "trajectory"], default="single")
    # single-mode sizes (rows)
    ap.add_argument("--n_balanced", type=int, default=4200)
    ap.add_argument("--n_natural", type=int, default=3000)
    # trajectory-mode sizes (patients -> ~14x rows)
    ap.add_argument("--patients_balanced", type=int, default=14700)
    ap.add_argument("--patients_natural", type=int, default=6000)
    ap.add_argument("--sessions_min", type=int, default=3)
    ap.add_argument("--sessions_max", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=".")
    ap.add_argument("--rich", action="store_true",
                    help="trajectory mode only: add responder archetypes, "
                         "comorbidity co-occurrence, adherence, chronotype, "
                         "chronicity, cognition/motor/sensory traits, life "
                         "events and engagement-driven attrition. Emits extra "
                         "columns; downstream scripts auto-detect them.")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    os.makedirs(args.out, exist_ok=True)

    if args.rich and args.mode != "trajectory":
        raise SystemExit("--rich requires --mode trajectory")

    if args.mode == "single":
        bal = gen_balanced(rng, args.n_balanced)
        nat = gen_natural(rng, args.n_natural)
    else:
        bal = gen_balanced_traj(rng, args.patients_balanced,
                                args.sessions_min, args.sessions_max,
                                rich=args.rich)
        nat = gen_natural_traj(rng, args.patients_natural,
                               args.sessions_min, args.sessions_max,
                               rich=args.rich)

    fields = FEATURE_FIELDS + RICH_FIELDS if args.rich else FEATURE_FIELDS
    nb = write_csv(os.path.join(args.out, "profiles_balanced_v3.csv"), bal, fields)
    nn = write_csv(os.path.join(args.out, "profiles_natural_v3.csv"), nat, fields)

    print(f"[gen_profiles] mode={args.mode} rich={args.rich} "
          f"conditions={len(cp.CONDITIONS)}")
    print(f"  balanced : {nb} rows -> profiles_balanced_v3.csv")
    print(f"  natural  : {nn} rows -> profiles_natural_v3.csv")
    from collections import Counter
    print("  balanced per-condition:", dict(Counter(r["diagnosis"] for r in bal)))


if __name__ == "__main__":
    main()
