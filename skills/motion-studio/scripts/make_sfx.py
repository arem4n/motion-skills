#!/usr/bin/env python3
"""Sound-design track for a scene from its cue list: real CC0 samples (assets/sfx, plus MOTION_STUDIO_SFX_DIR) where a cue has them, synthesized otherwise. No network.

    python3 -I make_sfx.py --cues cues.json --duration 6.4 --out audio.wav [--music bed.mp3 --music-gain -18] [--master -3]

cues.json: [{"name": "hit", "t": 3.5, "gain": 0.9, "dur": 0.8, "dir": "up"}, ...]   (the scene writes them with MG.cue)
Cue names with a real sample: hit (heavy soft impact), thud (short medium impact), pop (drop), tick (click),
step (footstep on concrete), shimmer (bell). Synthesized: whoosh (filtered noise sweep; dir "up"|"down"),
riser (rising noise, ends at t+dur), sub (low swell) — and any cue whose sample is missing.
--sfx-source auto|samples|synth: auto = samples where available (default), samples = fail if one is missing, synth = all synthesized.
Each cue is placed so its *peak* lands at `t` (whoosh and riser end/peak at t), because that is the moment the picture hits.
"""
import argparse
import os
import json
import subprocess
import tempfile
import wave

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy missing for this interpreter (-I hides user packages). Run setup.py once and use the python it prints (setup.py --print).")
from scipy import signal

SR = 44100


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env_ad(n, attack, decay_tau):
    a = np.minimum(1, np.arange(n) / max(1, attack * SR))
    return a * np.exp(-np.arange(n) / (decay_tau * SR))


def noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def swept_band(x, f0, f1, q=1.2):
    """Band-pass noise whose centre frequency glides f0 -> f1 (chunked, state carried across chunks)."""
    out = np.zeros_like(x)
    chunk = 512
    zi = None
    for i in range(0, len(x), chunk):
        f = f0 * (f1 / f0) ** (i / max(1, len(x)))
        lo, hi = max(40, f / (1 + 1 / q)), min(SR / 2 - 100, f * (1 + 1 / q))
        sos = signal.butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, x[i:i + chunk], zi=zi)
        out[i:i + chunk] = y
    return out


def hit(o):
    d = o.get("dur", 0.9); t = t_axis(d); n = len(t)
    f = 45 + 70 * np.exp(-t / 0.07)                       # pitch drop 115 -> 45 Hz
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.28)
    body = signal.sosfilt(signal.butter(2, 900, "low", fs=SR, output="sos"), noise(n, 1)) * env_ad(n, 0.001, 0.05) * 0.5
    click = signal.sosfilt(signal.butter(2, 2500, "high", fs=SR, output="sos"), noise(n, 2)) * env_ad(n, 0.0005, 0.012) * 0.35
    return sub * 1.0 + body + click, 0.0                    # peak at start


def whoosh(o):
    d = o.get("dur", 0.6); n = int(d * SR)
    up = o.get("dir", "up") == "up"
    x = swept_band(noise(n, 3), 350 if up else 4500, 4500 if up else 350, 1.0)
    shape = np.sin(np.pi * (np.arange(n) / n) ** 1.6) ** 2            # swell, peak ~60% of the way
    return x * shape * 0.9 / (np.abs(x).max() + 1e-9), d * 0.62     # peak offset from start


def pop(o):
    d = 0.22; t = t_axis(d)
    f = 480 + 520 * (1 - np.exp(-t / 0.02))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.002, 0.045) * 0.8, 0.0


def tick(o):
    d = 0.06; t = t_axis(d); n = len(t)
    c = signal.sosfilt(signal.butter(2, 2200, "high", fs=SR, output="sos"), noise(n, 4)) * env_ad(n, 0.0003, 0.004)
    return (c * 0.6 + np.sin(2 * np.pi * 1900 * t) * env_ad(n, 0.0005, 0.008) * 0.4), 0.0


def riser(o):
    d = o.get("dur", 1.2); n = int(d * SR); t = t_axis(d)
    x = swept_band(noise(n, 5), 300, 6500, 1.4)
    f = 200 * (6 ** (t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    amp = (t / d) ** 2.2
    y = (x / (np.abs(x).max() + 1e-9) * 0.8 + tone) * amp
    y[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return y, d                                              # peak at the end


def sub(o):
    d = o.get("dur", 1.4); t = t_axis(d)
    return np.sin(2 * np.pi * 48 * t) * np.sin(np.pi * np.minimum(1, t / d)) ** 0.7 * 0.9, d * 0.3


def shimmer(o):
    d = o.get("dur", 1.6); t = t_axis(d); y = np.zeros_like(t)
    for k, f in enumerate([1318, 1760, 2093, 2637, 3136]):
        y += np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * (4 + k) * t) / (6 + k)) * np.exp(-t / (0.5 + 0.1 * k)) / (k + 1.5)
    y *= np.minimum(1, t / 0.01)
    return y * 0.35, 0.0


GEN = {"hit": hit, "whoosh": whoosh, "pop": pop, "tick": tick, "riser": riser, "sub": sub, "shimmer": shimmer,
       "thud": lambda o: hit(dict(o, dur=o.get("dur", 0.35))), "step": tick}   # thud/step: sintético de respaldo


# ---- muestras reales: assets/sfx (CC0, viaja con el skill) + MOTION_STUDIO_SFX_DIR (local, nunca se empaqueta) ----
SKILL_SFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sfx")


def load_library():
    """{cue: [entry...]} de cada index.json. La carpeta local va primero: sus sonidos ganan para esa señal."""
    lib = {}
    dirs = [d for d in (os.environ.get("MOTION_STUDIO_SFX_DIR"), SKILL_SFX) if d]
    for d in dirs:
        p = os.path.join(d, "index.json")
        if not os.path.exists(p):
            continue
        for cue, entries in json.load(open(p)).get("cues", {}).items():
            if cue in lib or not entries:
                continue
            lib[cue] = [dict(e, path=os.path.join(d, e["file"])) for e in entries]
    return lib


_decoded = {}


def decode(path):
    if path not in _decoded:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(float) / 32768
        _decoded[path] = x * (0.9 / (np.abs(x).max() + 1e-9))      # todas al mismo pico; el balance lo dan gain_db y la señal
    return _decoded[path]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--music")
    ap.add_argument("--music-gain", type=float, default=-18.0, help="dB")
    ap.add_argument("--master", type=float, default=-3.0, help="peak ceiling in dB")
    ap.add_argument("--sfx-gain", type=float, default=0.0, help="dB applied to every cue")
    ap.add_argument("--sfx-source", choices=["auto", "synth", "samples"], default="auto",
                    help="auto: muestra real si hay para esa señal, si no sintético; synth: todo sintético; samples: falla si falta alguna")
    a = ap.parse_args()

    cues = sorted(json.load(open(a.cues)), key=lambda c: c["t"])
    lib = {} if a.sfx_source == "synth" else load_library()
    total = int((a.duration + 1.0) * SR)
    mix = np.zeros(total)
    used, seen = {"muestra": 0, "sintético": 0}, {}
    for c in cues:
        name = c["name"]
        if name in lib:                                   # variante rotando por aparición: determinista y sin repetir seguido
            k = seen.get(name, 0); seen[name] = k + 1
            e = lib[name][k % len(lib[name])]
            y, peak = decode(e["path"]) * 10 ** (e.get("gain_db", 0) / 20), e.get("peak", 0.0)
            used["muestra"] += 1
        else:
            if a.sfx_source == "samples":
                raise SystemExit(f"no sample for cue '{name}' (use --sfx-source auto)")
            gen = GEN.get(name)
            if not gen:
                print("unknown cue", name); continue
            y, peak = gen(c)
            used["sintético"] += 1
        start = int((c["t"] - peak) * SR)
        g = c.get("gain", 1.0) * 10 ** (a.sfx_gain / 20)
        s0, s1 = max(0, start), min(total, start + len(y))
        if s1 > s0:
            mix[s0:s1] += y[s0 - start:s1 - start] * g
    if a.music:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.music, "-ac", "1", "-ar", str(SR), tmp.name], check=True)
            with wave.open(tmp.name) as w:
                m = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        m = np.tile(m, int(np.ceil(total / len(m))))[:total] * 10 ** (a.music_gain / 20)
        fade = int(1.0 * SR); end = int(a.duration * SR)
        m[end - fade:end] *= np.linspace(1, 0, fade); m[end:] = 0
        mix += m
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)                 # gentle soft clip instead of hard clipping
    peak = np.abs(mix).max()
    ceiling = 10 ** (a.master / 20)
    if peak > 1e-6:
        mix *= min(1.0, ceiling / peak) if peak > ceiling else 1.0
    mix = mix[: int((a.duration) * SR)]
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())
    print(f"{len(cues)} cues ({used['muestra']} muestras reales, {used['sintético']} sintéticas) -> {a.out} ({a.duration:.2f}s, peak {20*np.log10(max(peak,1e-9)):.1f} dBFS before ceiling)")


if __name__ == "__main__":
    main()
