"""Montaje de una o varias escenas motion-studio en una composición Remotion (lo usa new_remotion.py)."""
import json
import math
import pathlib
import re
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
REMOTION = "4.0.543"


def loader_personality(scene_html):
    """Personalidad que declara el cargador de scene.html (q.get('personality') || 'xxx')."""
    m = re.search(r"get\('personality'\)\s*\|\|\s*'(\w+)'", pathlib.Path(scene_html).read_text())
    return m.group(1) if m else "corporate"


def shell(out):
    """Archivos comunes del proyecto Remotion: index, package.json, config y tsconfig."""
    (out / "src").mkdir(parents=True, exist_ok=True)
    (out / "src" / "index.ts").write_text(
        'import { registerRoot } from "remotion";\nimport { Root } from "./Root";\nregisterRoot(Root);\n')
    (out / "package.json").write_text(json.dumps({
        "name": "motion-studio-remotion", "private": True,
        "dependencies": {"@remotion/cli": REMOTION, "@remotion/media": REMOTION, "gsap": "3.15.0",
                         "react": "19.2.3", "react-dom": "19.2.3", "remotion": REMOTION},
        "devDependencies": {"@types/react": "19.2.7", "typescript": "5.9.3"}}, indent=1) + "\n")
    (out / "remotion.config.ts").write_text(
        'import { Config } from "@remotion/cli/config";\n\nConfig.setVideoImageFormat("png");\nConfig.setOverwriteOutput(true);\n'
        "// Con poca RAM, 2 pestañas bastan (cada una ~0,8 GB a 1080x1920). Súbelo si sobra memoria.\nConfig.setConcurrency(2);\n")
    (out / "tsconfig.json").write_text(
        '{"compilerOptions":{"target":"ES2022","module":"ESNext","moduleResolution":"bundler","jsx":"react-jsx","strict":false,'
        '"noEmit":true,"skipLibCheck":true,"allowJs":true,"esModuleInterop":true,"lib":["DOM","ES2022"]},"include":["src"]}\n')


def multi(a):
    from _scene_browser import open_scene
    W, H = (int(v) for v in a.size.lower().split("x"))
    out = pathlib.Path(a.out).resolve()
    (out / "src" / "scenes").mkdir(parents=True, exist_ok=True)
    (out / "public").mkdir(exist_ok=True)
    scenes, faces, imports, seqs, kits = [], [], [], [], []
    for spec in a.scene:
        name, _, rest = spec.partition("=")
        path, _, pers = rest.partition("@")
        if not name.isidentifier() or not path:
            raise SystemExit(f"--scene espera NOMBRE=RUTA[@personalidad] con NOMBRE tipo identificador; recibí {spec!r}")
        src = pathlib.Path(path).expanduser().resolve()
        html = src / "scene.html"
        if not html.is_file():
            raise SystemExit(f"{html} no existe")
        if "three.min.js" in html.read_text():
            raise SystemExit(f"{name}: escena con Three.js (MG.three): no está probado en Remotion; usa render.py para esa escena.")
        pers = pers or loader_personality(html)
        with open_scene(html, W, H, f"personality={pers}") as (page, info, errors):
            dur = info["duration"]
        frames = math.ceil(dur * a.fps)
        css = (src / "fonts.css").read_text()
        for line in css.splitlines():
            if line.startswith("@font-face") and line not in faces:
                faces.append(line)
        root = re.search(r":root\{([^}]*)\}", css)
        vars_ = {}
        if root:
            for decl in root.group(1).split(";"):
                if ":" in decl:
                    k, v = decl.split(":", 1)
                    vars_[k.strip()] = v.strip()
        fonts = [json.dumps(f"{m.group(2)} 40px '{m.group(1)}'") for m in re.finditer(r"font-family:'([^']+)';font-weight:(\d+)", css)]
        code, n = re.subn(r"window\.SCENE\s*=", "export default", (src / "timeline.js").read_text(), count=1)
        if n != 1:
            raise SystemExit(f"{name}: timeline.js no define window.SCENE")
        (out / "src" / "scenes" / f"{name}.js").write_text(code)
        if (src / "fonts").is_dir():
            shutil.copytree(src / "fonts", out / "public" / "fonts", dirs_exist_ok=True)
        if (src / "assets").is_dir():
            for f in (src / "assets").rglob("*"):
                if f.is_file():
                    dst = out / "public" / "assets" / f.relative_to(src / "assets")
                    if dst.exists() and dst.read_bytes() != f.read_bytes():
                        print(f"AVISO: assets/{f.relative_to(src / 'assets')} existe con contenido distinto en otra escena; se queda la primera.")
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, dst)
        kit = (src / "lib" / "mg.js").read_bytes()
        if kits and kit != kits[-1]:
            print(f"AVISO: {name} trae un lib/mg.js distinto al de la escena anterior; el proyecto usa UNO (el de {name}). "
                  "Recopia el kit actual a los proyectos viejos y vuelve a validar si algo cambia.")
        kits.append(kit)
        if b"api.reset" not in kit:
            print(f"AVISO: el lib/mg.js de {name} es anterior a MG.reset(): con varias escenas, señales y MG.stepped pueden heredarse. Recopia el kit.")
        (out / "src" / "mg.js").write_bytes(kit)
        shutil.copy(src / "tokens.js", out / "src" / "tokens.js")
        imports.append(f'import {name} from "./scenes/{name}.js";')
        seqs.append(
            f"      <Series.Sequence durationInFrames={{{frames}}}>{{/* {name}: {dur:.2f} s medidos */}}\n"
            f'        <GsapScene scene={{{name}}} personality="{pers}" w={{W}} h={{H}}\n'
            f"          fonts={{[{', '.join(fonts)}]}}\n"
            f"          vars={{{json.dumps(vars_)}}} />\n"
            f"      </Series.Sequence>")
        scenes.append((name, frames, dur))
    (out / "public" / "fonts.css").write_text("\n".join(faces) + "\n")
    shutil.copy(HERE.parent / "assets" / "remotion" / "GsapScene.tsx", out / "src" / "GsapScene.tsx")
    total = sum(f for _, f, _ in scenes)
    (out / "src" / "Main.tsx").write_text(
        'import React from "react";\n'
        'import { AbsoluteFill, Series, staticFile } from "remotion";\n'
        'import { GsapScene } from "./GsapScene";\n' + "\n".join(imports) + "\n\n"
        f"export const W = {W}, H = {H}, FPS = {a.fps};\n"
        f"export const TOTAL = {total}; // suma de las secuencias: actualízala si recortas una o añades un segmento nativo\n\n"
        "// Intercala aquí segmentos nativos de Remotion (<Video> de @remotion/media, subtítulos...) como más <Series.Sequence>.\n"
        "export const Main: React.FC = () => (\n"
        '  <AbsoluteFill style={{ background: "#000" }}>\n'
        '    <link rel="stylesheet" href={staticFile("fonts.css")} />\n'
        "    <Series>\n" + "\n".join(seqs) + "\n    </Series>\n  </AbsoluteFill>\n);\n")
    (out / "src" / "Root.tsx").write_text(
        'import React from "react";\nimport { Composition } from "remotion";\nimport { Main, W, H, FPS, TOTAL } from "./Main";\n\n'
        'export const Root: React.FC = () => <Composition id="Main" component={Main} durationInFrames={TOTAL} fps={FPS} width={W} height={H} />;\n')
    shell(out)
    print(f"proyecto Remotion multiescena listo: {out}")
    for name, frames, dur in scenes:
        print(f"  {name}: {frames} fotogramas ({dur:.2f} s)")
    print(f"  total {total} fotogramas; render: npx remotion render src/index.ts Main out.mp4 --image-format=png --is-production=false")
    if a.install:
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=out, check=True)
    else:
        print(f"  siguiente: cd {out} && npm install")
