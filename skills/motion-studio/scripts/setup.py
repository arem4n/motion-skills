#!/usr/bin/env python3
"""One-time setup for motion-studio: a private venv with everything the scripts import, plus headless Chromium.

    python3 setup.py            # create ~/.cache/motion-studio/venv (if missing) and install playwright, numpy, scipy, pillow, chromium
    python3 setup.py --check    # only report what is missing (exit 1 if anything is)
    python3 setup.py --print    # print the venv python path (use it instead of python3 for the other scripts)
    python3 setup.py --upgrade  # upgrade the packages (new Chromium build: renders may differ by a pixel; run smoke_test.py after)
    python3 setup.py --with-whisper   # also install faster-whisper (only needed by transcribe.py: local subtitles)

The other scripts run with `python -I` (isolated mode ignores user site-packages), so system pip installs are invisible to
them. A dedicated venv avoids that, and installs the Chromium build that matches the installed playwright version.
"""
import argparse
import pathlib
import subprocess
import sys
import venv

VENV = pathlib.Path.home() / ".cache" / "motion-studio" / "venv"
PY = VENV / "bin" / "python"
PKGS = ["playwright", "numpy", "scipy", "pillow"]


def run(*cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def missing():
    """What the venv still lacks (empty list = ready)."""
    if not PY.exists():
        return ["venv"]
    out = []
    for mod in ("playwright", "numpy", "scipy", "PIL"):
        if subprocess.run([str(PY), "-I", "-c", f"import {mod}"], capture_output=True).returncode:
            out.append(mod)
    probe = "from playwright.sync_api import sync_playwright as s\nwith s() as p:\n    p.chromium.launch().close()"
    if "playwright" not in out and subprocess.run([str(PY), "-I", "-c", probe], capture_output=True).returncode:
        out.append("chromium")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    ap.add_argument("--upgrade", action="store_true", help="upgrade playwright/numpy/scipy/pillow (changes the Chromium build: re-run smoke_test.py after)")
    ap.add_argument("--with-whisper", action="store_true", help="also install faster-whisper (optional; for transcribe.py)")
    a = ap.parse_args()
    if a.show:
        print(PY); return
    if a.check:
        m = missing()
        print("ready" if not m else "missing: " + ", ".join(m)); sys.exit(1 if m else 0)
    if not PY.exists():
        VENV.parent.mkdir(parents=True, exist_ok=True)
        venv.create(VENV, with_pip=True)
    # No --upgrade by default: re-running setup must not silently change playwright (and with it the Chromium build that renders).
    run(PY, "-m", "pip", "install", "--quiet", *(["--upgrade"] if a.upgrade else []), *PKGS)
    run(PY, "-m", "playwright", "install", "chromium-headless-shell")
    if a.with_whisper:
        run(PY, "-m", "pip", "install", "--quiet", "faster-whisper")
    m = missing()
    if m:
        sys.exit("setup incomplete, still missing: " + ", ".join(m))
    print(f"ready. Run the other scripts with: {PY} -I <script>.py ...")


if __name__ == "__main__":
    main()
