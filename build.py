#!/usr/bin/env python3
"""Empaqueta cada skill de skills/ en dist/<nombre>.skill (un zip con la carpeta <nombre>/ en la raíz).

    python3 build.py              # todas
    python3 build.py motion-studio

skills/ es la única fuente. ~/.claude/skills/motion-studio es un enlace a skills/motion-studio, así que lo que usa
Claude Code y lo que se empaqueta aquí son los mismos archivos. Ejecuta esto después de cualquier cambio.
"""
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SKIP = {"__pycache__", "node_modules", ".DS_Store", "contact_sheet.png", "validation_report.json"}   # los dos últimos: salidas por defecto de validate.py


def build(name):
    src = ROOT / "skills" / name
    if not (src / "SKILL.md").is_file():
        raise SystemExit(f"{src} no es una skill (falta SKILL.md)")
    out = ROOT / "dist" / f"{name}.skill"
    out.parent.mkdir(exist_ok=True)
    files = sorted(p for p in src.rglob("*") if p.is_file() and not SKIP & set(p.parts) and p.suffix != ".pyc")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, f"{name}/{p.relative_to(src).as_posix()}")
    print(f"{out.relative_to(ROOT)}: {len(files)} archivos, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
    for n in names:
        build(n)
