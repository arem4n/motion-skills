#!/usr/bin/env python3
"""Vista previa en vivo de una escena: barra de tiempo, play, cuadro a cuadro, formatos y recarga automática.

    $PY -I preview.py --scene proy/scene.html [--port 8765] [--host auto|127.0.0.1|0.0.0.0]

Sirve SOLO la carpeta del proyecto (lectura) y una página /__preview__ que carga scene.html en un iframe y lo mueve
con window.__seek(t) — el mismo acceso aleatorio que usa el render, así que lo que ves en un instante es lo que
saldrá en ese cuadro. Cuando cambia cualquier archivo del proyecto, recarga y vuelve al mismo segundo.
`--host auto` escucha en la IP de Tailscale si existe (abrir desde otro equipo de la tailnet), si no en 127.0.0.1.
La reproducción es "lo más rápido que se pueda": en escenas 3D pesadas puede ir más lenta que el tiempo real; el
render final no. Sin sonido (las señales se marcan sobre la barra). Ctrl+C para terminar.
"""
import argparse
import functools
import http.server
import json
import os
import pathlib
import re
import subprocess
import time

PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vista previa — __NAME__</title><style>
:root{--bg:#0b0d12;--panel:#151923;--ink:#e8ecf2;--mut:#8a93a6;--acc:#ff5a36}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.3 system-ui,sans-serif}
body{display:flex;flex-direction:column}
#stage{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;min-height:0;padding:12px}
#wrap{position:relative;box-shadow:0 0 0 1px #2a3142}
iframe{border:0;transform-origin:0 0;position:absolute;left:0;top:0;background:#000}
#bar{background:var(--panel);padding:10px 14px 12px;display:flex;flex-direction:column;gap:8px}
#row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button,select{background:#232a3a;color:var(--ink);border:1px solid #303a50;border-radius:6px;padding:6px 10px;font:inherit;cursor:pointer}
button:hover{border-color:var(--acc)}#play{min-width:76px}
#t{font-variant-numeric:tabular-nums;min-width:150px}#msg{color:var(--mut);margin-left:auto}
#track{position:relative;height:26px}
#scrub{width:100%;margin:0;position:absolute;top:6px;accent-color:var(--acc)}
.cue{position:absolute;top:0;width:2px;height:8px;background:#ffd166;opacity:.8}
</style></head><body>
<div id="stage"><div id="wrap"><iframe id="f"></iframe></div></div>
<div id="bar"><div id="track"><input id="scrub" type="range" min="0" max="1" step="0.001" value="0"></div>
<div id="row"><button id="play">▶ Play</button><button id="prev" title="cuadro anterior (←)">◀ 1</button><button id="next" title="cuadro siguiente (→)">1 ▶</button>
<label>formato <select id="fmt"></select></label><label><input type="checkbox" id="loop" checked> bucle</label>
<span id="t">0.000 s</span><span id="msg">cargando…</span></div></div>
<script>
var DEF = __SIZE__, FMTS = {"escena": DEF, "9x16": [1080, 1920], "16x9": [1920, 1080], "1x1": [1080, 1080], "4x5": [1080, 1350]};
var f = document.getElementById('f'), wrap = document.getElementById('wrap'), sc = document.getElementById('scrub'), tl = document.getElementById('t'),
    msg = document.getElementById('msg'), fmt = document.getElementById('fmt'), track = document.getElementById('track');
Object.keys(FMTS).forEach(function (k) { var o = document.createElement('option'); o.value = k; o.textContent = k + ' (' + FMTS[k].join('×') + ')'; fmt.appendChild(o); });
var q = new URLSearchParams(location.search); if (q.get('fmt') && FMTS[q.get('fmt')]) fmt.value = q.get('fmt');
var W, H, dur = 0, t = 0, playing = false, last = 0, stamp = null, FPS = 30;
function win() { return f.contentWindow; }
function fit() {
  var st = document.getElementById('stage'), s = Math.min((st.clientWidth - 24) / W, (st.clientHeight - 24) / H);
  wrap.style.width = W * s + 'px'; wrap.style.height = H * s + 'px'; f.style.width = W + 'px'; f.style.height = H + 'px'; f.style.transform = 'scale(' + s + ')';
}
function show(nt) {
  t = Math.max(0, Math.min(dur, nt));
  try { win().__seek(t); } catch (e) {}
  sc.value = t; tl.textContent = t.toFixed(3) + ' s  ·  cuadro ' + Math.round(t * FPS);
}
function load(keepT) {
  var sz = FMTS[fmt.value]; W = sz[0]; H = sz[1]; fit();
  msg.textContent = 'cargando…'; var want = keepT ? t : 0;
  f.src = 'scene.html?w=' + W + '&h=' + H + '&_=' + Date.now();
  var tries = 0, iv = setInterval(function () {
    var w = win(); tries++;
    if (w && w.__ready) {
      clearInterval(iv); dur = w.__duration || 0; sc.max = dur;
      [].slice.call(track.querySelectorAll('.cue')).forEach(function (n) { n.remove(); });
      (w.__cues || []).forEach(function (c) { var m = document.createElement('div'); m.className = 'cue'; m.title = c.name + ' @ ' + c.t.toFixed(2) + ' s';
        m.style.left = (c.t / dur * 100) + '%'; track.appendChild(m); });
      show(want); msg.textContent = W + '×' + H + '  ·  ' + dur.toFixed(2) + ' s  ·  ' + (w.__cues || []).length + ' señales de sonido';
    } else if (tries > 300) { clearInterval(iv); msg.textContent = 'la escena no llegó a __ready (mira la consola del iframe)'; }
  }, 50);
}
var gen = 0;                               // un solo ciclo de reproducción a la vez (pausa+play rápido no duplica la velocidad)
function tick(now, g) {
  if (!playing || g !== gen) return;
  var dt = last ? (now - last) / 1000 : 0; last = now; var nt = t + dt;
  if (nt >= dur) { if (document.getElementById('loop').checked) nt = 0; else { nt = dur; setPlay(false); } }
  show(nt); requestAnimationFrame(function (n) { tick(n, g); });
}
function setPlay(p) { playing = p; last = 0; document.getElementById('play').textContent = p ? '❚❚ Pausa' : '▶ Play'; gen++; var g = gen; if (p) requestAnimationFrame(function (n) { tick(n, g); }); }
document.getElementById('play').onclick = function () { if (!playing && t >= dur) show(0); setPlay(!playing); };
document.getElementById('prev').onclick = function () { setPlay(false); show(Math.round(t * FPS - 1) / FPS); };
document.getElementById('next').onclick = function () { setPlay(false); show(Math.round(t * FPS + 1) / FPS); };
sc.oninput = function () { setPlay(false); show(+sc.value); };
fmt.onchange = function () { setPlay(false); load(true); };
addEventListener('resize', fit);
addEventListener('keydown', function (e) {
  if (e.key === ' ') { e.preventDefault(); document.getElementById('play').click(); }
  else if (e.key === 'ArrowLeft') document.getElementById('prev').click(); else if (e.key === 'ArrowRight') document.getElementById('next').click();
});
setInterval(function () {                 // recarga en vivo: cambió algún archivo del proyecto
  fetch('__mtime__', { cache: 'no-store' }).then(function (r) { return r.text(); }).then(function (m) {
    if (stamp !== null && m !== stamp) { msg.textContent = 'cambió la escena, recargando…'; load(true); }
    stamp = m;
  }).catch(function () { msg.textContent = 'servidor detenido'; });
}, 800);
load(false);
</script></body></html>"""


def tailscale_ip():
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3).stdout.split()
        return out[0] if out else None
    except Exception:
        return None


def scene_size(html):
    m = re.search(r"\|\|\s*(\d+),\s*h:\s*\+q\.get\('h'\)\s*\|\|\s*(\d+)", html) or re.search(r"w:\s*(\d+),\s*h:\s*(\d+)", html)
    return [int(m.group(1)), int(m.group(2))] if m else [1080, 1920]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="auto")
    a = ap.parse_args()
    scene = pathlib.Path(a.scene).resolve(); root = scene.parent
    if scene.name != "scene.html":
        raise SystemExit("--scene tiene que ser el scene.html del proyecto")
    page = PAGE.replace("__SIZE__", json.dumps(scene_size(scene.read_text()))).replace("__NAME__", root.name)
    watch = [p for p in root.rglob("*") if p.is_file() and "node_modules" not in p.parts and p.suffix in (".js", ".html", ".css", ".json")]

    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/__preview__"):
                body = page.encode()
            elif path == "/__mtime__":
                body = str(max((p.stat().st_mtime_ns for p in watch if p.exists()), default=0)).encode()
            else:
                return super().do_GET()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8" if path != "/__mtime__" else "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

    host = a.host if a.host != "auto" else (tailscale_ip() or "127.0.0.1")
    for port in range(a.port, a.port + 20):          # puerto ocupado (otra vista previa abierta): prueba el siguiente
        try:
            srv = http.server.ThreadingHTTPServer((host, port), functools.partial(H, directory=str(root)))
            break
        except OSError:
            continue
    else:
        raise SystemExit(f"no hay puerto libre entre {a.port} y {a.port + 19}")
    print(f"vista previa de {root.name}: http://{host}:{port}/   (Ctrl+C para terminar)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
