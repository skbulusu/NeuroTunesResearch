#!/usr/bin/env python3
"""
ab_generate.py — A/B the production generator under three configs and analyse
the resulting MIDIs (tempo / mode / key correctness + real-music sanity).

Configs, all for the SAME patients with the SAME RNG seed so the only
difference is where the affective targets come from:

  A) v1 weights, UNWIRED  -> therapeutic_targets = old constants (0.5,0,0,0)
                             == current production behaviour
  B) v2 weights, UNWIRED  -> same old constants (proves retraining ALONE
                             changes nothing, because the model is disconnected)
  C) v2 weights, WIRED    -> therapeutic_targets = model state_vector
                             (the fix in app.py: model now shapes the music)

Requires the key-hash fix (already in music_generator.py) so the labelled key
matches the audible tonic.
"""
import os
import sys
import random
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_MLSERVER = os.path.dirname(_HERE)
sys.path.insert(0, _MLSERVER)

import mido  # noqa: E402
import music_generator as mgmod  # noqa: E402

PATIENTS = [
    dict(age=24, gender="Female", diagnosis="Anxiety", therapy_goal="Relaxation",
         stress_level=8, sleep_quality=3, energy_levels=3, mood="Stressed", session_number=1),
    dict(age=29, gender="Female", diagnosis="Healthy", therapy_goal="Cognitive Enhancement",
         stress_level=3, sleep_quality=7, energy_levels=7, mood="Focused", session_number=1),
]

# scale intervals mirror music_generator.MusicGenerator.scales
SCALES = {
    'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10],
    'pentatonic': [0, 2, 4, 7, 9], 'blues': [0, 3, 5, 6, 7, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10], 'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
}


def load_model(weights_dir):
    os.environ["WEIGHTS_PATH"] = weights_dir
    for m in list(sys.modules):
        if m == "neurotunes_model":
            del sys.modules[m]
    import neurotunes_model
    return neurotunes_model.NeuroTunesModel()


def analyse_midi(path, labeled_key, labeled_mode):
    """Return (bpm, n_notes, tonic_pc, pct_notes_in_scale_at_labeled_key)."""
    mid = mido.MidiFile(path)
    bpm = None
    pitches = []
    for tr in mid.tracks:
        for msg in tr:
            if msg.type == "set_tempo" and bpm is None:
                bpm = round(mido.tempo2bpm(msg.tempo))
            if msg.type == "note_on" and msg.velocity > 0:
                pitches.append(msg.note)
    key_pc = mgmod.key_pitch_class(labeled_key)
    scale = set(SCALES.get(labeled_mode, SCALES['major']))
    if pitches:
        in_scale = sum(1 for p in pitches if ((p - key_pc) % 12) in scale)
        pct = 100.0 * in_scale / len(pitches)
    else:
        pct = 0.0
    return bpm, len(pitches), key_pc, round(pct, 1)


def run(tag, model, patient, wired, outdir):
    # deterministic RNG so only the targets differ between configs
    random.seed(1234)
    np.random.seed(1234)
    sv = model.predict(None, original_patient_data={k: patient[k] for k in
                       ['age', 'gender', 'diagnosis', 'therapy_goal',
                        'stress_level', 'sleep_quality', 'energy_levels', 'mood']})
    sv = (list(np.asarray(sv).ravel()) + [0, 0, 0, 0])[:4]
    if wired:
        tt = {'arousal': float(sv[0]), 'valence': float(sv[1]),
              'focus': float(sv[2]), 'energy_state': float(sv[0])}
    else:
        tt = {'arousal': 0.5, 'valence': 0.0, 'focus': 0.0, 'energy_state': 0.0}
    up = {'age': patient['age'], 'diagnosis': patient['diagnosis'],
          'severity': 'moderate', 'session_number': patient['session_number']}

    gen = mgmod.MusicGenerator()
    gen.output_dir = outdir  # in case it's used
    tracks = gen.generate_therapeutic_music(tt, up, num_tracks=3)
    rows = []
    for t in tracks:
        mf = t.get('midi_file')
        if mf and os.path.exists(mf):
            bpm, n, tonic, pct = analyse_midi(mf, t['key'], t['mode'])
            rows.append((t['track_id'].split('_')[2], t['tempo'], bpm, t['key'],
                         tonic, t['mode'], round(t.get('clinical_complexity', 0), 2), n, pct))
    print(f"\n--- {tag} | patient={patient['diagnosis']}/{patient['therapy_goal']} "
          f"state={np.round(sv,2)} ---")
    print(f"    targets used: {({k: round(v,2) for k,v in tt.items()})}")
    print(f"    {'goal':<12}{'tempoLbl':>9}{'tempoMIDI':>10}{'key':>5}{'pc':>4}"
          f"{'mode':>12}{'cplx':>6}{'notes':>7}{'in-key%':>9}")
    for r in rows:
        print(f"    {r[0]:<12}{r[1]:>9}{r[2]:>10}{r[3]:>5}{r[4]:>4}{r[5]:>12}"
              f"{r[6]:>6}{r[7]:>7}{r[8]:>9}")
    return rows


def main():
    v1 = os.path.join(_MLSERVER, "models")
    v2 = os.path.join(_HERE, "out_v2")
    outdir = os.path.join(_HERE, "ab_out")
    os.makedirs(outdir, exist_ok=True)
    os.chdir(_MLSERVER)  # so generator's relative output/ dir resolves

    m1 = load_model(v1)
    m2 = load_model(v2)

    for p in PATIENTS:
        run("A) v1 weights UNWIRED (current prod)", m1, p, wired=False, outdir=outdir)
        run("B) v2 weights UNWIRED (retrain alone)", m2, p, wired=False, outdir=outdir)
        run("C) v2 weights WIRED   (the fix)", m2, p, wired=True, outdir=outdir)

    print("\nNOTE: in-key% = share of note-ons whose pitch class lies in the "
          "labelled mode rooted at the labelled key (key-hash fix verification).")


if __name__ == "__main__":
    main()
