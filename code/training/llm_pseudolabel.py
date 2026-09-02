#!/usr/bin/env python3
"""
Stage 1 - LLM clinical pseudo-labeler for EmotionNet.

Replaces the hand-designed synthetic target with soft labels produced by an
open-source instruction-tuned LLM reasoning over each patient profile. The LLM
acts as a scalable clinical annotator: given a patient's assessment it estimates
the TARGET therapeutic affective state the generated music should embody on four
axes - arousal, valence, focus, calm - each in [-1, 1]. Those become the
distillation targets for the production EmotionNet (see distill_from_llm.py).

Runs identically on CPU (this sandbox), an RTX 2060 (GPU offload via
n_gpu_layers), or AWS - the only thing that changes is n_gpu_layers.

Deterministic: temperature 0, fixed seed. Writes incrementally so a crash never
loses completed rows (resumes by skipping patient_ids already in the out file).
"""
import argparse, csv, json, os, re, sys, time

SYS_PROMPT = (
    "You are a board-certified music therapist and clinical affective-science "
    "expert. For each patient you output the TARGET therapeutic affective state "
    "that a personalized therapeutic music piece should induce for that patient "
    "- NOT the patient's current mood. Reason about the diagnosis, therapy goal, "
    "and baseline scores, then give four numbers, each strictly in [-1, 1]:\n"
    "  arousal  : desired activation/energy of the music (-1 very calming, +1 very activating)\n"
    "  valence  : desired emotional tone (-1 dark/somber, +1 bright/positive)\n"
    "  focus    : desired cognitive engagement/attentional pull (-1 diffuse/background, +1 sharply engaging)\n"
    "  calm     : desired parasympathetic soothing (-1 alerting, +1 deeply soothing)\n"
    "Respond with ONLY a JSON object: "
    '{"arousal": x, "valence": x, "focus": x, "calm": x}. No prose.'
)

USER_TMPL = (
    "Patient profile:\n"
    "- age: {age}\n- gender: {gender}\n- diagnosis: {diagnosis}\n"
    "- therapy_goal: {therapy_goal}\n- stress_level (0-10): {stress_level}\n"
    "- sleep_quality (0-10): {sleep_quality}\n- energy_levels (0-10): {energy_levels}\n"
    "- current_mood: {mood}\n\n"
    "Give the target therapeutic [arousal, valence, focus, calm] as JSON."
)

FIELDS = ["age", "gender", "diagnosis", "therapy_goal",
          "stress_level", "sleep_quality", "energy_levels", "mood"]


def parse_vec(text):
    """Extract the 4 floats from the model's JSON reply, robust to stray prose."""
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    out = []
    for k in ("arousal", "valence", "focus", "calm"):
        try:
            v = float(d[k])
        except Exception:
            return None
        out.append(max(-1.0, min(1.0, v)))
    return out


def main():
    ap = argparse.ArgumentParser()
    _here = os.path.dirname(os.path.abspath(__file__))
    _ml = os.path.dirname(_here)
    ap.add_argument("--model", default="/home/ubuntu/models_llm/Qwen2.5-7B-Instruct-Q4_K_M.gguf")
    ap.add_argument("--data", default=os.path.join(_ml, "data", "patients_v3_first_session.csv"),
                    help="patient-level table (one row/patient). Default = the rich v3 "
                         "first-session subset produced by make_first_session_subset.py.")
    ap.add_argument("--out", default=os.path.join(_here, "llm_labels.csv"))
    ap.add_argument("--n_gpu_layers", type=int, default=0,
                    help="0 = CPU. On an RTX 2060 use ~20-33 to offload; -1 = all.")
    ap.add_argument("--n_threads", type=int, default=os.cpu_count())
    ap.add_argument("--n_ctx", type=int, default=2048)
    ap.add_argument("--limit", type=int, default=0, help="probe: only first N rows (0=all)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from llama_cpp import Llama
    t0 = time.time()
    llm = Llama(model_path=args.model, n_ctx=args.n_ctx, n_threads=args.n_threads,
                n_gpu_layers=args.n_gpu_layers, seed=args.seed, verbose=False)
    print(f"[load] model loaded in {time.time()-t0:.1f}s  n_gpu_layers={args.n_gpu_layers}", flush=True)

    rows = list(csv.DictReader(open(args.data)))
    if args.limit:
        rows = rows[:args.limit]

    done = set()
    if os.path.exists(args.out):
        done = {r["patient_id"] for r in csv.DictReader(open(args.out))}
    write_header = not os.path.exists(args.out)
    fout = open(args.out, "a", newline="")
    w = csv.writer(fout)
    if write_header:
        w.writerow(["patient_id", "arousal", "valence", "focus", "calm"])

    n_ok = n_fail = 0
    t_start = time.time()
    for i, r in enumerate(rows):
        if r["patient_id"] in done:
            continue
        msgs = [{"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content": USER_TMPL.format(**{k: r.get(k, "") for k in FIELDS})}]
        resp = llm.create_chat_completion(messages=msgs, temperature=0.0,
                                          max_tokens=120, seed=args.seed)
        txt = resp["choices"][0]["message"]["content"]
        vec = parse_vec(txt)
        if vec is None:  # one deterministic retry with a nudge
            msgs.append({"role": "assistant", "content": txt})
            msgs.append({"role": "user", "content": 'Output ONLY the JSON object with the 4 keys.'})
            resp = llm.create_chat_completion(messages=msgs, temperature=0.0, max_tokens=80, seed=args.seed)
            vec = parse_vec(resp["choices"][0]["message"]["content"])
        if vec is None:
            n_fail += 1
            continue
        w.writerow([r["patient_id"], *[f"{x:.4f}" for x in vec]])
        fout.flush()
        n_ok += 1
        if n_ok % 25 == 0 or (args.limit and n_ok <= 10):
            rate = n_ok / (time.time() - t_start)
            print(f"[{n_ok}] {r['patient_id']} -> {vec}  ({rate:.2f} rows/s)", flush=True)

    dt = time.time() - t_start
    print(f"\n[done] ok={n_ok} fail={n_fail} in {dt:.1f}s  "
          f"({n_ok/max(dt,1e-9):.3f} rows/s, {dt/max(n_ok,1):.2f} s/row)", flush=True)
    fout.close()


if __name__ == "__main__":
    main()
