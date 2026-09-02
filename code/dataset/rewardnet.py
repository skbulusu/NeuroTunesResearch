"""
rewardnet.py  (RLHF reward model -- simulated preferences + real-feedback hook)
==============================================================================
This adds the missing piece for scaling the ML architecture beyond supervised
regression: a *reward model* trained from PREFERENCES, the way RLHF systems are.

Why a reward model (and not just EmotionNet)?
  EmotionNet predicts the *intended* affect target for a patient/session.
  But a music generator can hit that target in many ways, and some renditions
  are better than others (smoother iso-principle transition, less jarring, etc).
  A reward model scores candidate renditions so the generator can be steered /
  re-ranked toward the ones a listener would actually prefer -- this is the
  policy-improvement signal an RL loop needs.

How preferences are simulated (transparent, no black box):
  For each profile we take its clinical target affect (arousal,valence,focus,calm)
  and synthesize TWO candidate rendition-affect vectors by perturbing the target.
  The "preferred" candidate is the one whose affect is closer to the clinical
  target AND respects the iso-principle (starts nearer the patient's current
  mood-affect, resolves toward the goal). This yields a Bradley-Terry preference
  pair. Confidence-weighted rows contribute stronger preferences.

  These are SIMULATED preferences -- a stand-in until real listener feedback is
  collected. See `load_real_feedback()` for the drop-in real-data hook.

Model: RewardNet( [encoded profile | candidate affect (4)] ) -> scalar reward,
trained with the standard pairwise logistic (Bradley-Terry) loss:
    L = -log sigmoid( r(preferred) - r(rejected) )
Reported metric: pairwise ranking accuracy on a held-out split.

CPU-only, ~seconds.

Run:
    source /home/ubuntu/m2e_env/bin/activate
    cd code/dataset
    python rewardnet.py
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

import clinical_priors as cp

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = cp.TARGETS
BASE_NUMERIC = ["age", "stress_level", "sleep_quality", "energy_levels", "session_number"]
BASE_CATEG = ["gender", "diagnosis", "therapy_goal", "mood",
              "severity", "comorbidity", "time_of_day", "medication_state"]
SEED = 42


def resolve_features(df):
    """Use base columns + any rich columns that are actually present."""
    numeric = [c for c in BASE_NUMERIC + cp.RICH_NUMERIC if c in df.columns]
    categ = [c for c in BASE_CATEG + cp.RICH_CATEG if c in df.columns]
    return numeric, categ
REAL_FEEDBACK_CSV = os.path.join(HERE, "real_feedback.csv")

# mood -> current affect (where the listener starts), for iso-principle scoring
MOOD_VA = {
    "Anxious": (0.7, -0.6), "Tense": (0.6, -0.5), "Sad": (-0.5, -0.7),
    "Depressed": (-0.6, -0.6), "Angry": (0.8, -0.7), "Irritable": (0.6, -0.4),
    "Restless": (0.7, -0.2), "Fatigued": (-0.6, -0.2), "Numb": (-0.3, -0.3),
    "Calm": (-0.4, 0.5), "Content": (-0.2, 0.6), "Hopeful": (0.2, 0.6),
    "Happy": (0.5, 0.7), "Focused": (0.1, 0.3), "Neutral": (0.0, 0.0),
}


class RewardNet(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def build_encoder(df, numeric=None, categ=None):
    df = df.copy()
    df["comorbidity"] = df["comorbidity"].fillna("none").astype(str)
    if numeric is None or categ is None:
        numeric, categ = resolve_features(df)
    ct = ColumnTransformer([
        ("num", StandardScaler(), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categ),
    ])
    X = ct.fit_transform(df)
    X = X.toarray() if hasattr(X, "toarray") else X
    return ct, X.astype(np.float32)


def _iso_penalty(cand, start, target):
    """Small penalty if the candidate ignores the iso-principle: it should not
    sit farther from the patient's starting mood than the target does when the
    target itself is a gentle move. Rewards renditions that bridge start->goal."""
    # distance the candidate travels from start vs distance target travels
    d_cand = np.linalg.norm(cand[:2] - start)
    d_targ = np.linalg.norm(target[:2] - start)
    return max(0.0, d_cand - d_targ - 0.4)  # only penalize big overshoots


def simulate_preferences(df, rng):
    """Return (idx, cand_pref, cand_rej) arrays of simulated preference pairs."""
    idx, prefs, rejs, strengths = [], [], [], []
    tvals = df[TARGETS].values.astype(np.float32)
    for i in range(len(df)):
        target = tvals[i]
        mood = df.iloc[i]["mood"]
        start = np.array(MOOD_VA.get(mood, (0.0, 0.0)), dtype=np.float32)
        # two candidate renditions = target + gaussian perturbation
        c1 = np.clip(target + rng.normal(0, 0.35, size=4), -1, 1).astype(np.float32)
        c2 = np.clip(target + rng.normal(0, 0.35, size=4), -1, 1).astype(np.float32)
        # quality = negative distance to target minus iso overshoot penalty
        q1 = -np.linalg.norm(c1 - target) - _iso_penalty(c1, start, target)
        q2 = -np.linalg.norm(c2 - target) - _iso_penalty(c2, start, target)
        if abs(q1 - q2) < 1e-4:
            continue
        if q1 > q2:
            prefs.append(c1); rejs.append(c2)
        else:
            prefs.append(c2); rejs.append(c1)
        idx.append(i)
        strengths.append(abs(q1 - q2))
    return (np.array(idx), np.array(prefs, dtype=np.float32),
            np.array(rejs, dtype=np.float32), np.array(strengths, dtype=np.float32))


def load_real_feedback():
    """REAL-DATA HOOK.
    If real_feedback.csv exists, load listener preference pairs and return them
    as (profile_rows_df, pref_affect[N,4], rej_affect[N,4]). Expected columns:
      profile feature columns (age,gender,diagnosis,...) +
      pref_arousal,pref_valence,pref_focus,pref_calm,
      rej_arousal,rej_valence,rej_focus,rej_calm
    Each row = one A/B choice a real listener/therapist made (or a thumbs-up vs
    thumbs-down rendition for the same patient). Wire the platform's feedback
    table to emit this CSV and the same training code fine-tunes on real data.
    Returns None if no file present.
    """
    if not os.path.exists(REAL_FEEDBACK_CSV):
        return None
    fb = pd.read_csv(REAL_FEEDBACK_CSV)
    pcols = [f"pref_{t}" for t in TARGETS]
    rcols = [f"rej_{t}" for t in TARGETS]
    return fb, fb[pcols].values.astype(np.float32), fb[rcols].values.astype(np.float32)


def train_reward(profile_X, pref, rej, strengths, epochs=250, tag="simulated"):
    torch.manual_seed(SEED); np.random.seed(SEED)
    n = len(pref)
    perm = np.random.permutation(n)
    cut = int(0.85 * n)
    tr, te = perm[:cut], perm[cut:]
    in_dim = profile_X.shape[1] + 4
    model = RewardNet(in_dim)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)

    def feats(rows, cand):
        return torch.tensor(np.hstack([profile_X[rows], cand]))

    Xp_tr, Xr_tr = feats(tr, pref[tr]), feats(tr, rej[tr])
    Xp_te, Xr_te = feats(te, pref[te]), feats(te, rej[te])
    w_tr = torch.tensor(strengths[tr])
    for ep in range(epochs):
        model.train(); opt.zero_grad()
        diff = model(Xp_tr) - model(Xr_tr)
        loss = -(w_tr * torch.log(torch.sigmoid(diff) + 1e-8)).mean()
        loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        acc_tr = (model(Xp_tr) > model(Xr_tr)).float().mean().item()
        acc_te = (model(Xp_te) > model(Xr_te)).float().mean().item()
    print(f"[{tag}] pairs={n}  train_acc={acc_tr:.3f}  test_acc={acc_te:.3f}")
    return model, acc_tr, acc_te


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE,
                    help="directory holding dataset_balanced_v3.csv (default: script dir)")
    ap.add_argument("--no-save", action="store_true",
                    help="skip saving model weights / preprocessor")
    args = ap.parse_args()
    df = pd.read_csv(os.path.join(args.dir, "dataset_balanced_v3.csv"))
    numeric, categ = resolve_features(df)
    print(f"features: {len(numeric)} numeric + {len(categ)} categorical "
          f"({'rich' if any(c in cp.RICH_NUMERIC for c in numeric) else 'base'})")
    ct, X = build_encoder(df, numeric, categ)
    rng = np.random.default_rng(SEED)

    idx, pref, rej, strengths = simulate_preferences(df, rng)
    # weight preference strength by label confidence too
    strengths = strengths * df["confidence"].values[idx]
    print(f"simulated {len(idx)} preference pairs from {len(df)} profiles")
    model, acc_tr, acc_te = train_reward(X[idx], pref, rej, strengths,
                                         tag="simulated")

    lines = [
        "RewardNet (RLHF) results",
        f"  simulated preference pairs: {len(idx)}",
        f"  Bradley-Terry ranking accuracy: train={acc_tr:.3f} test={acc_te:.3f}",
        f"  reward input dim: {X.shape[1]}+4",
    ]

    # ---- SAVE the trained reward model + preprocessor ----
    if not args.no_save:
        torch.save(model.state_dict(), os.path.join(args.dir, "rewardnet_v3.pt"))
        joblib.dump(ct, os.path.join(args.dir, "rewardnet_v3_preprocess.joblib"))
        with open(os.path.join(args.dir, "rewardnet_v3_meta.json"), "w") as f:
            json.dump({
                "model": "RewardNet", "arch": "[profile|affect(4)]->64->32->1",
                "profile_dim": int(X.shape[1]), "input_dim": int(X.shape[1]) + 4,
                "targets": TARGETS, "numeric": numeric, "categorical": categ,
                "loss": "pairwise Bradley-Terry",
                "test_ranking_acc": round(float(acc_te), 4),
                "n_pairs": int(len(idx)),
            }, f, indent=2)
        lines.append("  saved weights   -> rewardnet_v3.pt")
        lines.append("  saved preprocess-> rewardnet_v3_preprocess.joblib")
        lines.append("  saved meta      -> rewardnet_v3_meta.json")
        print("[saved] rewardnet_v3.pt / rewardnet_v3_preprocess.joblib / "
              "rewardnet_v3_meta.json")

    real = load_real_feedback()
    if real is not None:
        fb, rp, rr = real
        _, ctf_X = build_encoder(fb)
        st = np.ones(len(rp), dtype=np.float32)
        print(f"\n[real feedback] found {len(rp)} real preference pairs -- fine-tuning")
        _, ra_tr, ra_te = train_reward(ctf_X, rp, rr, st, tag="real")
        lines.append(f"  REAL feedback pairs: {len(rp)}  test_acc={ra_te:.3f}")
    else:
        lines.append("  real-feedback hook: no real_feedback.csv yet "
                     "(drop one in to fine-tune on listener data)")

    with open(os.path.join(args.dir, "rewardnet_results.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n[written] rewardnet_results.txt")


if __name__ == "__main__":
    main()
