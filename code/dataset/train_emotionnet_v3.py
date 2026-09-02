"""
train_emotionnet_v3.py  (architecture-scaling proof)
====================================================
Trains the production EmotionNet (input -> 64 -> 32 -> 4, tanh) on the v3
BALANCED set, then evaluates R^2 on the v3 NATURAL-prevalence set. This is an
honest generalization test: we train on the balanced (over-sampled) data and
measure how well it predicts the naturally-distributed population it never saw.

Two ablations are run so we can show the confidence weighting helps:
  (1) unweighted MSE
  (2) confidence-weighted MSE (down-weights ambiguous / low-agreement rows)

CPU-only, ~seconds. No fabrication -- numbers are printed straight from sklearn.

Run:
    source /home/ubuntu/m2e_env/bin/activate
    cd code/dataset
    python train_emotionnet_v3.py
"""
import json
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import r2_score

import clinical_priors as cp

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = cp.TARGETS
# base feature columns, plus the optional rich columns (used automatically when
# present in the CSV -- see resolve_features()).
BASE_NUMERIC = ["age", "stress_level", "sleep_quality", "energy_levels", "session_number"]
BASE_CATEG = ["gender", "diagnosis", "therapy_goal", "mood",
              "severity", "comorbidity", "time_of_day", "medication_state"]
SEED = 42


def resolve_features(df):
    """Use base columns + any rich columns that are actually present."""
    numeric = [c for c in BASE_NUMERIC + cp.RICH_NUMERIC if c in df.columns]
    categ = [c for c in BASE_CATEG + cp.RICH_CATEG if c in df.columns]
    return numeric, categ


class EmotionNet(nn.Module):
    """Mirror of mlServer/neurotunes_model.py EmotionNet."""
    def __init__(self, input_size, output_size=4):
        super().__init__()
        self.layer1 = nn.Linear(input_size, 64)
        self.layer2 = nn.Linear(64, 32)
        self.output_layer = nn.Linear(32, output_size)
        self.relu = nn.ReLU()
        self.tanh = nn.Tanh()

    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.relu(self.layer2(x))
        return self.tanh(self.output_layer(x))


def prep(train_df, test_df, numeric, categ):
    # comorbidity has NaN for "none" -> fill so the encoder treats it as a category
    for df in (train_df, test_df):
        df["comorbidity"] = df["comorbidity"].fillna("none").astype(str)
    ct = ColumnTransformer([
        ("num", StandardScaler(), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categ),
    ])
    Xtr = ct.fit_transform(train_df)
    Xte = ct.transform(test_df)
    Xtr = Xtr.toarray() if hasattr(Xtr, "toarray") else Xtr
    Xte = Xte.toarray() if hasattr(Xte, "toarray") else Xte
    return ct, Xtr.astype(np.float32), Xte.astype(np.float32)


def train_eval(Xtr, Ytr, Xte, Yte, weights=None, epochs=300, tag=""):
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    model = EmotionNet(Xtr.shape[1], len(TARGETS))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    xt = torch.tensor(Xtr)
    yt = torch.tensor(Ytr.astype(np.float32))
    w = None if weights is None else torch.tensor(weights.astype(np.float32)).view(-1, 1)
    for ep in range(epochs):
        model.train()
        opt.zero_grad()
        pred = model(xt)
        se = (pred - yt) ** 2
        loss = (se * w).mean() if w is not None else se.mean()
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        yhat = model(torch.tensor(Xte)).numpy()
    per = {t: r2_score(Yte[:, i], yhat[:, i]) for i, t in enumerate(TARGETS)}
    overall = r2_score(Yte, yhat)
    print(f"\n[{tag}] R^2 on NATURAL eval set")
    for t in TARGETS:
        print(f"    {t:<8} R^2 = {per[t]:+.3f}")
    print(f"    {'OVERALL':<8} R^2 = {overall:+.3f}")
    return overall, per, model


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE,
                    help="directory holding dataset_*_v3.csv (default: script dir)")
    ap.add_argument("--no-save", action="store_true",
                    help="skip saving model weights / preprocessor")
    args = ap.parse_args()
    bal = pd.read_csv(os.path.join(args.dir, "dataset_balanced_v3.csv"))
    nat = pd.read_csv(os.path.join(args.dir, "dataset_natural_v3.csv"))
    print(f"train (balanced) = {len(bal)} rows | eval (natural) = {len(nat)} rows")
    numeric, categ = resolve_features(bal)
    print(f"features: {len(numeric)} numeric + {len(categ)} categorical "
          f"({'rich' if any(c in cp.RICH_NUMERIC for c in numeric) else 'base'})")
    ct, Xtr, Xte = prep(bal.copy(), nat.copy(), numeric, categ)
    Ytr = bal[TARGETS].values
    Yte = nat[TARGETS].values

    o_unw, _, _ = train_eval(Xtr, Ytr, Xte, Yte, weights=None,
                             tag="unweighted")
    o_w, per_w, model_w = train_eval(Xtr, Ytr, Xte, Yte,
                                     weights=bal["confidence"].values,
                                     tag="confidence-weighted")

    lines = []
    lines.append("EmotionNet v3 training proof")
    lines.append(f"  train=balanced ({len(bal)})  eval=natural ({len(nat)})")
    lines.append(f"  input_dim={Xtr.shape[1]}  arch=input->64->32->4 (tanh)")
    lines.append(f"  features: numeric={numeric}")
    lines.append(f"            categ={categ}")
    lines.append(f"  overall R^2 unweighted        = {o_unw:+.3f}")
    lines.append(f"  overall R^2 confidence-weighted = {o_w:+.3f}")
    lines.append("  per-target (confidence-weighted):")
    for t in TARGETS:
        lines.append(f"    {t:<8} {per_w[t]:+.3f}")

    # ---- SAVE the trained model + preprocessor so it can be loaded/served ----
    if not args.no_save:
        pt_path = os.path.join(args.dir, "emotionnet_v3.pt")
        pre_path = os.path.join(args.dir, "emotionnet_v3_preprocess.joblib")
        meta_path = os.path.join(args.dir, "emotionnet_v3_meta.json")
        torch.save(model_w.state_dict(), pt_path)
        joblib.dump(ct, pre_path)
        with open(meta_path, "w") as f:
            json.dump({
                "model": "EmotionNet", "arch": "input->64->32->4 (tanh)",
                "input_dim": int(Xtr.shape[1]), "targets": TARGETS,
                "numeric": numeric, "categorical": categ,
                "trained_on": "dataset_balanced_v3.csv (confidence-weighted)",
                "eval_overall_r2": round(float(o_w), 4),
                "n_train": int(len(bal)), "n_eval": int(len(nat)),
            }, f, indent=2)
        lines.append(f"  saved weights   -> emotionnet_v3.pt")
        lines.append(f"  saved preprocess-> emotionnet_v3_preprocess.joblib")
        lines.append(f"  saved meta      -> emotionnet_v3_meta.json")
        print(f"[saved] emotionnet_v3.pt / emotionnet_v3_preprocess.joblib / "
              f"emotionnet_v3_meta.json")

    with open(os.path.join(args.dir, "train_emotionnet_v3_results.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[written] train_emotionnet_v3_results.txt")


if __name__ == "__main__":
    main()
