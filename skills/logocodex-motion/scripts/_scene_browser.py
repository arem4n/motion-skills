"""Shared helpers: open a scene in headless Chromium and seek it frame by frame.

A scene must call MotionKit.expose(tl), which defines window.__seek(t), window.__duration, window.__labels.
That seek protocol (every frame is a pure function of t) is what makes capture deterministic — it is the same
idea Hyperframes' engine and Remotion's renderer rely on, so a scene written for this skill ports to either.
"""
import asyncio
import gc
import io
import pathlib
from contextlib import contextmanager

from playwright.sync_api import sync_playwright


@contextmanager
def open_scene(scene, width, height, query=""):
    scene = pathlib.Path(scene).resolve()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb", "--hide-scrollbars"])
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(f"file://{scene}{('?' + query) if query else ''}")
        page.wait_for_function("window.__ready === true", timeout=15000)
        page.evaluate("document.fonts.ready")
        info = page.evaluate("({duration: window.__duration, labels: window.__labels})")
        try:
            yield page, info, errors
        finally:
            browser.close()


_calls = 0


def _release(page):
    """Drop finished playwright tasks from the transport's error future.

    On Python 3.14 every API call awaits asyncio.wait({transport.on_error_future, ...}); asyncio records the calling task in
    that future's awaited-by set and, under playwright's sync (greenlet) API, never removes it. The future lives as long as
    the browser, so every finished task - and its result, i.e. every screenshot - stays in memory: ~2 MB per 1080p capture,
    2 GB per worker after a thousand captures, enough to run a small machine out of RAM and swap.

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
    """Seek to t seconds and return a PNG as bytes."""
    page.evaluate("t => window.__seek(t)", t)
    _release(page)
    return page.screenshot(type="png")
