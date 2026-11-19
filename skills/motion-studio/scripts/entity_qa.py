#!/usr/bin/env python3
"""QA por entidad: sigue cada elemento de la escena fotograma a fotograma y dice qué le pasó.

    python3 -I entity_qa.py --scene proy/scene.html --size 1080x1920 [--fps 30] [--report ent.json]

Idea tomada de Diorama (sloemo01, MIT): un actor muerto no debe esconderse detrás de otro que sí se mueve. Aquí cada elemento
(.mg-text, .mg-box, .mg-shape, .mg-img, svg y cualquiera con data-entity="nombre") se mide en CADA fotograma, sin capturas
(solo DOM, así que es barato). Veredictos por entidad:

  EMPTY      nunca fue visible (opacidad < 0.05, visibility:hidden o caja < 2 px) -> elemento muerto: bórralo o hazlo aparecer
  OFFSCREEN  fue visible pero su caja nunca tocó el cuadro
  TELEPORT   saltó > 25 % del lado corto en UN fotograma mientras era visible en ambos (un corte duro de escena no cuenta:
             solo se juzgan elementos cuyo salto no coincide con un cambio de visibilidad)
  FROZEN     (solo con data-entity + data-expect="moves") estuvo visible > 1 s sin cambiar de caja ni de opacidad (la caja se mide
             relativa a .mg-world: un empuje de cámara no cuenta como movimiento del elemento)
  OK         todo lo demás

FAIL (exit 1): EMPTY / OFFSCREEN / FROZEN en una entidad con data-entity (la declaraste: debe cumplir). Para el resto de
elementos solo hay WARN. Complementa a validate.py: no sustituye la hoja de contactos; no ve texto tapado por geometría 3D.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _scene_browser import open_scene, seek  # noqa: E402

PROBE = """(() => {
  const st = document.querySelector('.mg-stage'); if (!st) return null;
  const r0 = st.getBoundingClientRect(); let k = window.__eqid || 0; const out = [];
  const wr = (document.querySelector('.mg-world') || st).getBoundingClientRect(); const ks = r0.width ? (st.offsetWidth || r0.width) / wr.width : 1;
  const eff = el => { let o = 1; for (let n = el; n && n !== document.body; n = n.parentElement) {
    const cs = getComputedStyle(n); o *= parseFloat(cs.opacity); if (cs.visibility === 'hidden' || cs.display === 'none') return 0; } return o; };
  document.querySelectorAll('.mg-text, .mg-box, .mg-shape, .mg-img, .mg-world svg, [data-entity]').forEach(el => {
    if (el.closest('.mg-overlay')) return;
    if (!el.dataset.eqid) el.dataset.eqid = String(++k);
    const r = el.getBoundingClientRect(); const o = eff(el);
    const full = r.width * r.height > 0.8 * r0.width * r0.height && !el.dataset.entity;   // fondos a cuadro completo no son actores
    out.push([+el.dataset.eqid, o, r.left - r0.left, r.top - r0.top, r.width, r.height, full ? 1 : 0,
      el.dataset.entity || '', el.dataset.expect || '', (el.textContent || '').trim().slice(0, 18) || el.className.toString().slice(0, 18),
      (r.left - wr.left) * ks, (r.top - wr.top) * ks, r.width * ks, r.height * ks]);   // coords relativas al mundo: la cámara no cuenta como movimiento
  });
  window.__eqid = k; return { stage: [r0.width, r0.height], items: out };
})()"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--report")
    a = ap.parse_args()
    W, H = (int(v) for v in a.size.lower().split("x"))

    ents = {}   # id -> dict(name, expect, frames=[(t, vis, x, y, w, h)])
    with open_scene(a.scene, W, H) as (page, info, errors):
        dur = info["duration"]
        n = int(dur * a.fps) + 1
        stage = None
        for i in range(n):
            t = min(i / a.fps, dur)
            seek(page, t)
            res = page.evaluate(PROBE)
            if not res:
                raise SystemExit("no hay .mg-stage: ¿la escena usa MG.stage?")
            stage = res["stage"]
            for eid, o, x, y, w, h, full, name, expect, label, rx, ry, rw, rh in res["items"]:
                if full:
                    continue
                e = ents.setdefault(eid, {"name": name, "expect": expect, "label": label, "f": []})
                e["f"].append((t, o >= 0.05 and w >= 2 and h >= 2, x, y, w, h, o, rx, ry, rw, rh))
        short = min(stage)

    rows, fails, warns = [], 0, 0
    for eid, e in ents.items():
        f = e["f"]
        vis = [r for r in f if r[1]]
        verdict, note = "OK", ""
        if not vis:
            verdict, note = "EMPTY", "nunca visible"
        elif not any(r[2] < stage[0] and r[2] + r[4] > 0 and r[3] < stage[1] and r[3] + r[5] > 0 for r in vis):
            verdict, note = "OFFSCREEN", "visible pero fuera del cuadro"
        else:
            jumps = []
            for p, q in zip(f, f[1:]):
                if p[1] and q[1]:
                    d = ((q[2] + q[4] / 2 - p[2] - p[4] / 2) ** 2 + (q[3] + q[5] / 2 - p[3] - p[5] / 2) ** 2) ** 0.5
                    if d > 0.25 * short:
                        jumps.append((round(q[0], 2), round(d)))
            if jumps:
                verdict, note = "TELEPORT", f"salta {jumps[0][1]} px en un fotograma a t={jumps[0][0]}s"
            elif e["expect"] == "moves":
                # ventana de >1 s visible sin cambio de caja ni opacidad
                run_start, frozen = None, False
                for p, q in zip(f, f[1:]):
                    same = p[1] and q[1] and abs(p[7] - q[7]) < 0.5 and abs(p[8] - q[8]) < 0.5 and abs(p[9] - q[9]) < 0.5 and abs(p[6] - q[6]) < 0.01
                    if same:
                        run_start = p[0] if run_start is None else run_start
                        if q[0] - run_start > 1.0:
                            frozen = True
                            break
                    else:
                        run_start = None
                if frozen:
                    verdict, note = "FROZEN", f"quieta > 1 s desde t={round(run_start, 2)}s (data-expect=moves)"
        declared = bool(e["name"])
        if verdict in ("EMPTY", "OFFSCREEN", "FROZEN") and declared:
            level = "FAIL"; fails += 1
        elif verdict != "OK":
            level = "WARN"; warns += 1
        else:
            level = "PASS"
        rows.append({"id": eid, "entity": e["name"] or "-", "label": e["label"], "verdict": verdict, "level": level, "note": note,
                     "visible_s": round(len(vis) / a.fps, 2)})

    for r in rows:
        if r["level"] != "PASS":
            print(f"[{r['level']}] {r['entity']:<14} {r['label'][:18]:<18} {r['verdict']:<9} {r['note']}")
    declared = sum(1 for r in rows if r["entity"] != "-")
    print(f"{len(rows)} elementos ({declared} declarados con data-entity): {fails} FAIL, {warns} WARN, "
          f"{len(rows) - fails - warns} OK")
    if a.report:
        pathlib.Path(a.report).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
