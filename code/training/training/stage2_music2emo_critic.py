#!/usr/bin/env python3
"""
stage2_music2emo_critic.py — Stage 2 of the model-improvement pipeline.

Objective, human-label-adjacent quality gate for the generated music.

Idea
----
Stage 1 makes EmotionNet emit a therapeutic TARGET affect [arousal, valence, ...]
for a patient, and the production MusicGenerator renders that target into audio.
But nothing checks whether the rendered audio actually *sounds* like the intended
affect. Stage 2 closes that loop with an independent critic:

    Music2Emo (AMAAI-Lab, Apache-2.0; MERT-based; trained on DEAM / PMEmo /
    EmoMusic / MTG-Jamendo human valence-arousal annotations)

We sweep a grid of intended (valence, arousal) targets, render each with the
production generator, ask Music2Emo to *perceive* valence/arousal from the audio,
and correlate perceived vs intended. High correlation => the generator faithfully
renders the affect EmotionNet asks for, judged by a model trained on human labels.

This is an objective critic, not human ground truth, but it is trained on human
perceptual annotations, so it is the closest label-free proxy available and a
legitimate automated gate before any human-subject study.

Runs on CPU. Music2Emo predicts valence/arousal on a 1..9 scale; we map to
[-1, 1] via (x - 5) / 4 to compare against EmotionNet's [-1, 1] targets.
"""
import os
import sys
import csv
import json
import argparse
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)
if _MLSERVER not in sys.path:
    sys.path.insert(0, _MLSERVER)


def build_grid(n_side):
    """Grid of intended (valence, arousal) in [-0.8, 0.8]^2."""
    xs = np.linspace(-0.8, 0.8, n_side)
    grid = [(float(v), float(a)) for v in xs for a in xs]
    return grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m2e_repo", default="/home/ubuntu/music2emo_repo",
                    help="path to cloned AMAAI-Lab/Music2Emotion")
    ap.add_argument("--out", default=os.path.join(_HERE, "out_stage2"))
    ap.add_argument("--grid", type=int, default=4, help="grid side (n x n targets)")
    ap.add_argument("--diagnosis", default="Depression")
    ap.add_argument("--therapy_goal", default="Apathy & Mood Regulation")
    ap.add_argument("--focus", type=float, default=0.0)
    ap.add_argument("--calm", type=float, default=0.0)
    args = ap.parse_args()

    # Reproducible validation: the generator uses random note durations /
    # melodic movement, so seed both RNGs to get a stable, repeatable
    # perceived-affect measurement across runs.
    import random as _random
    _seed = int(os.environ.get("STAGE2_SEED", "0"))
    _random.seed(_seed)
    np.random.seed(_seed)

    args.out = os.path.abspath(args.out)
    os.makedirs(args.out, exist_ok=True)
    wav_dir = os.path.join(args.out, "wav")
    os.makedirs(wav_dir, exist_ok=True)

    grid = build_grid(args.grid)
    print(f"Sweeping {len(grid)} intended (valence, arousal) targets "
          f"[{args.diagnosis} / {args.therapy_goal}]")

    # === Phase 1: GENERATE all tracks (cwd = wav_dir; tracks land in wav_dir/output)
    # We must NOT generate inside the Music2Emo repo: its predict() does
    # shutil.rmtree("./output") on every call and would delete our tracks.
    from music_generator import MusicGenerator
    os.chdir(wav_dir)
    os.makedirs("output", exist_ok=True)  # generator writes MIDIs/WAVs to ./output
    gen = MusicGenerator()
    generated = []  # (val, aro, abs_wav_path)
    for i, (val, aro) in enumerate(grid):
        targets = {"arousal": aro, "valence": val, "focus": args.focus, "calm": args.calm}
        profile = {"diagnosis": args.diagnosis, "therapy_goal": args.therapy_goal,
                   "age": 45, "severity": "moderate", "session_number": 1}
        tracks = gen.generate_therapeutic_music(targets, profile, num_tracks=1)
        if not tracks or not tracks[0].get("audio_file"):
            print(f"  [gen {i+1}/{len(grid)}] failed (v={val:+.2f} a={aro:+.2f}) — skip")
            continue
        abs_wav = os.path.abspath(tracks[0]["audio_file"])
        generated.append((val, aro, abs_wav))
        print(f"  [gen {i+1}/{len(grid)}] v={val:+.2f} a={aro:+.2f} -> {os.path.basename(abs_wav)}")

    # === Phase 2: CRITIC (cwd = repo for its relative configs; predict abs paths) ==
    sys.path.insert(0, args.m2e_repo)
    os.chdir(args.m2e_repo)
    from music2emo import Music2emo
    critic = Music2emo()

    rows = []
    for i, (val, aro, abs_wav) in enumerate(generated):
        if not os.path.exists(abs_wav):
            print(f"  [critic {i+1}/{len(generated)}] missing {abs_wav} — skip")
            continue
        try:
            pred = critic.predict(abs_wav)
            pv = (float(pred["valence"]) - 5.0) / 4.0
            pa = (float(pred["arousal"]) - 5.0) / 4.0
        except Exception as e:
            print(f"  [critic {i+1}/{len(generated)}] failed on {os.path.basename(abs_wav)}: {e}")
            continue
        rows.append({"intended_valence": val, "intended_arousal": aro,
                     "perceived_valence": pv, "perceived_arousal": pa,
                     "wav": os.path.basename(abs_wav)})
        print(f"  [critic {i+1}/{len(generated)}] intended v={val:+.2f} a={aro:+.2f}  ->  "
              f"perceived v={pv:+.2f} a={pa:+.2f}")

    if len(rows) < 3:
        sys.exit(f"only {len(rows)} usable tracks — cannot correlate")

    iv = np.array([r["intended_valence"] for r in rows])
    ia = np.array([r["intended_arousal"] for r in rows])
    pv = np.array([r["perceived_valence"] for r in rows])
    pa = np.array([r["perceived_arousal"] for r in rows])

    def pearson(x, y):
        return float(np.corrcoef(x, y)[0, 1])

    def spearman(x, y):
        rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
        return pearson(rx.astype(float), ry.astype(float))

    r_val, r_aro = pearson(iv, pv), pearson(ia, pa)
    s_val, s_aro = spearman(iv, pv), spearman(ia, pa)

    # write csv
    csv_path = os.path.join(args.out, "stage2_results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    metrics = {
        "n_tracks": len(rows),
        "critic": "Music2Emo (AMAAI-Lab, Apache-2.0, MERT-based)",
        "diagnosis": args.diagnosis, "therapy_goal": args.therapy_goal,
        "pearson_valence": r_val, "pearson_arousal": r_aro,
        "spearman_valence": s_val, "spearman_arousal": s_aro,
    }
    with open(os.path.join(args.out, "stage2_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n=== Stage 2: intended vs Music2Emo-perceived (n=%d) ===" % len(rows))
    print(f"  valence  Pearson r = {r_val:+.3f}   Spearman = {s_val:+.3f}")
    print(f"  arousal  Pearson r = {r_aro:+.3f}   Spearman = {s_aro:+.3f}")
    print(f"\nSaved: {csv_path}")
    print(f"       {os.path.join(args.out, 'stage2_metrics.json')}")


if __name__ == "__main__":
    main()
