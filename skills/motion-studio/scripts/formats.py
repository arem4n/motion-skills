#!/usr/bin/env python3
"""Una misma escena en varios formatos: valida cada uno, arma una lámina para compararlos y renderiza.

    $PY -I formats.py --scene proy/scene.html --out-dir proy/out [--formats 9x16,16x9,1x1,4x5] [--name pieza]
                      [--at 3.2] [--only-sheet] [--no-validate] [-- --shutter 8 --music bed.mp3 ...]

La escena tiene que estar diseñada en relativo (S.w, S.h, u = min(S.w,S.h)/1080, `portrait = S.h > S.w`): el formato
llega como ?w=&h= y las plantillas lo leen solas. Lo que va después de `--` se pasa tal cual a render.py.
Sale: <out-dir>/<name>-<fmt>.mp4, hoja y reporte del validador por formato, y <name>-formatos.png (un cuadro de cada uno).
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SIZES = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    argv = sys.argv[1:]
    passthru = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--formats", default="9x16,16x9,1x1,4x5", help="de " + ", ".join(SIZES) + " o WxH")
    ap.add_argument("--name", help="prefijo de los archivos (por defecto, la carpeta de la escena)")
    ap.add_argument("--at", type=float, help="segundo del cuadro para la lámina (por defecto, 0,6 s antes del final)")
    ap.add_argument("--only-sheet", action="store_true", help="solo valida y arma la lámina, sin renderizar los videos")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)

    scene = pathlib.Path(a.scene).resolve(); out = pathlib.Path(a.out_dir).resolve(); out.mkdir(parents=True, exist_ok=True)
    name = a.name or scene.parent.name
    py = sys.executable
    fmts = []
    for f in a.formats.split(","):
        f = f.strip()
        w, h = SIZES.get(f) or tuple(int(v) for v in f.lower().split("x"))
        fmts.append((f.replace(":", "x"), w, h))

    rows, stills, dur = [], [], None
    for f, w, h in fmts:
        size = f"{w}x{h}"; status = "sin validar"
        if not a.no_validate:
            rep = out / f"{name}-{f}-reporte.json"
            code, log = run([py, "-I", str(HERE / "validate.py"), "--scene", str(scene), "--size", size,
                             "--sheet", str(out / f"{name}-{f}-hoja.png"), "--report", str(rep)])
            fails = [l for l in log.splitlines() if l.startswith("[FAIL]")]
            warns = [l for l in log.splitlines() if l.startswith("[WARN]")]
            if rep.exists():
                dur = json.load(open(rep)).get("duration", dur)
            status = f"{len(fails)} FAIL, {len(warns)} WARN"
            for l in fails + warns:
                print(f"  {f}: {l}")
        rows.append([f, size, status])

    at = a.at if a.at is not None else (max(0.0, dur - 0.6) if dur else 1.0)   # sin validar no hay duración: usa --at
    for f, w, h in fmts:
        png = out / f"{name}-{f}-cuadro.png"
        code, log = run([py, "-I", str(HERE / "render.py"), "--scene", str(scene), "--size", f"{w}x{h}", "--still", str(at), "--out", str(png)])
        if code == 0:
            stills.append((f, png))
        else:
            print(f"  {f}: el cuadro fijo falló:\n{log[-600:]}")

    # lámina: todos a la misma altura (540 px), en fila, con el nombre del formato
    if stills:
        inputs, filt = [], []
        for i, (f, png) in enumerate(stills):
            inputs += ["-i", str(png)]
            filt.append(f"[{i}]scale=-2:540,pad=iw+24:ih+60:12:48:#111111,drawtext=text='{f}':x=14:y=12:fontsize=28:fontcolor=white[v{i}]")
        filt.append("".join(f"[v{i}]" for i in range(len(stills))) + f"hstack=inputs={len(stills)}[o]" if len(stills) > 1 else "[v0]null[o]")
        sheet = out / f"{name}-formatos.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[o]", str(sheet)], check=True)
        print(f"lámina de formatos (t={at:.2f}s) -> {sheet}")

    if not a.only_sheet:
        for row in rows:
            f = row[0]; w, h = next((w, h) for ff, w, h in fmts if ff == f)
            mp4 = out / f"{name}-{f}.mp4"
            code, log = run([py, "-I", str(HERE / "render.py"), "--scene", str(scene), "--size", f"{w}x{h}", "--out", str(mp4), *passthru])
            qa = [l for l in log.splitlines() if l.startswith("qa ") or "WARN" in l]
            row.append(mp4.name if code == 0 else "FALLÓ")
            if code:
                print(f"  {f}: render falló:\n{log[-800:]}")
            for l in qa:
                print(f"  {f}: {l}")

    print("\nformato  tamaño      validación        video")
    for r in rows:
        print(f"{r[0]:8s} {r[1]:11s} {r[2]:17s} {r[3] if len(r) > 3 else '-'}")
    if any("FAIL" in r[2] and not r[2].startswith("0 FAIL") for r in rows) or any(len(r) > 3 and r[3] == "FALLÓ" for r in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
