#!/usr/bin/env python3
"""Prueba de humo de motion-studio: ejecútala después de tocar el kit (lib/mg.js), una plantilla o el validador.

    $PY -I smoke_test.py [--only kinetic,data] [--no-controls] [--matrix] [--keep]

Trabaja en un directorio temporal; nunca escribe en la skill. Sale con código 1 si algo falla. Tarda ~2 min (instala fuentes de npm por plantilla).

1. PLANTILLAS: para cada formato (kinetic, data, explainer, three, blank) hace `new_project.py` SIN --fonts (así se vigila el KeyError de
   'three') en 1080x1920 / corporate, corre `validate.py` y exige **0 FAIL y 0 WARN** (los 14 checks en PASS), y `entity_qa.py` sin FAIL.
   Con --matrix (10–20 min más): cada formato además con las 6 personalidades en 1080x1920 y con `corporate` en 1920x1080 y 1080x1080;
   ahí se exige **0 FAIL** (los WARN se listan: `fast-move`, `hook` con `calm`… son avisos conocidos, no fallos).
2. CONTROLES NEGATIVOS del validador (sobre una copia de `blank`): un validador que "arregla" falsos positivos no debe dejar de ver lo real.
   - dos textos realmente encimados            -> text-overlap debe dar FAIL
   - texto pegado al borde (fuera de zona)     -> safe-area debe dar FAIL
   - `Date.now()` en el timeline               -> lint debe dar FAIL
   - un titular reemplaza a otro               -> continuity debe dar WARN
   - un titular fijo y contenido que llega     -> continuity NO debe dar WARN (construir no es cortar)
   - tres líneas apiladas con `split:'words'`
     e interlineado apretado (0.9), bien
     separadas                                 -> text-overlap NO debe dar FAIL (la regresión del relleno de máscara)
   - plantilla `three` en 9x16 sin el ajuste de
     encuadre por proporción (objeto cortado)  -> three-framing debe dar FAIL (el validador ve el 3D cortado en el borde)
3. HERRAMIENTAS (--no-tools las salta):
   - `formats.py --only-sheet` sobre `blank` en 16x9 y 4x5: termina bien, 0 FAIL y arma la lámina de formatos.
   - `preview.py` en 127.0.0.1, abierto con Chromium: carga la escena, el selector de formato cambia el tamaño real (lo dice
     la escena, no un regex), recarga sola al editar `timeline.js`, y avisa cuando una escena de tamaño fijo no cambia de formato.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
FORMATS = ["kinetic", "data", "explainer", "three", "blank"]
SIZE = "1080x1920"

HEAD = "window.SCENE = { bg: '#0c0c0f', build: function (MG, T, S, tl) {\n  var sc = S.scene('main'); MG.show(tl, sc, 0);\n"
FOOT = "\n  return 3; } };\n"
CONTROLS = [
    ("texto realmente encimado -> text-overlap FAIL", "text-overlap", "fail",
     HEAD + "  MG.text(sc, { text: 'PRIMERA CAPA', x: S_w2(), y: 900, w: 900, size: 120, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });\n"
     "  MG.text(sc, { text: 'OTRA CAPA ENCIMA', x: S_w2(), y: 930, w: 900, size: 120, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });" + FOOT),
    ("texto pegado al borde -> safe-area FAIL", "safe-area", "fail",
     HEAD + "  MG.text(sc, { text: 'FUERA DE ZONA', x: 14, y: 900, w: 900, size: 120, weight: 700, align: 'left', font: 'var(--font-display)', color: '#fff' });" + FOOT),
    ("Date.now() -> lint FAIL", "lint", "fail",
     HEAD + "  var t0 = Date.now();\n  MG.text(sc, { text: 'RELOJ', x: S_w2(), y: 900, w: 900, size: 120, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });" + FOOT),
    ("un titular reemplaza a otro, sin nada que sobreviva -> continuity WARN", "continuity", "warn",
     HEAD + "  var a = MG.text(sc, { text: 'PRIMERA IDEA', x: S_w2(), y: 800, w: 900, size: 110, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });\n"
     "  var b = MG.text(sc, { text: 'SEGUNDA IDEA', x: S_w2(), y: 1000, w: 900, size: 110, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });\n"
     "  tl.set(b.el, { autoAlpha: 0 }, 0); tl.set(a.el, { autoAlpha: 0 }, 1.5); tl.set(b.el, { autoAlpha: 1 }, 1.5);" + FOOT),
    ("un titular se queda y debajo llega más contenido (construcción) -> continuity NO WARN", "continuity", "pass",
     HEAD + "  MG.text(sc, { text: 'TITULAR FIJO', x: S_w2(), y: 500, w: 900, size: 110, weight: 700, align: 'center', font: 'var(--font-display)', color: '#fff' });\n"
     "  [0, 1, 2, 3].forEach(function (i) { var bx = MG.box(sc, { x: 200 + i * 180, y: 900, w: 140, h: 300, bg: '#4dd2a1' }); tl.set(bx, { autoAlpha: 0 }, 0); tl.set(bx, { autoAlpha: 1 }, 1.5); });" + FOOT),
    ("tres líneas apiladas con split y lh 0.9, bien separadas -> text-overlap NO FAIL", "text-overlap", "not-fail",
     HEAD + "  ['UNO', 'DOS', 'TRES'].forEach(function (w, i) {\n"
     "    MG.text(sc, { text: w, x: S_w2(), y: 600 + i * 200 * 0.9, w: 900, size: 200, weight: 700, lh: 0.9, align: 'center', split: 'words', font: 'var(--font-display)', color: '#fff' });\n  });" + FOOT),
]


def run(args, **kw):
    return subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True, **kw)


def validate(scene, report, sheet, size=SIZE, query=None):
    r = run([HERE / "validate.py", "--scene", scene, "--size", size, "--report", report, "--sheet", sheet] + (["--query", query] if query else []))
    data = json.loads(pathlib.Path(report).read_text()) if pathlib.Path(report).exists() else {"results": []}
    return r, {x["check"].split(" ")[0]: x for x in data["results"]}


def tools_preview(tmp, base, ok):
    """preview.py de verdad: servidor + Chromium. Formato, tamaño real, recarga en vivo y aviso de tamaño fijo."""
    from playwright.sync_api import sync_playwright
    d = tmp / "pv"; shutil.copytree(base, d, ignore=shutil.ignore_patterns("node_modules"))
    fixed = tmp / "pvfix"; shutil.copytree(base, fixed, ignore=shutil.ignore_patterns("node_modules"))
    sh = (fixed / "scene.html").read_text()
    (fixed / "scene.html").write_text(sh.replace("+q.get('w') || 1080", "1080").replace("+q.get('h') || 1920", "1920"))
    procs = []
    def serve(p):
        pr = subprocess.Popen([sys.executable, "-I", str(HERE / "preview.py"), "--scene", str(p / "scene.html"), "--host", "127.0.0.1", "--port", "18760"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        procs.append(pr); line = pr.stdout.readline()
        return line.split("http://")[1].split()[0] if "http://" in line else None
    MSG = "document.getElementById('msg').textContent"
    step = ["arranque"]
    try:
        url, url_fix = serve(d), serve(fixed)
        if not url or not url_fix:
            ok("preview.py arranca", False, "no imprimió la URL"); return
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
            step[0] = "carga"; pg.goto("http://" + url); pg.wait_for_function(f"{MSG}.includes('señales')", timeout=30000)
            ok("preview.py carga la escena", True)
            step[0] = "formatos"; pg.select_option("#fmt", "4x5"); pg.wait_for_function(f"{MSG}.startsWith('1080×1350')", timeout=30000)
            pg.select_option("#fmt", "escena"); pg.wait_for_function(f"{MSG}.startsWith('1080×1920')", timeout=30000)
            ok("preview.py: formato 4x5 y vuelta al tamaño de la escena", True)
            step[0] = "recarga"; tl_ = d / "timeline.js"; src_ = tl_.read_text(); assert "Tu mensaje" in src_, "la plantilla blank cambió su texto"; tl_.write_text(src_.replace("Tu mensaje", "Recargado"))   # una palabra: el texto va partido en spans sin espacios
            pg.wait_for_function("() => { try { return document.getElementById('f').contentDocument.body.textContent.includes('Recargado'); } catch (e) { return false; } }", timeout=30000)
            ok("preview.py recarga al editar timeline.js", True)
            step[0] = "tamaño fijo"; pg.goto("http://" + url_fix); pg.wait_for_function(f"{MSG}.includes('señales')", timeout=30000)
            pg.select_option("#fmt", "16x9"); pg.wait_for_function(f"{MSG}.includes('señales')", timeout=30000)
            msg = pg.evaluate(MSG)
            ok("preview.py avisa que una escena de tamaño fijo no cambia de formato", msg.startswith("1080×1920") and "tamaño fijo" in msg, msg)
            b.close()
    except Exception as e:
        extra = ""
        try:
            extra = " | msg=" + pg.evaluate(MSG)[:120]
        except Exception:
            pass
        ok(f"preview.py ({step[0]})", False, str(e).splitlines()[0][:160] + extra)
    finally:
        for pr in procs:
            pr.terminate()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="formatos separados por coma (por defecto todos)")
    ap.add_argument("--no-controls", action="store_true", help="salta los controles negativos del validador")
    ap.add_argument("--matrix", action="store_true", help="además: 6 personalidades y 3 formatos por plantilla, exigiendo 0 FAIL")
    ap.add_argument("--keep", action="store_true", help="no borrar el directorio temporal")
    ap.add_argument("--no-tools", action="store_true", help="salta formats.py y preview.py")
    a = ap.parse_args()
    fmts = a.only.split(",") if a.only else FORMATS
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ms-smoke-"))
    fails, t0 = [], time.time()

    def ok(name, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{(' — ' + detail) if detail and not cond else ''}")
        if not cond:
            fails.append(name)

    try:
        print("1) Plantillas (1080x1920, corporate, sin --fonts): 0 FAIL y 0 WARN")
        for f in fmts:
            d = tmp / f
            r = run([HERE / "new_project.py", "--project", d, "--format", f, "--size", SIZE, "--personality", "corporate"])
            if r.returncode != 0:
                ok(f"{f}: new_project", False, (r.stderr or r.stdout).strip().splitlines()[-1][:160])
                continue
            r, res = validate(d / "scene.html", tmp / f"{f}.json", tmp / f"{f}.png")
            bad = [f"{k}={v['status']}" for k, v in res.items() if v["status"] != "pass"]
            ok(f"{f}: validate ({len(res) - len(bad)}/{len(res)} PASS)", res and not bad, ", ".join(bad))
            if f == "three":
                has = res.get("three-framing", {}).get("status") == "pass" and res.get("three-size", {}).get("status") == "pass"
                ok("three: los chequeos 3D corrieron de verdad", has, f"checks vistos: {sorted(res)}")
            r = run([HERE / "entity_qa.py", "--scene", d / "scene.html", "--size", SIZE])
            ok(f"{f}: entity_qa sin FAIL", r.returncode == 0, r.stdout.strip().splitlines()[-1][:160] if r.stdout.strip() else r.stderr[-160:])
        if a.matrix:
            print("1b) Matriz (0 FAIL; los WARN solo se listan)")
            for f in fmts:
                cases = [(SIZE, p, tmp / f) for p in ("playful", "premium", "energetic", "calm", "impact")]
                for size in ("1920x1080", "1080x1080"):
                    d = tmp / f"{f}-{size}"
                    r = run([HERE / "new_project.py", "--project", d, "--format", f, "--size", size, "--personality", "corporate"])
                    if r.returncode != 0:
                        ok(f"{f} {size}: new_project", False, (r.stderr or r.stdout).strip().splitlines()[-1][:160])
                        continue
                    cases.append((size, "corporate", d))
                for size, pers, d in cases:
                    if not (d / "scene.html").exists():
                        continue
                    r, res = validate(d / "scene.html", tmp / "m.json", tmp / "m.png", size, f"personality={pers}")
                    bad = [k for k, v in res.items() if v["status"] == "fail"]
                    warn = [k for k, v in res.items() if v["status"] == "warn"]
                    ok(f"{f} {size} {pers}" + (f"  (WARN: {', '.join(warn)})" if warn else ""), res and not bad, ", ".join(bad) + "=fail")
        if not a.no_controls:
            print("2) Controles negativos del validador (sobre una copia de blank)")
            base = tmp / "blank"
            if not base.exists():
                r = run([HERE / "new_project.py", "--project", base, "--format", "blank", "--size", SIZE])
                if r.returncode != 0:
                    raise SystemExit("no se pudo crear blank: " + r.stderr[-200:])
            for i, (name, check, expect, code) in enumerate(CONTROLS):
                d = tmp / f"ctl{i}"
                shutil.copytree(base, d, ignore=shutil.ignore_patterns("node_modules"))
                (d / "timeline.js").write_text(code.replace("S_w2()", "S.w / 2"))
                r, res = validate(d / "scene.html", tmp / f"ctl{i}.json", tmp / f"ctl{i}.png")
                st = res.get(check, {}).get("status", "(sin resultado)")
                cond = (st == expect) if expect in ("fail", "warn", "pass") else (st != "fail" and check in res)
                ok(name, cond, f"{check}={st}")
            d = tmp / "ctl3d"                                     # el 3D cortado en el borde tiene que fallar
            r = run([HERE / "new_project.py", "--project", d, "--format", "three", "--size", SIZE])
            tl_ = (d / "timeline.js").read_text()
            if r.returncode == 0 and "var fit = " in tl_:
                (d / "timeline.js").write_text(tl_.replace("var fit = Math.max(1, 1.4 / (S.w / S.h + 0.45));", "var fit = 1;"))
                r, res = validate(d / "scene.html", tmp / "ctl3d.json", tmp / "ctl3d.png")
                st = res.get("three-framing", {}).get("status", "(sin resultado)")
                ok("three sin ajuste de encuadre en 9x16 -> three-framing FAIL", st == "fail", f"three-framing={st}")
            else:
                ok("three sin ajuste de encuadre en 9x16 -> three-framing FAIL", False, "no se pudo preparar el control (¿cambió la plantilla?)")
        if not a.no_tools:
            print("3) Herramientas: formats.py y preview.py")
            base = tmp / "blank"
            if not base.exists():
                run([HERE / "new_project.py", "--project", base, "--format", "blank", "--size", SIZE])
            r = run([HERE / "formats.py", "--scene", base / "scene.html", "--out-dir", tmp / "fmt", "--formats", "16x9,4x5", "--only-sheet", "--name", "b"])
            ok("formats.py --only-sheet 16x9,4x5: sin FAIL y con lámina", r.returncode == 0 and (tmp / "fmt" / "b-formatos.png").exists(),
               (r.stdout + r.stderr).strip()[-200:])
            tools_preview(tmp, base, ok)
    finally:
        if a.keep:
            print("directorio temporal:", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODO OK' if not fails else str(len(fails)) + ' FALLO(S)'} en {time.time() - t0:.0f} s")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
