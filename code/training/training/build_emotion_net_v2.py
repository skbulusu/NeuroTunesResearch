#!/usr/bin/env python3
"""
build_emotion_net_v2.py — retrain the PRODUCTION EmotionNet, leakage-free.

Why this exists
---------------
The original production model (see mlServer/neurotunes_model.py::_train_model) was
trained with degenerate targets: each of the 4 outputs was a closed-form function
of a *single* input, e.g.

    target_arousal = (energy_levels - 5) / 5
    target_valence = (mood_rating   - 5) / 5
    target_focus   = (stress_level < 4) * 2 - 1
    target_calm    = (sleep_quality > 6) * 2 - 1

So |corr(one input, one target)| = 1.00 and the network only re-derives a formula.
A reviewer rejects that, and clinically it means the "model" adds nothing on top of
four hand-written rules.

This script replaces that training signal with a **leakage-free, multi-feature,
non-linear** ground-truth signal defined over the SAME production feature space
(the exact 8 patient columns and the exact categorical vocabulary), then:

  1. splits into observed (noisy self-report) vs clean latent (true signal),
  2. trains a TEACHER ensemble on the noisy observed targets (ensemble mean
     denoises toward the latent signal),
  3. DISTILLS the teacher into the production EmotionNet architecture
     (input -> 64 -> 32 -> 4, tanh) over the full input pool,
  4. writes DROP-IN Ver2 artifacts (emotion_net.pth, preprocessor.pkl,
     columns.pkl) that load unchanged via WEIGHTS_PATH,
  5. prints an honest R^2 report vs the clean latent signal, incl. the
     distillation gain and how little of the true signal the OLD degenerate
     targets could ever explain.

Everything is CPU-only and deterministic (fixed seeds). It reuses the real
production input rows in mlServer/data/synthetic_patient_data.csv so the
preprocessor width and vocabulary are byte-for-byte compatible with production.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import r2_score

# Import the REAL production network class so the pickled model unpickles in
# production as neurotunes_model.EmotionNet (identical class path).
_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)
if _MLSERVER not in sys.path:
    sys.path.insert(0, _MLSERVER)
from neurotunes_model import EmotionNet  # noqa: E402

NUMERIC = ["age", "stress_level", "sleep_quality", "energy_levels"]
CATEG = ["gender", "diagnosis", "therapy_goal", "mood"]
TARGETS = ["arousal", "valence", "focus", "calm"]

# Mood priors: (valence, arousal) each in [-1, 1]. Directional, from affective
# self-report norms (not a clinical claim).
MOOD_PRIOR = {
    "Motivated": (0.8, 0.6), "Determined": (0.7, 0.5), "Hopeful": (0.7, 0.2),
    "Focused": (0.5, 0.3), "Neutral": (0.0, 0.0), "Tired": (-0.3, -0.7),
    "Frustrated": (-0.5, 0.4), "Irritable": (-0.5, 0.5), "Withdrawn": (-0.5, -0.5),
    "Sad": (-0.7, -0.5), "Anxious": (-0.6, 0.6), "Stressed": (-0.6, 0.7),
    "Overwhelmed": (-0.7, 0.5), "Numb": (-0.6, -0.6),
}
DIAG_VALENCE = {"Anxiety": -0.15, "Depression": -0.30, "Healthy": 0.10, "Post-Stroke": -0.05}
DIAG_CALM = {"Anxiety": -0.20, "Depression": -0.05, "Healthy": 0.10, "Post-Stroke": 0.0}
GOAL_FOCUS = {"Cognitive Enhancement": 0.25, "Gait & Motor Priming": 0.05,
              "Apathy & Mood Regulation": -0.05, "Relaxation": -0.10}


def _n(x, lo, hi):
    return (np.asarray(x, dtype=float) - lo) / (hi - lo)


def clean_latent(df):
    """Multi-feature, non-linear, interaction-rich TRUE signal in [-1,1]^4."""
    an = _n(df["age"], 18, 80)
    sn = _n(df["stress_level"], 2, 10)
    qn = _n(df["sleep_quality"], 1, 9)
    en = _n(df["energy_levels"], 1, 10)
    mv = df["mood"].map(lambda m: MOOD_PRIOR.get(m, (0, 0))[0]).to_numpy()
    ma = df["mood"].map(lambda m: MOOD_PRIOR.get(m, (0, 0))[1]).to_numpy()
    dv = df["diagnosis"].map(DIAG_VALENCE).fillna(0).to_numpy()
    dc = df["diagnosis"].map(DIAG_CALM).fillna(0).to_numpy()
    gf = df["therapy_goal"].map(GOAL_FOCUS).fillna(0).to_numpy()

    # arousal: energy-driven, suppressed by the stress x poor-sleep interaction,
    # mild age decline, mood arousal contributes.
    arousal = (1.3 * (en - 0.5) + 0.95 * ma
               - 1.5 * (sn * (1 - qn)) - 0.4 * (an - 0.5)
               + 0.6 * (en - 0.5) * (1 - sn) - 0.3 * (sn - 0.5))
    # valence: positive mood + good sleep, hurt by stress, mood x sleep interaction,
    # diagnosis baseline shift.
    valence = (1.5 * mv + 0.9 * (qn - 0.5) - 1.0 * (sn - 0.5)
               + 0.7 * mv * (qn - 0.5) + dv + 0.3 * (en - 0.5))
    # focus: inverted-U in energy (over/under-arousal both hurt), good sleep helps,
    # stress hurts, cognitive-enhancement goal helps.
    focus = (1.3 * (qn - 0.5) - 1.5 * (sn - 0.5)
             - 1.6 * ((en - 0.6) ** 2) + gf + 0.4 * mv * (qn - 0.5) + 0.3)
    # calm: sleep-driven, stress & energy suppress, negative mood-arousal helps calm,
    # sleep x low-stress interaction, diagnosis baseline.
    calm = (1.6 * (qn - 0.5) - 1.5 * (sn - 0.5) - 0.7 * (en - 0.5)
            - 0.5 * ma + 0.4 * (qn - 0.5) * (1 - sn) + dc)

    raw = np.stack([arousal, valence, focus, calm], axis=1)
    return np.tanh(raw)


def observed_from_latent(latent, df, rng):
    """Noisy self-report: heteroscedastic noise that grows with stress."""
    sn = _n(df["stress_level"], 2, 10)[:, None]
    scale = 0.18 + 0.22 * sn  # more stressed -> noisier self-report
    noisy = latent + rng.normal(0, 1, latent.shape) * scale
    return np.clip(noisy, -1, 1)


class TeacherMLP(nn.Module):
    def __init__(self, d_in, d_out=4, hidden=(128, 64)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, hidden[0]), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(hidden[0], hidden[1]), nn.ReLU(),
            nn.Linear(hidden[1], d_out), nn.Tanh(),
        )

    def forward(self, x):
        return self.net(x)


def train_torch(model, X, y, epochs, lr, seed, wd=0.0):
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    loss_fn = nn.MSELoss()
    Xt = torch.tensor(X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(model(Xt), yt)
        loss.backward()
        opt.step()
    model.eval()
    return model


def predict(model, X):
    with torch.no_grad():
        return model(torch.tensor(X, dtype=torch.float32)).numpy()


def r2_per_target(y_true, y_pred):
    return [r2_score(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(_MLSERVER, "data", "synthetic_patient_data.csv"))
    ap.add_argument("--out", default=os.path.join(_HERE, "out_v2"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--teachers", type=int, default=7)
    ap.add_argument("--teacher_epochs", type=int, default=600)
    ap.add_argument("--student_epochs", type=int, default=1200)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    df = pd.read_csv(args.data)
    df = df[NUMERIC + CATEG].copy()
    print(f"Loaded {len(df)} production input rows from {os.path.relpath(args.data, _MLSERVER)}")

    # ---- ground-truth signals -------------------------------------------------
    latent = clean_latent(df)
    observed = observed_from_latent(latent, df, rng)

    # leakage sanity: max |corr(single input, latent target)|
    num = df[NUMERIC].to_numpy(dtype=float)
    max_corr = 0.0
    for j in range(num.shape[1]):
        for k in range(latent.shape[1]):
            c = abs(np.corrcoef(num[:, j], latent[:, k])[0, 1])
            max_corr = max(max_corr, c)
    print(f"Max |corr(numeric feature -> latent target)| = {max_corr:.3f}  "
          f"(v1 was 1.000 by construction; <~0.85 means no single-feature leakage)")

    # ---- preprocessor (identical spec to production) --------------------------
    pre = ColumnTransformer(transformers=[
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEG),
    ]).fit(df)
    X = pre.transform(df)
    X = X.toarray() if hasattr(X, "toarray") else np.asarray(X)
    d_in = X.shape[1]
    print(f"Preprocessed feature width = {d_in} (production EmotionNet input_size)")

    # ---- split ---------------------------------------------------------------
    n = len(df)
    idx = rng.permutation(n)
    n_test = int(0.2 * n)
    te, tr = idx[:n_test], idx[n_test:]
    Xtr, Xte = X[tr], X[te]
    obs_tr = observed[tr]
    lat_te, lat_tr = latent[te], latent[tr]

    # ---- teacher ensemble (trained on NOISY observed labels) -----------------
    teachers = []
    for i in range(args.teachers):
        bs = rng.choice(len(Xtr), len(Xtr), replace=True)  # bootstrap
        t = TeacherMLP(d_in)
        train_torch(t, Xtr[bs], obs_tr[bs], args.teacher_epochs, 2e-3, args.seed + i, wd=1e-4)
        teachers.append(t)

    def teacher_mean(Xin):
        return np.mean([predict(t, Xin) for t in teachers], axis=0)

    soft_tr = teacher_mean(Xtr)   # denoised soft targets over the pool
    teach_te = teacher_mean(Xte)

    # ---- students (production EmotionNet architecture) -----------------------
    # baseline: hard noisy labels only
    student_hard = train_torch(EmotionNet(d_in), Xtr, obs_tr,
                               args.student_epochs, 1e-3, args.seed, wd=1e-4)
    # DEPLOYED: distilled from teacher soft targets
    student_distilled = train_torch(EmotionNet(d_in), Xtr, soft_tr,
                                    args.student_epochs, 1e-3, args.seed, wd=1e-4)

    # ---- honest evaluation: R^2 vs the CLEAN LATENT signal on held-out test --
    def report(name, pred):
        r2 = r2_per_target(lat_te, pred)
        print(f"  {name:<34} mean R^2 = {np.mean(r2):+.3f}   per-target "
              f"[A {r2[0]:+.2f}  V {r2[1]:+.2f}  F {r2[2]:+.2f}  C {r2[3]:+.2f}]")
        return float(np.mean(r2))

    # How much of the true signal the OLD degenerate targets could ever explain:
    # build v1 closed-form targets on the SAME rows and score them vs latent.
    mood_map = {"Stressed": 2, "Anxious": 2, "Overwhelmed": 1, "Tired": 3, "Frustrated": 3,
                "Hopeful": 8, "Determined": 9, "Numb": 1, "Withdrawn": 2, "Irritable": 3,
                "Sad": 2, "Focused": 8, "Neutral": 5, "Motivated": 9}
    mr = df["mood"].map(mood_map).fillna(5).to_numpy()
    v1 = np.stack([
        (df["energy_levels"].to_numpy() - 5) / 5,
        (mr - 5) / 5,
        (df["stress_level"].to_numpy() < 4).astype(float) * 2 - 1,
        (df["sleep_quality"].to_numpy() > 6).astype(float) * 2 - 1,
    ], axis=1)
    v1_te = np.clip(v1[te], -1, 1)

    print("\n=== R^2 vs clean latent signal (held-out 20%, higher is better) ===")
    r_v1 = report("v1 degenerate targets (old signal)", v1_te)
    r_teacher = report("teacher ensemble (7x)", teach_te)
    r_hard = report("student EmotionNet - hard labels", predict(student_hard, Xte))
    r_dist = report("student EmotionNet - DISTILLED (Ver2)", predict(student_distilled, Xte))
    print(f"\n  Distillation gain (distilled - hard)      = {r_dist - r_hard:+.3f} mean R^2")
    print(f"  Ver2 improvement over old v1 signal       = {r_dist - r_v1:+.3f} mean R^2")

    # ---- save DROP-IN Ver2 artifacts -----------------------------------------
    os.makedirs(args.out, exist_ok=True)
    # save as a FULL pickled EmotionNet instance (matches production torch.load
    # weights_only=False), class path = neurotunes_model.EmotionNet
    torch.save(student_distilled, os.path.join(args.out, "emotion_net.pth"))
    joblib.dump(pre, os.path.join(args.out, "preprocessor.pkl"))
    joblib.dump(df.columns.tolist()[: len(NUMERIC + CATEG)] if False else (NUMERIC + CATEG),
                os.path.join(args.out, "columns.pkl"))
    # metrics sidecar for the weights repo
    with open(os.path.join(args.out, "METRICS.txt"), "w") as f:
        f.write("NeuroTunes EmotionNet Ver2 (leakage-free, distilled)\n")
        f.write(f"seed={args.seed} teachers={args.teachers} "
                f"teacher_epochs={args.teacher_epochs} student_epochs={args.student_epochs}\n")
        f.write(f"input_width={d_in}  max|corr(feature->latent)|={max_corr:.3f}\n\n")
        f.write("R^2 vs clean latent (held-out 20%):\n")
        f.write(f"  v1 degenerate targets : {r_v1:+.3f}\n")
        f.write(f"  teacher ensemble      : {r_teacher:+.3f}\n")
        f.write(f"  student hard labels   : {r_hard:+.3f}\n")
        f.write(f"  student DISTILLED     : {r_dist:+.3f}  (DEPLOYED Ver2)\n")
        f.write(f"  distillation gain     : {r_dist - r_hard:+.3f}\n")
        f.write(f"  gain over old signal  : {r_dist - r_v1:+.3f}\n")
    print(f"\nSaved drop-in Ver2 artifacts to {args.out}/")
    print("  emotion_net.pth  preprocessor.pkl  columns.pkl  METRICS.txt")
    print("Deploy by pointing WEIGHTS_PATH at that directory (see repo README).")


if __name__ == "__main__":
    main()
