#!/usr/bin/env python3
"""Transcribe un audio EN LOCAL (faster-whisper) a subtítulos por palabra en el formato `Caption` de Remotion.

    $PY -I transcribe.py --audio voz.mp3 --out captions.json [--lang es] [--model small]

Necesita faster-whisper, que es opcional: `python3 setup.py --with-whisper` lo instala en el venv del skill (una vez).
Nada sale de la máquina si el modelo ya está en ~/.cache/huggingface (small y base lo están); si no, faster-whisper lo baja una vez
desde Hugging Face (solo se descarga, no se sube nada). HF_HUB_OFFLINE=1 lo impide.

--snap (por defecto) ajusta cada palabra a los silencios REALES del audio (ffmpeg silencedetect, -35 dB, >= 0,25 s): Whisper estira
palabras sobre las pausas (medido: "Suma" salía 0,6 s antes de pronunciarse) y el subtítulo se encendería antes de la voz. Con --no-snap
quedan los tiempos crudos del modelo.

Salida: JSON `[{text, startMs, endMs, timestampMs, confidence}]`, una entrada por palabra; `text` lleva el espacio inicial
(convención de @remotion/captions: así createTikTokStyleCaptions respeta los espacios). Se imprime un resumen con las palabras
de menor confianza: revísalas contra el guion antes de confiar en el subtítulo.
"""
import argparse
import json
import re
import subprocess
import sys

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise SystemExit("este python no tiene faster-whisper. Instálalo en el venv del skill:  python3 setup.py --with-whisper")


def silences(audio, db=-35, dur=0.25):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", audio, "-af", f"silencedetect=noise={db}dB:d={dur}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(st, en))


def snap(caps, sil, min_dur=0.1):
    """Mueve inicios/finales que caen dentro de un silencio real. Devuelve cuántas palabras cambió."""
    changed = 0
    for c in caps:
        s0, s1 = c["startMs"] / 1000, c["endMs"] / 1000
        o0, o1 = s0, s1
        for a, b in sil:
            if a <= s0 < b or (s0 < a and s1 > b):      # empieza dentro de la pausa, o la abarca entera: la palabra viene DESPUÉS
                s0 = b
            elif a < s1 <= b:                            # termina dentro de la pausa: acábala donde empieza
                s1 = a
        if s1 - s0 < min_dur:
            s1 = s0 + min_dur
        if (s0, s1) != (o0, o1):
            changed += 1
            c["startMs"], c["endMs"] = round(s0 * 1000), round(s1 * 1000)
            c["timestampMs"] = round((s0 + s1) / 2 * 1000)
    for prev, cur in zip(caps, caps[1:]):                # sin solapes
        if prev["endMs"] > cur["startMs"]:
            prev["endMs"] = max(prev["startMs"] + 50, cur["startMs"])
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="es")
    ap.add_argument("--model", default="small", help="tiny|base|small|medium (small: buen equilibrio en CPU)")
    ap.add_argument("--no-snap", action="store_true", help="no ajustar las palabras a los silencios reales")
    ap.add_argument("--prompt", help="texto inicial con nombres propios o jerga para sesgar el reconocimiento")
    a = ap.parse_args()
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    # Decode with ffmpeg (16 kHz mono float32) instead of letting faster-whisper open the file through PyAV: the PyAV wheel that
    # installs on recent Pythons can be too old for faster-whisper ("open() got an unexpected keyword argument 'metadata_errors'").
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.audio, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)
    segs, info = model.transcribe(audio, language=a.lang, word_timestamps=True, vad_filter=True, initial_prompt=a.prompt)
    caps = []
    for s in segs:
        for w in s.words or []:
            t = w.word if w.word.startswith(" ") else " " + w.word
            caps.append({"text": t, "startMs": round(w.start * 1000), "endMs": round(w.end * 1000),
                         "timestampMs": round((w.start + w.end) / 2 * 1000), "confidence": round(float(w.probability), 3)})
    if not a.no_snap:
        n = snap(caps, silences(a.audio))
        print(f"ajustadas a silencios reales: {n} de {len(caps)} palabras")
    json.dump(caps, open(a.out, "w"), ensure_ascii=False, indent=1)
    low = sorted(caps, key=lambda c: c["confidence"])[:5]
    print(f"{len(caps)} palabras, {caps[-1]['endMs'] / 1000:.1f} s de {info.duration:.1f} s ({a.model}, idioma {info.language}) -> {a.out}")
    print("menor confianza (revisa):", ", ".join(f"{c['text'].strip()}={c['confidence']}" for c in low))


if __name__ == "__main__":
    sys.exit(main())
