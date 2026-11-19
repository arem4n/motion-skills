#!/usr/bin/env python3
"""Pone la pista de sonido sintético (MG.cue) a un MP4 que NO la tiene, p. ej. el render de Remotion (camino híbrido).

    python3 -I add_audio.py --scene proy/scene.html --video remotion.mp4 --out final.mp4 [--size 1080x1920] [--music pista.mp3]
    python3 -I add_audio.py --scene a/scene.html@0 --scene b/scene.html@7.6:10 --video combo.mp4 --out final.mp4   # varias escenas
                            [--music-gain -18] [--sfx-gain 0] [--loudness -14]

Hace lo mismo que render.py al final: lee las señales `MG.cue` de la escena, las sintetiza con make_sfx.py, masteriza a LUFS
objetivo con limitador y mezcla con `-c:v copy` (el video no se vuelve a codificar) y `-t` = fotogramas / fps. Así el audio de un
render de Remotion y el de `render.py` salen de la misma ruta de código.

Varias escenas (composición con <Series>): cada --scene es RUTA@INICIO[:LARGO] con INICIO en segundos desde el comienzo del video
(= fotograma de inicio de su secuencia / fps) y LARGO opcional si la escena está recortada (se descartan las señales posteriores).
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _scene_browser import open_scene  # noqa: E402
import render  # noqa: E402  (reutiliza _master y _qa: una sola ruta de audio)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", action="append", required=True, help="RUTA[@INICIO[:LARGO]] (repetible)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--music")
    ap.add_argument("--music-gain", type=float, default=-18.0)
    ap.add_argument("--sfx-gain", type=float, default=0.0)
    ap.add_argument("--sfx-source", choices=["auto", "synth", "samples"], default="auto", help="auto: muestras CC0 reales donde hay, sintético donde no")
    ap.add_argument("--loudness", default="-14")
    a = ap.parse_args()
    W, H = (int(v) for v in a.size.lower().split("x"))
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate",
                            "-of", "csv=p=0", a.video], capture_output=True, text=True, check=True).stdout.strip().split(",")
    num, den = probe[0].split("/") if "/" in probe[0] else (probe[0], "1")
    fps = float(num) / float(den)
    frames = int(probe[1])
    cues = []
    for spec in a.scene:
        path, _, rng = spec.partition("@")
        start, _, length = rng.partition(":")
        start = float(start) if start else 0.0
        with open_scene(path, W, H) as (page, info, errors):
            for c in info["cues"]:
                if length and c["t"] > float(length):
                    continue
                cues.append({**c, "t": c["t"] + start})
    cues.sort(key=lambda c: c["t"])
    dur = frames / fps
    if not cues and not a.music:
        raise SystemExit("la escena no registró MG.cue y no hay --music: no hay nada que mezclar")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="add-audio-"))
    try:
        (tmp / "cues.json").write_text(json.dumps(cues))
        wav = tmp / "sfx.wav"
        cmd = [sys.executable, "-I", str(HERE / "make_sfx.py"), "--cues", str(tmp / "cues.json"), "--duration", f"{dur:.3f}",
               "--out", str(wav), "--sfx-gain", str(a.sfx_gain), "--sfx-source", a.sfx_source]
        if a.music:
            cmd += ["--music", a.music, "--music-gain", str(a.music_gain)]
        subprocess.run(cmd, check=True)
        if a.loudness != "off":
            wav = render._master(wav, float(a.loudness), tmp)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video, "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{frames / fps:.4f}", "-movflags", "+faststart", a.out],
                       check=True)
        print(f"-> {a.out}  ({len(cues)} cues, {frames} fotogramas @ {fps:g} fps)")
        render._qa(a.out, a.loudness)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
