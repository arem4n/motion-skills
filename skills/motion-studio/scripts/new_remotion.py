#!/usr/bin/env python3
"""Crea un proyecto Remotion que monta una o varias escenas motion-studio YA EXISTENTES (camino híbrido: la misma timeline.js).

    python3 -I new_remotion.py --scene main=./proy --out ./proy/remotion [--install]
    python3 -I new_remotion.py --scene hook=./proyA --scene cierre=./proyB@premium --out ./combo [--size 1080x1920] [--fps 30] [--install]

--scene NOMBRE=RUTA[@personalidad] (repetible; NOMBRE es un identificador). `--from RUTA` equivale a `--scene main=RUTA`.
Cada proyecto pasa a src/scenes/NOMBRE.js (su `window.SCENE =` se vuelve `export default`) y se monta con <GsapScene> dentro de un
<Series> en src/Main.tsx, una tras otra, cada una a su duración medida. Se copian fonts/, fonts.css y assets/ a public/. Las variables
--font-display/--font-body de cada escena se aplican solo a su contenedor.

Render:  cd <out> && npx remotion render src/index.ts Main out.mp4 --image-format=png --is-production=false
Sonido:  add_audio.py --scene RUTA/scene.html@inicio[:largo] ... --video out.mp4 --out final.mp4
Detalle, trampas y licencia de Remotion: references/remotion.md. No soporta escenas con Three.js (MG.three): no está probado.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", action="append", help="NOMBRE=RUTA[@personalidad], repetible")
    ap.add_argument("--from", dest="src", help="atajo: una sola escena (= --scene main=RUTA)")
    ap.add_argument("--personality", help="solo con --from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--install", action="store_true", help="npm install al terminar")
    a = ap.parse_args()
    if bool(a.scene) == bool(a.src):
        ap.error("usa --scene (una o varias) o --from (una), no ambos ni ninguno")
    if a.src:
        a.scene = [f"main={a.src}" + (f"@{a.personality}" if a.personality else "")]
    import _remotion_multi   # tarde: el aviso de playwright sale solo si se usa
    return _remotion_multi.multi(a)


if __name__ == "__main__":
    sys.exit(main())
