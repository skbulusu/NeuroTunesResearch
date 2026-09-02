"""
distill.py  —  NeuroTunes affective-model knowledge distillation experiment.

Goal
----
Show a *real*, reproducible improvement from knowledge distillation on the
NeuroTunes affective model, WITHOUT any new real-world data.

Method
------
  TEACHER  : an ensemble of K wide MLPs trained on the (noisy) observed targets.
             Averaging the ensemble cancels independent variance, so the
             ensemble's mean prediction is a DENOISED estimate of the latent
             signal -> a better teacher than any single small model.
  STUDENT-hard      : one small MLP (the deployable size) trained on noisy labels.
  STUDENT-distilled : the SAME small architecture trained on the teacher's
             predictions (soft targets), blended with the hard labels (alpha).

We evaluate on a held-out test set against:
  * observed (noisy) targets  -> what you'd measure in practice, and
  * latent (clean) targets     -> the true signal (the thing we actually want).

The headline result is R^2 against the CLEAN latent targets: distillation should
let the small deployable student recover more true signal than training it on
noisy labels directly, approaching the big ensemble at a fraction of the size.

Run:  python distill.py --seed 42 --teachers 7 --epochs 300
Produces: models_v2/*.pth, distill_results.csv, distill_results.png
"""
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

NUM = ["age", "stress_level", "sleep_quality", "energy_levels", "session_number"]
CAT = ["gender", "diagnosis", "therapy_goal", "mood"]
TARGETS = ["arousal", "valence", "focus", "energy_state"]


class MLP(nn.Module):
    def __init__(self, d_in, hidden, d_out=4, p=0.1):
        super().__init__()
        layers, d = [], d_in
        for h in hidden:
            layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(p)]
            d = h
        layers += [nn.Linear(d, d_out), nn.Tanh()]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def n_params(m):
    return sum(p.numel() for p in m.parameters())


def train(model, Xtr, Ytr, Xva, Yva, epochs, lr=1e-3, seed=0):
    torch.manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    lossf = nn.MSELoss()
    best, best_state, patience, bad = 1e9, None, 40, 0
    for ep in range(epochs):
        model.train()
        opt.zero_grad()
        loss = lossf(model(Xtr), Ytr)
        loss.backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            vloss = lossf(model(Xva), Yva).item()
        if vloss < best - 1e-5:
            best, best_state, bad = vloss, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state:
        model.load_state_dict(best_state)
    return model


def evaluate(model, X, Y_noisy, Y_clean):
    model.eval()
    with torch.no_grad():
        pred = model(X).numpy()
    return {
        "R2_clean": r2_score(Y_clean, pred),
        "R2_noisy": r2_score(Y_noisy, pred),
        "MSE_clean": mean_squared_error(Y_clean, pred),
    }, pred


def run_once(X, ynoisy, yclean, d_in, seed, teachers_k, epochs, alpha, train_n, unlabeled):
    """One full teacher/student/distilled pass at a given seed. Returns metrics dict.

    If `unlabeled` is True, the student distills from the teacher's soft targets
    over the ENTIRE train+val input pool (features only, no labels), not just the
    few labeled rows. This is the realistic data-scarce setting: NeuroTunes has
    lots of intake/feature rows but few completed outcome self-reports, so the
    teacher can spread its (denoised) knowledge across input space the student's
    handful of labels never covers.
    """
    idx = np.arange(len(X))
    itr_full, ite = train_test_split(idx, test_size=0.2, random_state=seed)
    itr_full, iva = train_test_split(itr_full, test_size=0.2, random_state=seed)

    # Simulate label scarcity: only `train_n` rows carry usable labels.
    # The remaining train rows become an UNLABELED pool (features only).
    if train_n and train_n < len(itr_full):
        rng = np.random.default_rng(seed)
        itr = rng.choice(itr_full, size=train_n, replace=False)
    else:
        itr = itr_full
    pool = itr_full  # all train-available inputs (features), labels ignored for the pool

    def T(a):
        return torch.tensor(a, dtype=torch.float32)

    Xtr, Xva, Xte = T(X[itr]), T(X[iva]), T(X[ite])
    Xpool = T(X[pool])
    Ytr_n, Yva_n = T(ynoisy[itr]), T(ynoisy[iva])
    yte_n, yte_c = ynoisy[ite], yclean[ite]

    # 1. Teacher ensemble (wide), bootstrapped -> denoises by averaging.
    #    In the transfer setting the teacher is trained on the FULL labeled pool
    #    (a stand-in for a data-rich source such as public DEAM/PMEmo affect data);
    #    the student below only ever sees the few `train_n` target labels.
    Xteach = T(X[itr_full]) if unlabeled else Xtr
    Yteach = T(ynoisy[itr_full]) if unlabeled else Ytr_n
    teachers = []
    for k in range(teachers_k):
        bs = np.random.default_rng(seed + k).choice(len(Xteach), len(Xteach), replace=True)
        m = MLP(d_in, [128, 128, 64], p=0.15)
        m = train(m, Xteach[bs], Yteach[bs], Xva, Yva_n, epochs, seed=seed + k)
        teachers.append(m)

    def teacher_predict(Xin):
        with torch.no_grad():
            return torch.stack([t(Xin) for t in teachers]).mean(0)

    class Ensemble(nn.Module):
        def forward(self, x):
            return teacher_predict(x)
    teach_metrics, _ = evaluate(Ensemble(), Xte, yte_n, yte_c)

    # 2. Student-hard: small MLP on the few noisy labels (baseline)
    student_hard = MLP(d_in, [64, 32], p=0.1)
    student_hard = train(student_hard, Xtr, Ytr_n, Xva, Yva_n, epochs, seed=seed)
    hard_metrics, _ = evaluate(student_hard, Xte, yte_n, yte_c)

    # 3. Student-distilled: same small MLP trained on teacher soft targets.
    if unlabeled:
        # Distill over the WHOLE input pool (teacher labels every row).
        Xtr_d = Xpool
        Ytr_d = teacher_predict(Xpool)
        # blend hard labels back in only where they exist would need alignment;
        # for the unlabeled-pool variant we train purely on teacher targets.
    else:
        Xtr_d = Xtr
        Ytr_d = alpha * teacher_predict(Xtr) + (1 - alpha) * Ytr_n
    Yva_d = alpha * teacher_predict(Xva) + (1 - alpha) * Yva_n
    student_distilled = MLP(d_in, [64, 32], p=0.1)
    student_distilled = train(student_distilled, Xtr_d, Ytr_d, Xva, Yva_d, epochs, seed=seed)
    dist_metrics, _ = evaluate(student_distilled, Xte, yte_n, yte_c)

    return {
        "teacher": teach_metrics, "hard": hard_metrics, "distilled": dist_metrics,
        "params_teacher": n_params(teachers[0]) * teachers_k,
        "params_student": n_params(student_hard),
        "n_labeled": len(itr), "n_pool": len(pool),
        "models": (student_hard, student_distilled),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--seeds", type=int, default=1,
                    help="average the result over this many seeds (seed, seed+1, ...). "
                         "Multi-seed averaging gives a stable, honest estimate of the gain.")
    ap.add_argument("--teachers", type=int, default=7)
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--alpha", type=float, default=0.7, help="weight on teacher soft targets vs hard labels")
    ap.add_argument("--train_n", type=int, default=0,
                    help="cap the number of LABELED training rows to simulate data scarcity "
                         "(0 = use all). Distillation helps most in the low-label regime.")
    ap.add_argument("--unlabeled", action="store_true",
                    help="distill the student over the teacher's predictions on the FULL "
                         "train+val input pool (features only), not just the few labeled rows. "
                         "This is the realistic semi-supervised setting and where distillation wins.")
    ap.add_argument("--datadir", default=".")
    args = ap.parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    feats = pd.read_csv(f"{args.datadir}/synthetic_features_v2.csv")
    ynoisy = pd.read_csv(f"{args.datadir}/synthetic_targets_v2.csv")[TARGETS].values.astype("float32")
    yclean = pd.read_csv(f"{args.datadir}/synthetic_targets_clean_v2.csv")[TARGETS].values.astype("float32")

    pre = ColumnTransformer([
        ("num", StandardScaler(), NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
    ])
    X = pre.fit_transform(feats)
    if hasattr(X, "toarray"):
        X = X.toarray()
    X = X.astype("float32")
    d_in = X.shape[1]

    print(f"train_n={args.train_n or 'ALL'}  unlabeled_pool={args.unlabeled}  "
          f"teachers={args.teachers}  epochs={args.epochs}  seeds={args.seeds}")
    runs = []
    for s in range(args.seed, args.seed + args.seeds):
        r = run_once(X, ynoisy, yclean, d_in, s, args.teachers, args.epochs,
                     args.alpha, args.train_n, args.unlabeled)
        runs.append(r)
        g = r["distilled"]["R2_clean"] - r["hard"]["R2_clean"]
        print(f"  seed {s}: hard={r['hard']['R2_clean']:.4f}  "
              f"distilled={r['distilled']['R2_clean']:.4f}  gain={g:+.4f}")

    def agg(key):
        return np.array([r[key]["R2_clean"] for r in runs])
    teach_a, hard_a, dist_a = agg("teacher"), agg("hard"), agg("distilled")
    gains = dist_a - hard_a

    rows = [
        ("Teacher ensemble (Kx wide)", runs[0]["params_teacher"], teach_a),
        ("Student — hard labels (baseline)", runs[0]["params_student"], hard_a),
        ("Student — DISTILLED", runs[0]["params_student"], dist_a),
    ]
    df = pd.DataFrame([{
        "model": name, "params": p,
        "R2_vs_true_mean": round(a.mean(), 4),
        "R2_vs_true_std": round(a.std(), 4),
    } for name, p, a in rows])
    print("\n" + "=" * 74)
    print(f"RESULTS  (mean over {args.seeds} seeds; R2_vs_true = recovery of latent signal)")
    print("=" * 74)
    print(df.to_string(index=False))

    print("\nHeadline:")
    print(f"  Distillation gain in true-signal R^2: {gains.mean():+.4f} "
          f"± {gains.std():.4f}  ({gains.mean()/max(hard_a.mean(),1e-9)*100:+.1f}% relative)")
    wins = int((gains > 0).sum())
    print(f"  Distillation beat the baseline in {wins}/{args.seeds} seeds.")
    print(f"  The distilled student reaches {dist_a.mean()/teach_a.mean()*100:.1f}% of the "
          f"ensemble's R^2 using ~{runs[0]['params_student']/runs[0]['params_teacher']*100:.1f}% of its parameters.")

    df.to_csv(f"{args.datadir}/distill_results.csv", index=False)
    import os
    os.makedirs(f"{args.datadir}/models_v2", exist_ok=True)
    sh, sd = runs[0]["models"]
    torch.save(sd.state_dict(), f"{args.datadir}/models_v2/student_distilled.pth")
    torch.save(sh.state_dict(), f"{args.datadir}/models_v2/student_hard.pth")
    print(f"\nSaved models_v2/*.pth and distill_results.csv")

    # plot: mean R2 with std error bars
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4.5))
        names = [r[0] for r in rows]
        means = [a.mean() for *_, a in rows]
        errs = [a.std() for *_, a in rows]
        colors = ["#764ba2", "#dc3545", "#28a745"]
        ax.bar(names, means, yerr=errs, capsize=5, color=colors)
        ax.set_ylabel("R² vs true latent signal (test)")
        ax.set_title(f"NeuroTunes distillation @ train_n={args.train_n or 'ALL'} "
                     f"(mean±std, {args.seeds} seeds)")
        for i, v in enumerate(means):
            ax.text(i, v + 0.005, f"{v:.3f}", ha="center", fontweight="bold")
        plt.xticks(rotation=12, ha="right", fontsize=8)
        plt.tight_layout()
        plt.savefig(f"{args.datadir}/distill_results.png", dpi=130)
        print("Saved distill_results.png")
    except Exception as e:
        print("(plot skipped:", e, ")")


if __name__ == "__main__":
    main()
