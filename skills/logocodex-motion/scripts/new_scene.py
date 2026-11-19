#!/usr/bin/env python3
"""Scaffold a runnable LogocodeX motion project.

    python3 -I new_scene.py --project ./my-video --layers layers.json [--scene scene.html] [--archetype sabio]

Creates in --project:
    vendor/gsap.min.js (+ CustomEase, MorphSVG, DrawSVG, SplitText, MotionPath)   from npm `gsap`
    lib/motion-kit.js        deterministic tween helpers
    tokens.js                window.TOKENS (archetype motion personalities)
    layers.js                window.LAYERS (vectorized logo layers)
    scene.html               thin loader that mounts the stage and exposes the timeline
    timeline.js              buildTimeline(kit, stg, T, tl): the animation itself (blank starter unless --scene is given;
                             with --scene the sibling timeline.js is copied). Shared by every render target.

Everything is relative so `scene.html` also opens by double-click (file://) — handy for previews.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ["gsap", "CustomEase", "MorphSVGPlugin", "DrawSVGPlugin", "SplitText", "MotionPathPlugin"]


def ensure_gsap(project: pathlib.Path) -> pathlib.Path:
    nm = project / "node_modules" / "gsap" / "dist"
    if not nm.exists():
        project.mkdir(parents=True, exist_ok=True)
        if not (project / "package.json").exists():
            (project / "package.json").write_text('{"name":"logocodex-motion-project","private":true}')
        # gsap >= 3.13 ships every plugin (MorphSVG, DrawSVG, SplitText...) free of charge on npm
        subprocess.run(["npm", "i", "gsap", "--silent", "--no-fund", "--no-audit"], cwd=project, check=True)
    return nm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--layers", required=True, help="layers.json from split_logo_layers.py")
    ap.add_argument("--scene", help="a finished scene.html to copy instead of the blank starter")
    ap.add_argument("--archetype", default="sabio")
    args = ap.parse_args()

    project = pathlib.Path(args.project).resolve()
    dist = ensure_gsap(project)
    (project / "vendor").mkdir(exist_ok=True)
    (project / "lib").mkdir(exist_ok=True)
    for name in PLUGINS:
        src = dist / f"{name}.min.js"
        if src.exists():
            shutil.copy(src, project / "vendor" / src.name)
    shutil.copy(SKILL / "assets" / "lib" / "motion-kit.js", project / "lib" / "motion-kit.js")

    tokens = json.loads((SKILL / "assets" / "motion-tokens.json").read_text())
    (project / "tokens.js").write_text("window.TOKENS = " + json.dumps(tokens) + ";\n")

    layers = pathlib.Path(args.layers).read_text()
    (project / "layers.js").write_text("window.LAYERS = " + layers.strip() + ";\n")

    scene_src = pathlib.Path(args.scene) if args.scene else SKILL / "assets" / "templates" / "scene.starter.html"
    html = scene_src.read_text().replace("__ARCHETYPE__", args.archetype)
    (project / "scene.html").write_text(html)
    tl_src = scene_src.with_name("timeline.js") if args.scene else SKILL / "assets" / "templates" / "timeline.starter.js"
    shutil.copy(tl_src, project / "timeline.js")
    print(f"project ready: {project}\n  open {project/'scene.html'}  (or render with scripts/render_frames.py)")


if __name__ == "__main__":
    sys.exit(main())
