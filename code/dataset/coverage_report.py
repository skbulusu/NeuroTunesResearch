"""
coverage_report.py  (QA / representativeness)
=============================================
Prints a full coverage + representativeness report for the v3 datasets so we
can answer, with real numbers, the question: "is this dataset massive and
representative enough?"

Reports, for both the balanced and natural-prevalence sets:
  - row counts
  - condition coverage (all 14?)
  - valence/arousal quadrant balance (the therapeutic-target plane)
  - arousal-axis balance (low vs high) -- the axis we DO want balanced
  - severity / comorbidity / medication_state / time_of_day distributions
  - gender + age spread
  - label-confidence stats (mean, %flagged for human review)

Run:
    source /home/ubuntu/m2e_env/bin/activate
    cd code/dataset
    python coverage_report.py
"""
import os
import numpy as np
import pandas as pd

import clinical_priors as cp

HERE = os.path.dirname(os.path.abspath(__file__))


def quadrant(v, a):
    if v >= 0 and a >= 0:
        return "happy/excited (v+ a+)"
    if v >= 0 and a < 0:
        return "calm/content (v+ a-)"
    if v < 0 and a >= 0:
        return "anxious/tense (v- a+)"
    return "sad/low (v- a-)"


def pct(n, d):
    return f"{100.0 * n / d:5.1f}%" if d else "  n/a"


def report(df, name):
    n = len(df)
    lines = []
    lines.append(f"\n{'='*66}\n{name}  (n={n})\n{'='*66}")

    # --- condition coverage ---
    conds = df["diagnosis"].value_counts()
    expected = set(cp.CONDITIONS.keys())
    present = set(conds.index)
    lines.append(f"\nConditions covered: {len(present)}/{len(expected)}")
    missing = expected - present
    if missing:
        lines.append(f"  !! MISSING: {sorted(missing)}")
    for c, cnt in conds.items():
        lines.append(f"  {c:<16} {cnt:>5}  ({pct(cnt, n)})")

    # --- VA quadrant balance (targets) ---
    q = df.apply(lambda r: quadrant(r["valence"], r["arousal"]), axis=1)
    qc = q.value_counts()
    lines.append("\nTarget valence/arousal quadrants:")
    for name_q in ["happy/excited (v+ a+)", "calm/content (v+ a-)",
                   "anxious/tense (v- a+)", "sad/low (v- a-)"]:
        lines.append(f"  {name_q:<24} {qc.get(name_q,0):>5}  ({pct(qc.get(name_q,0), n)})")
    neg_v = int((df["valence"] < 0).sum())
    lines.append(f"  --> negative-valence (iso-principle match targets): {pct(neg_v, n)}")

    # --- arousal-axis balance (the axis we DO balance) ---
    hi = int((df["arousal"] >= 0).sum())
    lines.append(f"\nArousal axis: high/activating {pct(hi,n)}  |  low/calming {pct(n-hi,n)}")

    # --- categorical axes ---
    for col in ["severity", "comorbidity", "medication_state", "time_of_day", "gender"]:
        if col not in df.columns:
            continue
        vc = df[col].value_counts()
        lines.append(f"\n{col}:")
        for k, v in vc.items():
            kd = "none" if (isinstance(k, float) and np.isnan(k)) else k
            lines.append(f"  {str(kd):<16} {v:>5}  ({pct(v,n)})")

    # --- RICH patient-realism axes (only present in --rich datasets) ---
    rich_cat = [c for c in cp.RICH_CATEG if c in df.columns]
    rich_num = [c for c in cp.RICH_NUMERIC if c in df.columns]
    if rich_cat or rich_num:
        lines.append(f"\n{'-'*66}\nRICH PATIENT-REALISM AXES\n{'-'*66}")
        # distinct patients & sessions-per-patient (patient_id = <pid>_s<NN>)
        if df["patient_id"].astype(str).str.contains("_s").any():
            base_pid = df["patient_id"].astype(str).str.rsplit("_s", n=1).str[0]
            spp = base_pid.value_counts()
            lines.append(f"\ndistinct patients: {spp.size}  |  sessions/patient: "
                         f"min={spp.min()} max={spp.max()} mean={spp.mean():.1f}")
        for col in rich_cat:
            vc = df[col].value_counts()
            lines.append(f"\n{col}:")
            for k, v in vc.items():
                lines.append(f"  {str(k):<16} {v:>5}  ({pct(v,n)})")
        for col in rich_num:
            s = df[col]
            lines.append(f"\n{col}: min={s.min():g} max={s.max():g} "
                         f"mean={s.mean():.2f} sd={s.std():.2f}")
        if "life_event" in df.columns:
            le = int((df["life_event"] >= 1).sum())
            lines.append(f"\nsessions with an acute life event: {le}  ({pct(le,n)})")

    # --- age ---
    lines.append(f"\nage: min={df['age'].min()} max={df['age'].max()} "
                 f"mean={df['age'].mean():.1f} sd={df['age'].std():.1f}")

    # --- confidence ---
    if "confidence" in df.columns:
        c = df["confidence"]
        flagged = int((c < 0.5).sum())
        lines.append(f"\nlabel confidence: mean={c.mean():.3f} min={c.min():.3f} "
                     f"max={c.max():.3f}")
        lines.append(f"  flagged for human review (conf<0.5): {flagged}  ({pct(flagged,n)})")
        lines.append(f"  disagreement: mean={df['disagreement'].mean():.4f} "
                     f"max={df['disagreement'].max():.4f}")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE,
                    help="directory holding dataset_*_v3.csv (default: script dir)")
    args = ap.parse_args()
    bal = pd.read_csv(os.path.join(args.dir, "dataset_balanced_v3.csv"))
    nat = pd.read_csv(os.path.join(args.dir, "dataset_natural_v3.csv"))
    out = []
    out.append(report(bal, "BALANCED SET (training)"))
    out.append(report(nat, "NATURAL-PREVALENCE SET (honest eval)"))
    total = len(bal) + len(nat)
    out.append(f"\n{'='*66}\nTOTAL ROWS ACROSS BOTH SETS: {total}\n{'='*66}")
    text = "\n".join(out)
    print(text)
    with open(os.path.join(args.dir, "coverage_report.txt"), "w") as f:
        f.write(text + "\n")
    print(f"\n[written] {os.path.join(args.dir, 'coverage_report.txt')}")


if __name__ == "__main__":
    main()
