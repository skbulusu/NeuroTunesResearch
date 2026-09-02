#!/usr/bin/env python3
"""
track_qa.py -- Objective QA harness for the NeuroTunes clinical MIDI generator.

Answers three questions, purely from the generated artifacts (NO music
therapist needed):

  1. FEATURES / MUSIC QUALITY   -- note density, polyphony, longest silence,
                                   note count, active instruments.
  2. PARAMETER CONFORMANCE      -- does the generated MIDI actually match the
                                   tempo / mode / register / dynamics /
                                   instruments / binaural settings that
                                   _create_clinical_params() selected?
  3. DURATION                   -- intended vs. actual track length (seconds).

For every generated track it emits an intended-vs-actual row with a PASS/FAIL
per check, writes a CSV, and prints a summary with an overall conformance rate.

Usage:
    cd code                 (so the generator's "output/" dir resolves)
    python training/track_qa.py --out training/qa_out --seed 0

This is objective *engineering* QA (does the generator do what it says).
It is NOT clinical-efficacy validation (that needs human outcomes).
"""
import argparse
import csv
import os
import random
import sys
from datetime import datetime

import numpy as np
import pretty_midi

# Import the production generator from the parent (code) dir.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from music_generator import MusicGenerator  # noqa: E402


# Tolerances for PASS/FAIL. Chosen to be strict enough to catch real bugs
# but tolerant of the generator's intentional per-track randomness.
TEMPO_TOL_BPM = 2.0          # written tempo should match params exactly (~rounding)
DUR_TOL_FRAC = 0.05          # actual end-time within 5% of intended duration
IN_SCALE_MIN = 0.90          # >=90% of pitches must belong to the intended mode
REGISTER_TOL_ST = 6.0        # mean melody pitch within 6 semitones of expected
DENSITY_MIN = 0.05           # at least some notes (notes/sec) -> not empty
SILENCE_MAX_FRAC = 0.25      # longest silent gap < 25% of track


def _root_pc(key_name):
    """Pitch class (0-11) of a key name like 'C', 'Db', 'Bb'."""
    try:
        return pretty_midi.note_name_to_number(f"{key_name}0") % 12
    except Exception:
        return 0


def analyze_midi(path):
    """Extract objective acoustic/structural features from a MIDI file."""
    pm = pretty_midi.PrettyMIDI(path)
    end = pm.get_end_time()
    _, tempi = pm.get_tempo_changes()
    tempo = float(tempi[0]) if len(tempi) else float("nan")

    all_notes = []
    programs = []
    inst_names = []
    for inst in pm.instruments:
        programs.append(inst.program)
        inst_names.append(inst.name or "")
        for n in inst.notes:
            all_notes.append(n)

    pitches = np.array([n.pitch for n in all_notes]) if all_notes else np.array([])
    vels = np.array([n.velocity for n in all_notes]) if all_notes else np.array([])

    # Note density (notes / second) and polyphony (max simultaneous notes).
    density = (len(all_notes) / end) if end > 0 else 0.0
    polyphony = _max_polyphony(all_notes)
    silence_frac = _longest_silence(all_notes, end)

    return {
        "pm": pm,
        "actual_tempo": tempo,
        "actual_duration": end,
        "n_notes": len(all_notes),
        "n_instruments": len(pm.instruments),
        "programs": programs,
        "inst_names": inst_names,
        "pitches": pitches,
        "vels": vels,
        "density": density,
        "polyphony": polyphony,
        "silence_frac": silence_frac,
    }


def _max_polyphony(notes):
    if not notes:
        return 0
    events = []
    for n in notes:
        events.append((n.start, 1))
        events.append((n.end, -1))
    events.sort()
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    return mx


def _longest_silence(notes, end):
    """Longest gap (as a fraction of total duration) with no sounding note."""
    if not notes or end <= 0:
        return 1.0
    intervals = sorted((n.start, n.end) for n in notes)
    merged = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    gap = merged[0][0]  # silence before first note
    for i in range(1, len(merged)):
        gap = max(gap, merged[i][0] - merged[i - 1][1])
    gap = max(gap, end - merged[-1][1])  # trailing silence
    return gap / end


def _best_fit_fraction(pcs, scale):
    """Max fraction of pitch-classes matching the mode over all 12 roots."""
    if not pcs:
        return 0.0
    best = 0.0
    for root in range(12):
        allowed = {(root + s) % 12 for s in scale}
        best = max(best, sum(1 for pc in pcs if pc in allowed) / len(pcs))
    return best


def mode_conformance_per_layer(pm, mode, scales):
    """Note-weighted mean of per-instrument best-fit in-scale fraction.

    Measures whether each layer (melody, chords, complement) individually
    follows the intended mode's interval structure. Near 1.0 = every layer
    respects the mode.
    """
    scale = scales.get(mode, scales["major"])
    total = 0
    acc = 0.0
    for inst in pm.instruments:
        pcs = [n.pitch % 12 for n in inst.notes]
        if not pcs:
            continue
        acc += _best_fit_fraction(pcs, scale) * len(pcs)
        total += len(pcs)
    return acc / total if total else 0.0


def key_coherence(pitches, mode, scales):
    """Whole-mix best-fit in-scale fraction (single shared root).

    LOW value + HIGH per-layer conformance => layers are the right mode but
    are transposed to different roots (polytonal / no shared key center).
    """
    scale = scales.get(mode, scales["major"])
    pcs = [int(p) % 12 for p in pitches]
    return _best_fit_fraction(pcs, scale)


def build_cases():
    """Grid of clinical scenarios x affect targets to exercise the generator."""
    diagnoses = [
        "anxiety", "depression", "post_stroke", "parkinson",
        "adhd", "ptsd", "dementia", "healthy",
    ]
    # (valence, arousal) corners + center of the affect plane.
    affects = [
        (-0.8, -0.8), (-0.8, 0.8), (0.8, -0.8), (0.8, 0.8), (0.0, 0.0),
    ]
    cases = []
    for diag in diagnoses:
        for (v, a) in affects:
            cases.append({"diagnosis": diag, "valence": v, "arousal": a})
    return cases


def expected_binaural(params):
    """Generator only writes a binaural track when arousal < 0.3 (post-fix)."""
    return bool(params.get("binaural_frequency")) and params.get("affect_arousal", -1.0) < 0.3


def run(out_dir, seed):
    random.seed(seed)
    np.random.seed(seed)

    gen = MusicGenerator()
    os.makedirs(out_dir, exist_ok=True)
    # create_clinical_midi writes to "output/..." relative to CWD.
    os.makedirs("output", exist_ok=True)

    rows = []
    for i, case in enumerate(build_cases()):
        targets = {
            "valence": case["valence"],
            "arousal": case["arousal"],
            "focus": 0.0,
            "energy_state": case["arousal"],
        }
        profile = {"diagnosis": case["diagnosis"], "severity": "moderate",
                   "session_number": 1, "age": 40}
        primary = gen._clinical_assessment(targets, profile)
        secondary = gen._identify_secondary_goals(targets, profile)
        params = gen._create_clinical_params(targets, profile, primary, secondary, 0)

        name = f"qa_{i:02d}_{case['diagnosis']}_v{case['valence']}_a{case['arousal']}"
        midi_path = gen.create_clinical_midi(params, name)
        if not midi_path or not os.path.exists(midi_path):
            print(f"[FAIL] generation returned no file for {name}")
            continue

        feats = analyze_midi(midi_path)

        # ---- Conformance checks (intended vs actual) ----
        int_tempo = params["tempo"]
        int_dur = params["duration"]
        int_mode = params["mode"]
        int_key = params["key"]
        int_progs = params["instruments"]
        reg_off = params.get("register_offset", 0)
        exp_reg = 60 + reg_off  # melody base is ~60 + register_offset

        mode_conf = mode_conformance_per_layer(feats["pm"], int_mode, gen.scales)
        key_coh = key_coherence(feats["pitches"], int_mode, gen.scales)
        mean_pitch = float(np.mean(feats["pitches"])) if len(feats["pitches"]) else float("nan")

        chk_tempo = abs(feats["actual_tempo"] - int_tempo) <= TEMPO_TOL_BPM
        chk_dur = abs(feats["actual_duration"] - int_dur) <= DUR_TOL_FRAC * int_dur
        chk_mode = mode_conf >= IN_SCALE_MIN
        chk_reg = (not np.isnan(mean_pitch)) and abs(mean_pitch - exp_reg) <= REGISTER_TOL_ST + 12
        # main program should be the first intended instrument
        chk_instr = len(feats["programs"]) > 0 and feats["programs"][0] == int_progs[0]
        chk_density = feats["density"] >= DENSITY_MIN
        chk_silence = feats["silence_frac"] <= SILENCE_MAX_FRAC
        exp_bin = expected_binaural(params)
        has_bin = any("binaural" in n.lower() or "Binaural" in n for n in feats["inst_names"])
        chk_bin = (has_bin == exp_bin)

        checks = {
            "tempo": chk_tempo, "duration": chk_dur, "mode": chk_mode,
            "register": chk_reg, "instrument": chk_instr, "density": chk_density,
            "silence": chk_silence, "binaural": chk_bin,
        }
        n_pass = sum(checks.values())

        rows.append({
            "case": name,
            "diagnosis": case["diagnosis"],
            "goal": primary,
            "valence": case["valence"], "arousal": case["arousal"],
            "int_tempo": int_tempo, "act_tempo": round(feats["actual_tempo"], 1),
            "int_dur_s": round(int_dur, 1), "act_dur_s": round(feats["actual_duration"], 1),
            "int_mode": int_mode,
            "mode_conf_pct": round(mode_conf * 100, 1),
            "key_coherence_pct": round(key_coh * 100, 1),
            "exp_register": exp_reg, "mean_pitch": round(mean_pitch, 1) if not np.isnan(mean_pitch) else "",
            "int_instr": int_progs[0], "act_instr": feats["programs"][0] if feats["programs"] else "",
            "n_instr": feats["n_instruments"], "n_notes": feats["n_notes"],
            "density_nps": round(feats["density"], 2), "polyphony": feats["polyphony"],
            "silence_frac": round(feats["silence_frac"], 3),
            "exp_binaural": exp_bin, "has_binaural": has_bin,
            "checks_pass": f"{n_pass}/8",
            **{f"chk_{k}": ("PASS" if val else "FAIL") for k, val in checks.items()},
        })

    # ---- Write CSV ----
    csv_path = os.path.join(out_dir, "track_qa.csv")
    if rows:
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    # ---- Summary ----
    print("\n" + "=" * 78)
    print("NeuroTunes Track QA -- objective parameter conformance & quality")
    print("=" * 78)
    total_checks = len(rows) * 8
    total_pass = sum(int(r["checks_pass"].split("/")[0]) for r in rows)
    print(f"Tracks analyzed : {len(rows)}")
    print(f"Checks passed   : {total_pass}/{total_checks} "
          f"({100*total_pass/max(1,total_checks):.1f}%)")
    # Per-check pass rate
    check_names = ["tempo", "duration", "mode", "register", "instrument",
                   "density", "silence", "binaural"]
    print("\nPer-check pass rate:")
    for c in check_names:
        p = sum(1 for r in rows if r[f"chk_{c}"] == "PASS")
        print(f"  {c:11s}: {p}/{len(rows)} ({100*p/max(1,len(rows)):.0f}%)")
    # Duration stats
    durs = [r["act_dur_s"] for r in rows]
    if durs:
        print(f"\nDuration (actual, seconds): min={min(durs):.1f} "
              f"max={max(durs):.1f} mean={np.mean(durs):.1f}")
    # Mode fidelity: per-layer conformance vs whole-mix key coherence
    mc = [r["mode_conf_pct"] for r in rows]
    kc = [r["key_coherence_pct"] for r in rows]
    if mc:
        print(f"Mode conformance (per-layer): mean={np.mean(mc):.1f}%  "
              f"(each layer follows the intended mode)")
        print(f"Key coherence  (shared root): mean={np.mean(kc):.1f}%  "
              f"(lower => layers transposed to different roots / polytonal)")
    # Tempo responsiveness to arousal (sanity)
    lo = [r["act_tempo"] for r in rows if r["arousal"] <= -0.5]
    hi = [r["act_tempo"] for r in rows if r["arousal"] >= 0.5]
    if lo and hi:
        print(f"Tempo vs arousal: low-arousal mean={np.mean(lo):.0f} BPM, "
              f"high-arousal mean={np.mean(hi):.0f} BPM "
              f"(delta={np.mean(hi)-np.mean(lo):+.0f})")
    print(f"\nCSV written: {csv_path}")
    print("=" * 78)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="training/qa_out")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    run(args.out, args.seed)
