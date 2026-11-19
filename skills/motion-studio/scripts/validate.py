#!/usr/bin/env python3
"""Validate a motion-studio scene: determinism, legibility and pacing, and write a contact sheet.

    python3 -I validate.py --scene project/scene.html --size 1080x1920 --sheet contact.png --report report.json [--safe l,t,r,b]

Checks (exit code 1 if any FAIL):
  lint            no clock, randomness, timers, endless repeats (fail); callbacks / ticker (warn)
  random-access   frames rendered forward and backward are identical (any seek order gives the same picture)
  hook            something moves within the first 0.6 s (warn): a film that starts blank loses the viewer
  end-hold        the last 0.5 s are still, so the final message can be read (warn)
  static-stretch  longest unchanged stretch (warn above 2.5 s)
  safe-area       text/shapes stay inside the safe margins in every settled frame (default: portrait l/r 6%, top 10%, bottom 14%
                  — where platform UI covers a reel; landscape 5% all round)
  text-size       smallest visible text >= 2.8% of the short side (warn): below that it is unreadable on a phone
  contrast        text vs its surrounding background >= 3:1 for large text, 4.5:1 otherwise (fail below 2)
  text-overlap    two visible texts whose boxes overlap by >15% of the smaller one in a settled frame (fail): labels piled on each other
  text-gap        a stretch >1.0 s with no visible text between the first text and the final hold (warn; fine if intentional)
  audio-cues      cues registered with MG.cue (warn if none: the film will be silent)
  continuity      at each section boundary (where most of what was on screen disappears, plus every MG.transition), does something
                  survive it and visibly move/scale into the next beat? score = carried / boundaries; warn below 0.5
                  (beats that replace each other read as slides; hard-cut bursts and the end card are the legit exceptions)
  rhythm          shot lengths between boundaries: warn if the longest is < 3x the shortest (cutting on a metronome)
  fast-move       fastest element travel per frame at the render fps; warn above 80 px/frame (strobes into copies:
                  render with --shutter)
  read-time       texts of >= 5 words stay on screen >= chars/15 + 1.5 s (warn; fine when the narration says the same words)
  framing         elements marked with MG.inFrame(el[, 'whole']) leave the frame (fail)
  three-framing   a 3D mesh cut by the frame edge in a settled frame: part in, part out (fail). Projects the real vertices;
                  fully off-screen meshes are fine (entrances), floor/ao helpers are skipped, opt out with mesh.userData.crop = true
  three-size      at its largest across settled frames, the 3D occupies < 30 % of the frame on its larger side (warn): hero too small
Settled frames = frames that barely differ from the previous 0.1 s sample, so entrances in flight are not judged.
"""
import argparse
import io
import json
import pathlib
import re
import sys

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy missing for this interpreter (-I hides user packages). Run setup.py once and use the python it prints (setup.py --print).")
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _scene_browser import grab, open_scene, seek  # noqa: E402

LINT = [
    (r"Math\.random\s*\(", "fail", "Math.random() makes frames differ between renders"),
    (r"Date\.now|new Date\s*\(|performance\.now", "fail", "reads the wall clock; time must come only from the timeline"),
    (r"requestAnimationFrame|setTimeout|setInterval", "fail", "timers/rAF drive animation off the render clock"),
    (r"repeat\s*:\s*-1", "fail", "infinite repeat has no defined last frame; use a finite repeat"),
    (r"\bon(Complete|Start|Repeat|Reverse)\s*:|eventCallback|\.call\s*\(", "warn", "callbacks run as the playhead passes and break random access"),
    (r"gsap\.ticker", "warn", "the global ticker advances with real time"),
    (r"ScrollTrigger|Draggable|Observer", "warn", "interaction plugins have no meaning in a rendered film"),
]

MEASURE = """(() => {
  const st = document.querySelector('.mg-stage'); if (!st) return [];
  const r0 = st.getBoundingClientRect(); const out = [];
  const eff = el => { let o = 1; for (let n = el; n && n !== document.body; n = n.parentElement) { const cs = getComputedStyle(n); o *= parseFloat(cs.opacity); if (cs.visibility === 'hidden') return 0; } return o; };
  document.querySelectorAll('.mg-text, .mg-box, .mg-shape, .mg-img, .mg-world svg').forEach(el => {
    if (el.closest('.mg-overlay')) return;
    if (eff(el) < 0.6) return;
    if (el.classList.contains('mg-text') && el.querySelector('.mg-wm')) {      // masked entrance: words still outside their mask are not visible
      const ws = [...el.querySelectorAll('.mg-w')]; const seen = ws.some(w => { const a = w.getBoundingClientRect(), b = w.parentElement.getBoundingClientRect();
        const iw = Math.min(a.right, b.right) - Math.max(a.left, b.left), ih = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        return iw > 0 && ih > 0.5 * a.height; });
      if (!seen) return;
    }
    let rect;
    if (el.classList.contains('mg-text')) { const rg = document.createRange(); rg.selectNodeContents(el); rect = rg.getBoundingClientRect();
      if (el.querySelector('.mg-wm')) {        // mask wrappers carry invisible padding (0.14em top, 0.18em bottom, 0.06em sides; negative margin cancels it in layout): do not measure it
        const stg = el.closest('.mg-stage'), k = stg ? stg.getBoundingClientRect().width / stg.offsetWidth : 1, fs = parseFloat(getComputedStyle(el).fontSize) * k;
        const p = { l: 0.06 * fs * k, t: 0.14 * fs * k, r: 0.06 * fs * k, b: 0.18 * fs * k };
        rect = { left: rect.left + p.l, right: rect.right - p.r, top: rect.top + p.t, bottom: rect.bottom - p.b, width: rect.width - p.l - p.r, height: rect.height - p.t - p.b };
      } }
    else rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return;
    const tp = document.elementFromPoint((rect.left + rect.right) / 2, (rect.top + rect.bottom) / 2);   // covered by another scene / clipped away -> not visible
    // texts stacked in the SAME scene must stay measurable (otherwise the top one hides the other from text-overlap); a text under another scene or a card is still skipped
    const stacked = tp && tp.closest('.mg-text') && tp.closest('.mg-scene') && tp.closest('.mg-scene') === el.closest('.mg-scene');
    if (tp && !tp.closest('.mg-overlay') && !el.contains(tp) && !tp.contains(el) && !stacked) return;
    const cs = getComputedStyle(el);
    out.push({ kind: el.classList.contains('mg-text') ? 'text' : 'shape', x0: rect.left, y0: rect.top, x1: rect.right, y1: rect.bottom,
      font: parseFloat(cs.fontSize), color: cs.color, text: (el.textContent || '').trim().slice(0, 24) });
  });
  return { stage: [r0.left, r0.top, r0.width, r0.height], items: out };
})()"""


PROBE = """(() => {
  const st = document.querySelector('.mg-stage'); if (!st) return null;
  const r0 = st.getBoundingClientRect(); const out = [];
  const eff = el => { let o = 1; for (let n = el; n && n !== document.body; n = n.parentElement) { const cs = getComputedStyle(n); o *= parseFloat(cs.opacity); if (cs.visibility === 'hidden') return 0; } return o; };
  let k = window.__mgid || 0;
  document.querySelectorAll('.mg-text, .mg-box, .mg-shape, .mg-img, .mg-world svg, [data-in-frame]').forEach(el => {
    if (el.closest('.mg-overlay')) return;
    if (!el.dataset.mgid) el.dataset.mgid = String(++k);
    if (eff(el) < 0.5) return;
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
    if (r.right < r0.left || r.left > r0.right || r.bottom < r0.top || r.top > r0.bottom) { if (!el.dataset.inFrame) return; }
    if (r.width * r.height > 0.8 * r0.width * r0.height && !el.dataset.inFrame) return;      // full-frame backdrops are not beats
    const tx = (el.textContent || '').trim(); out.push([+el.dataset.mgid, r.left, r.top, r.width, r.height, el.dataset.inFrame || '', tx.slice(0, 20), el.classList.contains('mg-text') ? tx.length : 0, tx.split(/\\s+/).length]);
  });
  window.__mgid = k;
  return { stage: [r0.left, r0.top, r0.width, r0.height], items: out };
})()"""


def continuity_checks(page, D, fps, add):
    """Boundaries, carry, rhythm, fast moves and framing from DOM samples (no screenshots: cheap)."""
    step = 0.2
    declared = page.evaluate("window.__boundaries || []")
    samples = []
    worst_v, worst_v_at, worst_v_txt, off = 0.0, 0.0, "", []
    for i in range(int(D / step) + 1):
        t = min(i * step, D)
        seek(page, t); m = page.evaluate(PROBE)
        if not m:
            return
        cur = {it[0]: it for it in m["items"]}
        samples.append((t, cur))
        sx, sy, sw, sh = m["stage"]
        for it in m["items"]:
            if it[5]:
                cx, cy = it[1] + it[3] / 2, it[2] + it[4] / 2
                whole = it[5] == "whole"
                bad = (it[1] < sx - 1 or it[2] < sy - 1 or it[1] + it[3] > sx + sw + 1 or it[2] + it[4] > sy + sh + 1) if whole else \
                      not (sx <= cx <= sx + sw and sy <= cy <= sy + sh)
                if bad:
                    off.append((round(t, 1), it[6] or f"#{it[0]}"))
        if t + 1.0 / fps <= D:
            seek(page, t + 1.0 / fps); m2 = page.evaluate(PROBE)
            for it in (m2 or {}).get("items", []):
                p = cur.get(it[0])
                if p:
                    v = max(abs((it[1] + it[3] / 2) - (p[1] + p[3] / 2)), abs((it[2] + it[4] / 2) - (p[2] + p[4] / 2)))
                    if v > worst_v:
                        worst_v, worst_v_at, worst_v_txt = v, t, it[6] or f"#{it[0]}"
    # boundaries: most of what was on screen 0.4 s before is GONE 0.4 s after (a replacement). Things ARRIVING next to what stays
    # (a title that holds while a chart builds under it) are a build-up, not a cut: they must not ask the title to move.
    kk = 2
    change = []
    for i in range(kk, len(samples) - kk):
        A, B = set(samples[i - kk][1]), set(samples[i + kk][1])
        change.append((i, len(A - B) / len(A) if A else 0.0))
    found = []
    for j, (i, c) in enumerate(change):
        if c > 0.6 and c >= max(x[1] for x in change[max(0, j - 3): j + 4]):
            if not found or samples[i][0] - samples[found[-1]][0] >= 0.8:
                found.append(i)
    bnds = []
    for i in found:
        t = samples[i][0]
        A, B = samples[i - kk][1], samples[i + kk][1]
        moved = False
        for key in set(A) & set(B):
            a_, b_ = A[key], B[key]
            d = max(abs((a_[1] + a_[3] / 2) - (b_[1] + b_[3] / 2)), abs((a_[2] + a_[4] / 2) - (b_[2] + b_[4] / 2)))
            s = max(b_[3] / a_[3], a_[3] / b_[3], b_[4] / a_[4], a_[4] / b_[4])
            if d > 30 or s > 1.15:                      # output px / size ratio
                moved = True; break
        bnds.append([t, moved])
    for b in declared:                                  # MG.transition / morph / carry calls
        hit = [x for x in bnds if abs(x[0] - b["t"] - b["dur"] / 2) < 0.6]
        if hit:
            hit[0][1] = hit[0][1] or b["carried"]
        elif b["type"] in ("cut", "fade", "push-left", "push-up", "wipe-right", "wipe-left", "zoom", "iris", "brush", "zoom-through"):
            bnds.append([b["t"] + b["dur"] / 2, b["carried"]])
    bnds.sort()
    if not bnds:
        add("continuity", "pass", "one continuous beat (no section boundary detected)")
    else:
        carried = sum(1 for _, c in bnds if c)
        score = carried / len(bnds)
        cut = [round(t, 1) for t, c in bnds if not c]
        add("continuity", "pass" if score >= 0.5 else "warn",
            f"{carried}/{len(bnds)} boundaries carried (score {score:.2f})" + (f"; replaced at t={cut[:8]}" if cut else ""))
    edges = [0.0] + [t for t, _ in bnds] + [D]
    shots = [b - a for a, b in zip(edges, edges[1:]) if b - a > 0.15]
    if len(shots) >= 3:
        r = max(shots) / min(shots)
        add("rhythm", "pass" if r >= 3 else "warn",
            f"shot lengths {min(shots):.1f}-{max(shots):.1f}s ({r:.1f}x)" + ("" if r >= 3 else ": too even, vary them >= 4x (short hits next to long holds)"))
    add("fast-move", "warn" if worst_v > 80 else "pass",
        f"fastest travel {worst_v:.0f} px/frame at {fps} fps (t={worst_v_at:.1f}s, {worst_v_txt!r})" +
        ("; render with --shutter 8 or it strobes" if worst_v > 80 else ""))
    # read-time: a sentence on screen needs ~ chars/15 + 1.5 s to be read (titles and single words are exempt)
    vis = {}
    for t, cur in samples:
        for key, it in cur.items():
            if it[7] and it[8] >= 5:
                vis.setdefault(key, []).append(t)
    short = []
    for key, ts in vis.items():
        it = next(c[key] for _, c in samples if key in c)
        runs, s0, prev = [], ts[0], ts[0]
        for t in ts[1:]:
            if t - prev > step * 1.5:
                runs.append((s0, prev)); s0 = t
            prev = t
        runs.append((s0, prev))
        need = it[7] / 15 + 1.5
        for r0, r1 in runs:
            if r1 < D - 0.3 and (r1 - r0 + step) < need:
                short.append((round(r0, 1), it[6], round(r1 - r0 + step, 1), round(need, 1)))
    add("read-time", "warn" if short else "pass",
        "on screen shorter than it takes to read (t, text, shown s, needed s): " + str(short[:4]) +
        " — fine if the voice says the same words" if short else "every sentence stays long enough to be read (chars/15 + 1.5 s)")
    marked = page.evaluate("document.querySelectorAll('[data-in-frame]').length")
    if marked:
        o = sorted(set(off))
        add("framing", "fail" if o else "pass", f"left the frame: {o[:5]}" if o else f"{marked} marked element(s) stay in frame")


def lum(rgb):
    c = np.array(rgb[:3], float) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_color(s):
    m = re.findall(r"[\d.]+", s)
    return [float(x) for x in m[:3]] if len(m) >= 3 else [255, 255, 255]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--safe", help="l,t,r,b as fractions of the canvas (default depends on orientation)")
    ap.add_argument("--sheet", default="contact_sheet.png")
    ap.add_argument("--report", default="validation_report.json")
    ap.add_argument("--query", default="")
    ap.add_argument("--fps", type=int, default=30, help="render fps, for the fast-move check")
    a = ap.parse_args()
    W, H = (int(v) for v in a.size.lower().split("x"))
    if a.safe:
        sl, st_, sr, sb = (float(v) for v in a.safe.split(","))
    elif H > W:
        sl, st_, sr, sb = 0.06, 0.10, 0.06, 0.14
    else:
        sl = st_ = sr = sb = 0.05
    results = []

    def add(name, status, detail):
        results.append({"check": name, "status": status, "detail": detail})
        print(f"[{status.upper():4}] {name}: {detail}")

    base = pathlib.Path(a.scene).parent
    src = ""
    for f in ("scene.html", "timeline.js"):
        if (base / f).exists():
            src += (base / f).read_text() + "\n"
    hits = []
    for pat, sev, msg in LINT:
        if re.search(pat, src):
            hits.append((sev, msg))
    if any(s == "fail" for s, _ in hits):
        add("lint", "fail", "; ".join(m for s, m in hits if s == "fail"))
    elif hits:
        add("lint", "warn", "; ".join(m for _, m in hits))
    else:
        add("lint", "pass", "no clock, randomness, timers, endless repeats or callbacks")

    with open_scene(a.scene, W, H, a.query) as (page, info, errors):
        D = info["duration"]
        print(f"duration {D:.2f}s  size {W}x{H}  labels={ {k: round(v, 2) for k, v in info['labels'].items()} }")
        if errors:
            add("page-errors", "fail", "; ".join(errors[:3]))

        # ---- random access ----
        n = 8
        times = [D * (i + 0.5) / n for i in range(n)]
        def img(t): return Image.open(io.BytesIO(grab(page, t))).convert("RGB")
        fwd = {t: np.array(img(t)).astype(int) for t in times}
        bwd = {t: np.array(img(t)).astype(int) for t in reversed(times)}
        bad = []; worst = 0.0
        for t in times:
            share = float((np.abs(fwd[t] - bwd[t]).max(axis=2) > 16).mean()); worst = max(worst, share)
            if share > 0.0001:
                bad.append(round(t, 2))
        add("random-access (forward vs backward)", "fail" if bad else "pass",
            f"frames differ at t={bad} ({worst*100:.3f}% of pixels)" if bad else f"{n} frames identical in both orders (worst {worst*100:.4f}%)")

        # film grain shimmers on purpose; hide it so 'motion' means real motion
        page.evaluate("document.querySelectorAll('.mg-grain').forEach(g => g.style.display = 'none')")
        # boiling linework (MG.boil) also moves on purpose: freeze it, or every frame counts as motion
        page.evaluate("document.querySelectorAll('[id^=mg-boil-] feTurbulence').forEach(t => { t.setAttribute('data-frozen', t.getAttribute('seed')); });"
                      "document.querySelectorAll('*').forEach(n => { if ((n.style.filter || '').includes('mg-boil-')) n.style.filter = 'none'; })")
        # ---- motion probe at 10 fps: hook, end-hold, static stretch, settled frames ----
        step = 0.1; N = int(D / step)
        prev = first = None; moves = []; settled = []; strict = []; still_run = worst_run = 0.0; worst_at = 0.0; first_move = None
        for i in range(N + 1):
            t = min(i * step, D)
            cur = np.array(img(t).convert("L").resize((W // 4, H // 4))).astype(np.int16)
            if first is None:
                first = cur
            if prev is not None:
                dm = float(np.abs(cur - prev).mean()); moves.append((t, dm))
                if dm < 0.15:
                    settled.append(t)
                if dm < 0.03:
                    strict.append(t)
                if dm < 0.02:
                    still_run += step
                    if still_run > worst_run:
                        worst_run, worst_at = still_run, t
                else:
                    still_run = 0.0
            if first_move is None and float(np.abs(cur - first).mean()) > 0.4:
                first_move = t
            prev = cur
        add("hook (first change)", "pass" if first_move is not None and first_move <= 0.6 else "warn",
            f"first visible change at t={first_move:.1f}s" if first_move is not None else "nothing ever changes")
        tail = [dm for t, dm in moves if t > D - 0.5]
        add("end-hold", "pass" if tail and max(tail) < 0.15 else "warn",
            "the last 0.5 s are still" if tail and max(tail) < 0.15 else "the film ends while something still moves; hold the final frame ~0.6 s")
        add("static-stretch", "warn" if worst_run > 2.5 else "pass", f"longest unchanged stretch {worst_run:.1f}s (ending t={worst_at:.1f}s)")

        # ---- DOM checks on settled frames (+ last frame) ----
        base = strict if len(strict) >= 3 else settled   # strict: nothing in flight (an iris/push can hide a scene under another)
        pick = sorted(set(base[:: max(1, len(base) // 12)] + [D]))
        out_of_safe, small, low, piled = [], [], [], []
        cut3d, size3d, has3d = [], None, False
        min_font = 1e9
        for t in pick:
            png = grab(page, t); im = Image.open(io.BytesIO(png)).convert("RGB"); arr = np.array(im)
            m = page.evaluate(MEASURE)
            if not m:
                continue
            sx, sy, sw, sh = m["stage"]; k = W / sw if sw else 1
            # canvas dimensions in design px: stage is scaled to fit, so ratio of design/css is design_w / sw
            design_w = page.evaluate("document.querySelector('.mg-stage').offsetWidth"); design_h = page.evaluate("document.querySelector('.mg-stage').offsetHeight")
            k = design_w / sw
            boxes = page.evaluate("window.__threeBoxes ? window.__threeBoxes() : null")
            if boxes is not None:
                has3d = True; tol_x, tol_y = 0.005 * design_w, 0.005 * design_h; ux0 = uy0 = 1e9; ux1 = uy1 = -1e9
                for b in boxes:
                    if b["behind"] or (b["x1"] - b["x0"] > design_w and b["y1"] - b["y0"] > design_h):
                        continue                     # cámara dentro del objeto o fondo más grande que el cuadro
                    inside = b["x1"] > 0 and b["x0"] < design_w and b["y1"] > 0 and b["y0"] < design_h
                    if inside and (b["x0"] < -tol_x or b["x1"] > design_w + tol_x or b["y0"] < -tol_y or b["y1"] > design_h + tol_y):
                        side = "left" if b["x0"] < -tol_x else "right" if b["x1"] > design_w + tol_x else "top" if b["y0"] < -tol_y else "bottom"
                        cut3d.append((round(t, 1), b["name"], side))
                    if inside:
                        ux0, uy0 = min(ux0, max(0, b["x0"])), min(uy0, max(0, b["y0"])); ux1, uy1 = max(ux1, min(design_w, b["x1"])), max(uy1, min(design_h, b["y1"]))
                frac = max((ux1 - ux0) / design_w, (uy1 - uy0) / design_h) if ux1 > ux0 else 0.0
                size3d = max(size3d or 0.0, frac)          # el mayor tamaño entre los cuadros quietos (una pieza puede terminar vacía a propósito)
            tx = [it for it in m["items"] if it["kind"] == "text"]
            for i, p_ in enumerate(tx):
                for q_ in tx[i + 1:]:
                    iw = min(p_["x1"], q_["x1"]) - max(p_["x0"], q_["x0"]); ih = min(p_["y1"], q_["y1"]) - max(p_["y0"], q_["y0"])
                    if iw > 0 and ih > 0:
                        small_area = min((p_["x1"] - p_["x0"]) * (p_["y1"] - p_["y0"]), (q_["x1"] - q_["x0"]) * (q_["y1"] - q_["y0"]))
                        if iw * ih > 0.15 * small_area:
                            piled.append((round(t, 1), p_["text"], q_["text"]))
            for it in m["items"]:
                dx0, dy0, dx1, dy1 = (it["x0"] - sx) * k, (it["y0"] - sy) * k, (it["x1"] - sx) * k, (it["y1"] - sy) * k
                if dx0 < sl * design_w - 1 or dx1 > (1 - sr) * design_w + 1 or dy0 < st_ * design_h - 1 or dy1 > (1 - sb) * design_h + 1:
                    if it["kind"] == "text" or (dx1 - dx0) < design_w * 0.9:
                        out_of_safe.append((round(t, 1), it["text"] or it["kind"]))
                if it["kind"] == "text":
                    fs = it["font"]; min_font = min(min_font, fs)
                    if fs < 0.028 * min(design_w, design_h):
                        small.append((round(t, 1), it["text"], round(fs)))
                    # contrast: median colour of a ring just outside the text box vs the text colour
                    pad = 3                                    # tight ring: text on small chips/badges must not sample past the chip edge
                    x0, y0, x1, y1 = int(it["x0"]) - pad, int(it["y0"]) - pad, int(it["x1"]) + pad, int(it["y1"]) + pad
                    cl = lambda v_, hi: min(hi - 1, max(0, int(v_)))
                    pts = []
                    for xx in np.linspace(max(0, x0), min(W - 1, x1), 6):
                        pts += [arr[cl(y0, H)][cl(xx, W)], arr[cl(y1, H)][cl(xx, W)]]
                    for yy in np.linspace(max(0, y0), min(H - 1, y1), 4):
                        pts += [arr[cl(yy, H)][cl(x0, W)], arr[cl(yy, H)][cl(x1, W)]]
                    bg = np.median(np.array(pts), axis=0)
                    cr = ratio(parse_color(it["color"]), bg)
                    large = fs >= 0.04 * min(design_w, design_h)
                    if cr < (3.0 if large else 4.5):
                        low.append((round(t, 1), it["text"], round(cr, 1)))
        if has3d:
            c3 = sorted(set(cut3d))
            add("three-framing", "fail" if c3 else "pass",
                f"3D cut by the frame edge (time, mesh, side): {c3[:5]} — pull the camera back, or mesh.userData.crop = true if intended" if c3
                else f"no 3D mesh cut by the frame in {len(pick)} settled frames")
            if size3d is not None:
                add("three-size", "warn" if size3d < 0.30 else "pass",
                    f"3D occupies at most {size3d*100:.0f}% of the frame: the hero reads small" if size3d < 0.30 else f"3D occupies up to {size3d*100:.0f}% of the frame")
        pl = sorted(set(piled))
        add("text-overlap", "fail" if pl else "pass",
            f"texts on top of each other: {pl[:4]}" if pl else f"no overlapping texts in {len(pick)} settled frames")
        oos = sorted(set(out_of_safe))
        add("safe-area", "fail" if oos else "pass",
            f"outside margins ({sl:.2f},{st_:.2f},{sr:.2f},{sb:.2f}): {oos[:5]}" if oos else f"inside margins ({sl:.2f},{st_:.2f},{sr:.2f},{sb:.2f}) in {len(pick)} settled frames")
        add("text-size", "warn" if small else "pass",
            f"too small for a phone: {sorted(set(small))[:4]}" if small else f"smallest text {min_font:.0f}px of {min(design_w, design_h)} short side" if min_font < 1e8 else "no text found")
        worst_cr = min([c for _, _, c in low], default=None)
        add("contrast", "fail" if worst_cr is not None and worst_cr < 2 else ("warn" if low else "pass"),
            f"low contrast: {sorted(set(low))[:4]}" if low else "text/background contrast is sufficient in the sampled frames")
        has, run, worst_gap, gap_at, seen = [], 0.0, 0.0, 0.0, False
        for i in range(int((D - 0.5) / 0.25) + 1):
            t = i * 0.25; seek(page, t)
            m = page.evaluate(MEASURE)
            vis = bool(m) and any(it["kind"] == "text" for it in m["items"])
            seen = seen or vis
            if seen and not vis:
                run += 0.25
                if run > worst_gap:
                    worst_gap, gap_at = run, t
            else:
                run = 0.0
        add("text-gap", "warn" if worst_gap > 1.0 else "pass",
            f"{worst_gap:.2f}s with no visible text (ending t={gap_at:.2f}s)" if worst_gap > 1.0 else "no stretch longer than 1 s without text")
        add("audio-cues", "pass" if info["cues"] else "warn", f"{len(info['cues'])} sound cues" if info["cues"] else "no MG.cue registered: the film will be silent")
        continuity_checks(page, D, a.fps, add)

        # ---- contact sheet ----
        count = 12
        ts = [D * i / (count - 1) for i in range(count)]
        tw = 360; th = int(tw * H / W)
        cols = 6 if W >= H else 6
        rows = (count + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (24, 24, 24)); dr = ImageDraw.Draw(sheet)
        for i, t in enumerate(ts):
            fr = img(t).resize((tw, th)); x, y = (i % cols) * tw, (i // cols) * (th + 22)
            sheet.paste(fr, (x, y + 22))
            lab = [k for k, v in info["labels"].items() if abs(v - t) < D / (count * 2)]
            dr.text((x + 6, y + 5), f"t={t:.1f}s" + (f" ({lab[0]})" if lab else ""), fill=(230, 230, 230))
        sheet.save(a.sheet); print("contact sheet ->", a.sheet)

    json.dump({"duration": D, "size": [W, H], "results": results}, open(a.report, "w"), indent=1)
    sys.exit(1 if any(r["status"] == "fail" for r in results) else 0)


if __name__ == "__main__":
    main()
