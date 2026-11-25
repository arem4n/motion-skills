"""Shared helpers: open a scene in headless Chromium and seek it frame by frame.

A scene must call MG.expose(tl) (or MotionKit.expose), which defines window.__seek(t), window.__duration, window.__labels and window.__cues.
That seek protocol (every frame is a pure function of t) is what makes capture deterministic — it is the same
idea Hyperframes' engine and Remotion's renderer rely on, so a scene written for this skill ports to either.
"""
import asyncio
import base64
import gc
import io
import os
import pathlib
from contextlib import contextmanager

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("playwright is not available to this interpreter (-I hides user site-packages).\n"
                     "Run once:  python3 setup.py   then use the venv python it prints:  python3 setup.py --print")


def use_gpu():
    """WebGL por GPU (ANGLE/Vulkan) si el proceso puede abrir el nodo de render; si no, SwiftShader (CPU).
    MOTION_STUDIO_GPU=0 lo fuerza apagado, =1 encendido. Sin acceso al nodo, Vulkan deja la página SIN WebGL
    (no cae a SwiftShader), por eso el modo automático exige acceso real. Medido 2026-11-18 en la Intel HD 530:
    mismo resultado entre corridas (byte a byte), 52,7 dB PSNR contra SwiftShader, captura 3D ~3-4x más rápida."""
    v = os.environ.get("MOTION_STUDIO_GPU", "auto")
    if v in ("0", "1"):
        return v == "1"
    node = "/dev/dri/renderD128"
    return os.path.exists(node) and os.access(node, os.R_OK | os.W_OK)


@contextmanager
def open_scene(scene, width, height, query=""):
    scene = pathlib.Path(scene).resolve()
    with sync_playwright() as p:
        try:
            args = ["--force-color-profile=srgb", "--hide-scrollbars"]
            if use_gpu():
                args += ["--use-angle=vulkan", "--enable-features=Vulkan", "--ignore-gpu-blocklist"]
            browser = p.chromium.launch(args=args)
        except Exception as e:
            if "Executable doesn't exist" in str(e):
                raise SystemExit("Chromium for this playwright version is not installed.\n"
                                 "Run:  python3 -m playwright install chromium-headless-shell   (or python3 setup.py)")
            raise
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        q = [p for p in (query or "").split("&") if p]
        if not any(p.startswith(("w=", "h=")) for p in q):      # el formato viaja en la URL: la escena lo lee si es relativa
            q += [f"w={width}", f"h={height}"]
        page.goto(f"file://{scene}?{'&'.join(q)}")
        try:
            page.wait_for_function("window.__ready === true", timeout=15000)
        except Exception:
            # el error de JS es la causa real; el traceback de playwright no dice nada útil
            why = "; ".join(dict.fromkeys(errors))[:400] or "no console error was logged"
            browser.close()
            raise SystemExit(f"la escena no terminó de cargar en 15 s ({scene.name}): {why}")
        page.evaluate("document.fonts.ready")
        info = page.evaluate("({duration: window.__duration, labels: window.__labels, cues: window.__cues || []})")
        try:
            yield page, info, errors
        finally:
            browser.close()


_CDP = {}
_calls = 0


def _release(page):
    """Drop finished playwright tasks from the transport's error future.

    On Python 3.14 every API call awaits asyncio.wait({transport.on_error_future, ...}); asyncio records the calling task in
    that future's awaited-by set and, under playwright's sync (greenlet) API, never removes it. The future lives as long as
    the browser, so every finished task - and its result, i.e. every screenshot - stays in memory: ~2 MB per 1080p capture,
    2 GB per worker after a thousand captures. That is what ran this server out of RAM and swap (2026-11-10).

    The released tasks sit in reference cycles, and the collector is paced by object count, not bytes: a few hundred objects
    holding megabytes each never trigger it (measured: still +1.8 MB per capture). Hence the explicit collect every 16 calls.
    """
    global _calls
    _calls += 1
    try:
        fut = page._impl_obj._connection._transport.on_error_future
        for w in list(getattr(fut, "_asyncio_awaited_by", None) or ()):
            if w.done():
                asyncio.future_discard_from_awaited_by(fut, w)
    except Exception:
        pass
    if _calls % 16 == 0:
        gc.collect()


def grab(page, t):
    """Seek to t seconds and return a PNG as bytes.

    Uses CDP captureScreenshot with optimizeForSpeed: still lossless and pixel-identical (verified max diff 0), but its
    faster zlib setting makes noisy frames (film grain, paper, photos) ~3.5x cheaper to capture (0.75 s -> 0.2 s at 1080p).
    """
    page.evaluate("t => window.__seek(t)", t)
    _release(page)
    key = id(page)
    if key not in _CDP:
        try:
            _CDP[key] = page.context.new_cdp_session(page)
        except Exception:
            _CDP[key] = None
    s = _CDP[key]
    if s is not None:
        try:
            return base64.b64decode(s.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})["data"])
        except Exception:
            _CDP[key] = None
    return page.screenshot(type="png")


def seek(page, t):
    """Seek without taking a screenshot (cheap: use it to probe the DOM at many instants)."""
    page.evaluate("t => window.__seek(t)", t)
    _release(page)
