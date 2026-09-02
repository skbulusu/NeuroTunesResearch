#!/usr/bin/env python3
"""
distill_from_llm.py — Stage 1 of the model-improvement pipeline.

Distill an open-source LLM's clinical reasoning into the PRODUCTION EmotionNet.

Pipeline
--------
1. Stage-0 (separate, offline): llm_pseudolabel.py runs an open-source instruction
   LLM (Qwen2.5-7B-Instruct, Apache-2.0) over the synthetic patient assessments and
   emits, per patient, a soft therapeutic TARGET vector [arousal, valence, focus, calm]
   in [-1, 1] -> llm_labels.csv. These are model-derived clinical *reasoning* labels
   (deterministic, temp=0), NOT human ground truth.

2. This script:
     a. loads llm_labels.csv and joins it to the production patient rows on patient_id,
     b. fits the production preprocessor (ColumnTransformer) on the FULL patient pool so
        the OneHotEncoder vocabulary + feature width stay byte-for-byte production-
        compatible (width must equal the deployed EmotionNet input_size), then transforms
        ONLY the labeled subset,
     c. trains a small TEACHER ensemble on the LLM labels (bootstrap; ensemble mean
        smooths LLM quantization),
     d. DISTILLS the teacher into the production EmotionNet architecture
        (input -> 64 -> 32 -> 4, tanh),
     e. reports honest held-out R^2 of EmotionNet vs the LLM clinician labels, plus a
        direct (non-distilled) student and the distillation gain,
     f. writes DROP-IN Ver3 artifacts (emotion_net.pth, preprocessor.pkl, columns.pkl,
        METRICS.txt) that load unchanged via WEIGHTS_PATH.

Everything is CPU-only and deterministic (fixed seeds). Reuses the exact production
feature space, so the artifacts are a drop-in replacement for the deployed weights.
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

_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)
if _MLSERVER not in sys.path:
    sys.path.insert(0, _MLSERVER)
from neurotunes_model import EmotionNet  # noqa: E402

NUMERIC = ["age", "stress_level", "sleep_quality", "energy_levels"]
CATEG = ["gender", "diagnosis", "therapy_goal", "mood"]
TARGETS = ["arousal", "valence", "focus", "calm"]


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
    ap.add_argument("--data", default=os.path.join(_MLSERVER, "data", "patients_v3_first_session.csv"),
                    help="FULL patient pool (defines preprocessor vocabulary + width). "
                         "Default = the rich v3 first-session subset.")
    ap.add_argument("--labels", default=os.path.join(_HERE, "llm_labels.csv"),
                    help="LLM pseudo-labels from llm_pseudolabel.py (patient_id + 4 targets)")
    ap.add_argument("--out", default=os.path.join(_HERE, "out_v3"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--teachers", type=int, default=7)
    ap.add_argument("--teacher_epochs", type=int, default=600)
    ap.add_argument("--student_epochs", type=int, default=1200)
    ap.add_argument("--test_frac", type=float, default=0.2)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    full = pd.read_csv(args.data)
    lab = pd.read_csv(args.labels)
    print(f"Full patient pool     : {len(full)} rows from {os.path.relpath(args.data, _MLSERVER)}")
    print(f"LLM pseudo-labels      : {len(lab)} rows from {os.path.relpath(args.labels, _MLSERVER)}")

    missing = [c for c in ["patient_id"] + TARGETS if c not in lab.columns]
    if missing:
        sys.exit(f"labels file is missing columns: {missing}")

    # join labels -> production rows on patient_id (labeled subset)
    df = full.merge(lab[["patient_id"] + TARGETS], on="patient_id", how="inner")
    if len(df) == 0:
        sys.exit("no patient_id overlap between --data and --labels")
    print(f"Labeled subset (joined): {len(df)} rows")
    # coverage report
    cov = df.groupby(["diagnosis", "therapy_goal"]).size()
    print("Coverage per diagnosis x therapy_goal:")
    for k, v in cov.items():
        print(f"    {k[0]:<12} {k[1]:<26} {v}")

    y = df[TARGETS].to_numpy(dtype=float)

    # ---- preprocessor: FIT ON FULL POOL so width + vocabulary == production --------
    pre = ColumnTransformer(transformers=[
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEG),
    ]).fit(full[NUMERIC + CATEG])
    X = pre.transform(df[NUMERIC + CATEG])
    X = X.toarray() if hasattr(X, "toarray") else np.asarray(X)
    d_in = X.shape[1]
    print(f"Preprocessed feature width = {d_in} (must match deployed EmotionNet input_size)")

    # ---- split the LABELED subset -------------------------------------------------
    n = len(df)
    idx = rng.permutation(n)
    n_test = max(1, int(args.test_frac * n))
    te, tr = idx[:n_test], idx[n_test:]
    Xtr, Xte = X[tr], X[te]
    ytr, yte = y[tr], y[te]
    print(f"Train/test split       : {len(tr)} / {len(te)} (test_frac={args.test_frac})")

    # ---- teacher ensemble on LLM labels (bootstrap; smooths quantization) ---------
    teachers = []
    for i in range(args.teachers):
        bs = rng.choice(len(Xtr), len(Xtr), replace=True)
        t = TeacherMLP(d_in)
        train_torch(t, Xtr[bs], ytr[bs], args.teacher_epochs, 2e-3, args.seed + i, wd=1e-4)
        teachers.append(t)

    def teacher_mean(Xin):
        return np.mean([predict(t, Xin) for t in teachers], axis=0)

    soft_tr = teacher_mean(Xtr)
    teach_te = teacher_mean(Xte)

    # ---- students (production EmotionNet architecture) ----------------------------
    student_hard = train_torch(EmotionNet(d_in), Xtr, ytr,
                               args.student_epochs, 1e-3, args.seed, wd=1e-4)
    student_distilled = train_torch(EmotionNet(d_in), Xtr, soft_tr,
                                    args.student_epochs, 1e-3, args.seed, wd=1e-4)

    # ---- honest evaluation: R^2 vs held-out LLM clinician labels ------------------
    def report(name, pred):
        r2 = r2_per_target(yte, pred)
        print(f"  {name:<38} mean R^2 = {np.mean(r2):+.3f}   per-target "
              f"[A {r2[0]:+.2f}  V {r2[1]:+.2f}  F {r2[2]:+.2f}  C {r2[3]:+.2f}]")
        return float(np.mean(r2))

    print("\n=== R^2 vs held-out LLM clinician labels (higher is better) ===")
    r_teacher = report("teacher ensemble (%dx)" % args.teachers, teach_te)
    r_hard = report("student EmotionNet - direct", predict(student_hard, Xte))
    r_dist = report("student EmotionNet - DISTILLED (Ver3)", predict(student_distilled, Xte))
    print(f"\n  Distillation gain (distilled - direct) = {r_dist - r_hard:+.3f} mean R^2")

    # ---- save DROP-IN Ver3 artifacts ----------------------------------------------
    os.makedirs(args.out, exist_ok=True)
    torch.save(student_distilled, os.path.join(args.out, "emotion_net.pth"))
    joblib.dump(pre, os.path.join(args.out, "preprocessor.pkl"))
    joblib.dump(NUMERIC + CATEG, os.path.join(args.out, "columns.pkl"))
    with open(os.path.join(args.out, "METRICS.txt"), "w") as f:
        f.write("NeuroTunes EmotionNet Ver3 (LLM-distilled clinical reasoning)\n")
        f.write(f"teacher_llm=Qwen2.5-7B-Instruct (Apache-2.0)  labeled_rows={n}\n")
        f.write(f"seed={args.seed} teachers={args.teachers} "
                f"teacher_epochs={args.teacher_epochs} student_epochs={args.student_epochs}\n")
        f.write(f"input_width={d_in}  test_frac={args.test_frac}\n\n")
        f.write("R^2 vs held-out LLM clinician labels:\n")
        f.write(f"  teacher ensemble      : {r_teacher:+.3f}\n")
        f.write(f"  student direct        : {r_hard:+.3f}\n")
        f.write(f"  student DISTILLED     : {r_dist:+.3f}  (DEPLOYED Ver3)\n")
        f.write(f"  distillation gain     : {r_dist - r_hard:+.3f}\n")
    print(f"\nSaved drop-in Ver3 artifacts to {args.out}/")
    print("  emotion_net.pth  preprocessor.pkl  columns.pkl  METRICS.txt")
    print("Deploy by pointing WEIGHTS_PATH at that directory (see repo README).")


if __name__ == "__main__":
    main()
