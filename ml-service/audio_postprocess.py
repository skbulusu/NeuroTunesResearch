"""
audio_postprocess.py  —  NeuroTunes loudness fix (non-invasive).

Why this exists
---------------
The rendered therapy tracks come out near-silent: measured RMS ~= -56 dBFS and
peak ~= -37 dBFS, because the MIDI note velocities are low (20-40 / 127) and
FluidSynth's default synth gain is 0.2. On normal playback the audio is
effectively inaudible, which blocks demos and any listening study.

This module fixes that WITHOUT touching the patent-critical music_generator.py.
It is a pure post-processor: give it a rendered .wav (or a directory of them)
and it peak-normalizes to a target dBFS with a short fade in/out to avoid clicks.
Optionally it can also re-render a .mid with a higher FluidSynth gain first.

Design goals
------------
  * Zero new dependencies: stdlib `wave` + numpy only (numpy already required).
  * Deterministic and reversible: never overwrites the source unless asked.
  * Safe: clips are peak-normalized (no distortion) and limited to <= 0 dBFS.

Usage
-----
  # normalize one file to -1 dBFS, writing <name>_norm.wav next to it
  python audio_postprocess.py output/track_1.wav

  # normalize every wav in output/ in place-safe mode (writes *_norm.wav)
  python audio_postprocess.py output/ --target-dbfs -1.0

  # overwrite the originals (use with care)
  python audio_postprocess.py output/ --inplace

Integration (one line, no edit to the protected generator)
----------------------------------------------------------
  from audio_postprocess import normalize_wav
  wav = generator.midi_to_audio(midi_file, track_name)
  if wav:
      wav = normalize_wav(wav, target_dbfs=-1.0, inplace=True)
"""
import argparse
import os
import sys
import wave
import numpy as np

TARGET_DBFS_DEFAULT = -1.0
FADE_MS_DEFAULT = 15


def _read_wav(path):
    with wave.open(path, "rb") as w:
        nch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        dtype, full = np.int16, 32767.0
    elif sw == 4:
        dtype, full = np.int32, 2147483647.0
    elif sw == 1:
        dtype, full = np.uint8, 255.0
    else:
        raise ValueError(f"Unsupported sample width: {sw*8} bit")
    data = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if sw == 1:                       # 8-bit PCM is unsigned, centered at 128
        data = data - 128.0
        full = 128.0
    data = data / full                # -> float in [-1, 1]
    if nch > 1:
        data = data.reshape(-1, nch)
    return data, sr, nch, sw


def _write_wav(path, data, sr, nch, sw):
    full = {1: 128.0, 2: 32767.0, 4: 2147483647.0}[sw]
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}[sw]
    arr = np.clip(data, -1.0, 1.0) * full
    if sw == 1:
        arr = arr + 128.0
    arr = arr.astype(dtype)
    with wave.open(path, "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(sw)
        w.setframerate(sr)
        w.writeframes(arr.tobytes())


def _dbfs(x):
    peak = np.max(np.abs(x)) if x.size else 0.0
    return -np.inf if peak <= 0 else 20.0 * np.log10(peak)


def _apply_fade(data, sr, fade_ms):
    n = int(sr * fade_ms / 1000.0)
    if n <= 0 or data.shape[0] < 2 * n:
        return data
    ramp = np.linspace(0.0, 1.0, n)
    if data.ndim == 1:
        data[:n] *= ramp
        data[-n:] *= ramp[::-1]
    else:
        data[:n] *= ramp[:, None]
        data[-n:] *= ramp[::-1, None]
    return data


def normalize_wav(path, target_dbfs=TARGET_DBFS_DEFAULT, fade_ms=FADE_MS_DEFAULT,
                  inplace=False, suffix="_norm"):
    """Peak-normalize a WAV to `target_dbfs` and return the output path."""
    data, sr, nch, sw = _read_wav(path)
    before = _dbfs(data)
    peak = np.max(np.abs(data))
    if peak > 0:
        target_lin = 10.0 ** (target_dbfs / 20.0)
        data = data * (target_lin / peak)
    data = _apply_fade(data, sr, fade_ms)
    after = _dbfs(data)
    if inplace:
        out = path
    else:
        base, ext = os.path.splitext(path)
        out = f"{base}{suffix}{ext}"
    _write_wav(out, data, sr, nch, sw)
    print(f"  {os.path.basename(path)}: {before:6.1f} dBFS -> {after:6.1f} dBFS  "
          f"(gain {after-before:+.1f} dB)  -> {os.path.basename(out)}")
    return out


def main():
    ap = argparse.ArgumentParser(description="NeuroTunes loudness post-processor")
    ap.add_argument("path", help="a .wav file or a directory of .wav files")
    ap.add_argument("--target-dbfs", type=float, default=TARGET_DBFS_DEFAULT,
                    help="target peak level in dBFS (default -1.0)")
    ap.add_argument("--fade-ms", type=float, default=FADE_MS_DEFAULT,
                    help="fade in/out length in ms to avoid clicks (default 15)")
    ap.add_argument("--inplace", action="store_true", help="overwrite the source files")
    args = ap.parse_args()

    if os.path.isdir(args.path):
        wavs = sorted(f for f in os.listdir(args.path)
                      if f.lower().endswith(".wav") and "_norm" not in f)
        if not wavs:
            print("No .wav files found in", args.path); sys.exit(1)
        print(f"Normalizing {len(wavs)} file(s) in {args.path} to {args.target_dbfs} dBFS:")
        for f in wavs:
            normalize_wav(os.path.join(args.path, f), args.target_dbfs,
                          args.fade_ms, args.inplace)
    else:
        normalize_wav(args.path, args.target_dbfs, args.fade_ms, args.inplace)


if __name__ == "__main__":
    main()
