import time, pathlib
from playwright.sync_api import sync_playwright
MSG = "document.getElementById('msg').textContent"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto('http://127.0.0.1:18790/')
    pg.wait_for_function(f"{MSG}.includes('señales')", timeout=30000); print('1', pg.evaluate(MSG))
    print('mtime', pg.evaluate("fetch('__mtime__').then(r=>r.text())"))
    tl = pathlib.Path('pvd/timeline.js'); src = tl.read_text(); print('tiene Tu mensaje:', 'Tu mensaje' in src); tl.write_text(src.replace('Tu mensaje', 'Recarga en vivo'))
    time.sleep(3)
    print('mtime', pg.evaluate("fetch('__mtime__').then(r=>r.text())"), '| msg:', pg.evaluate(MSG))
    print('texto iframe:', pg.evaluate("document.getElementById('f').contentDocument.body.textContent.slice(0,200)"))
    b.close()
