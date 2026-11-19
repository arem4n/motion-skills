#!/usr/bin/env python3
"""Scaffold a motion-studio project.

    python3 -I new_project.py --project ./promo --format kinetic --size 1080x1920 --personality impact [--fonts bebas-neue:400,inter:500,700]

Formats (starting templates in assets/templates/): kinetic | data | explainer | three (3D hero object, Three.js) | blank
Creates:  scene.html (loader), timeline.js (the scene: edit this), vendor/gsap.min.js, lib/mg.js, tokens.js, fonts/ + fonts.css
Fonts come from npm (@fontsource/*), so they are bundled with the project and render the same everywhere.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_FONTS = {"kinetic": "bebas-neue:400,inter:500,700", "data": "inter:500,700,800", "explainer": "space-grotesk:500,700,inter:400,500",
                 "three": "inter:500,700", "blank": "inter:500,700"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--format", default="blank", choices=["kinetic", "data", "explainer", "three", "blank"])
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--personality", default="corporate")
    ap.add_argument("--fonts", help="family:weight[,weight][,family:weight]  (fontsource names, e.g. inter:500,700)")
    a = ap.parse_args()
    W, H = (int(v) for v in a.size.lower().split("x"))
    proj = pathlib.Path(a.project).resolve(); proj.mkdir(parents=True, exist_ok=True)

    # parse "bebas-neue:400,inter:500,700" -> {family: [weights]}
    fam, cur = {}, None
    for tok in (a.fonts or DEFAULT_FONTS[a.format]).split(","):
        if ":" in tok:
            cur, wgt = tok.split(":"); fam.setdefault(cur, []).append(wgt)
        else:
            fam[cur].append(tok)

    if not (proj / "package.json").exists():
        (proj / "package.json").write_text('{"name":"motion-studio-project","private":true}')
    pk = ["gsap"] + [f"@fontsource/{f}" for f in fam]
    subprocess.run(["npm", "i", *pk, "--silent", "--no-fund", "--no-audit"], cwd=proj, check=True)

    for d in ("vendor", "lib", "fonts"):
        (proj / d).mkdir(exist_ok=True)
    dist = proj / "node_modules" / "gsap" / "dist"
    for n in ("gsap.min.js", "CustomEase.min.js", "MorphSVGPlugin.min.js", "DrawSVGPlugin.min.js", "SplitText.min.js", "MotionPathPlugin.min.js"):
        if (dist / n).exists():
            shutil.copy(dist / n, proj / "vendor" / n)
    shutil.copy(SKILL / "assets" / "lib" / "mg.js", proj / "lib" / "mg.js")
    (proj / "tokens.js").write_text("window.TOKENS = " + (SKILL / "assets" / "personalities.json").read_text() + ";\n")

    css, loads = [], []
    for f, weights in fam.items():
        label = f.replace("-", " ").title().replace(" ", " ")
        for wgt in weights:
            src = proj / "node_modules" / "@fontsource" / f / "files" / f"{f}-latin-{wgt}-normal.woff2"
            if not src.exists():
                print(f"warning: {src.name} not found, skipped"); continue
            shutil.copy(src, proj / "fonts" / src.name)
            css.append(f"@font-face{{font-family:'{label}';font-weight:{wgt};font-style:normal;src:url(fonts/{src.name}) format('woff2');}}")
            loads.append(f"{wgt} 40px '{label}'")
    families = list(fam)
    display = families[0].replace("-", " ").title(); body = families[-1].replace("-", " ").title()
    css.append(f":root{{--font-display:'{display}',sans-serif;--font-body:'{body}',sans-serif;}}")
    (proj / "fonts.css").write_text("\n".join(css) + "\n")

    tpl = SKILL / "assets" / "templates" / a.format
    scene = (tpl / "scene.html").read_text().replace("__W__", str(W)).replace("__H__", str(H)).replace("__PERSONALITY__", a.personality)\
        .replace("__FONTS__", json.dumps(loads))
    (proj / "scene.html").write_text(scene)
    shutil.copy(tpl / "timeline.js", proj / "timeline.js")
    if a.format == "three":
        shutil.copy(SKILL / "assets" / "vendor" / "three.min.js", proj / "vendor" / "three.min.js")
    print(f"project ready: {proj}\n  edit timeline.js, then:\n  python3 -I {SKILL}/scripts/render.py --scene {proj}/scene.html --out out.mp4 --size {W}x{H}")


if __name__ == "__main__":
    sys.exit(main())
