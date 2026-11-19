#!/usr/bin/env python3
"""Validate a LogocodeX motion scene against the manual's rules (Manual de Aplicación Visual §5) and against
the determinism that every renderer (this one, Hyperframes, Remotion) depends on.

    python3 -I validate_motion.py --scene project/scene.html --size 1080x1920 \
        --source logo.png --sheet contact_sheet.png --report report.json [--safe 0.04,0.10,0.04,0.14]

Checks
  lint             no clock, randomness, rAF/timers, endless repeats or callbacks in the scene source
  random-access    frames rendered forward and backward match (any order of seeking gives the same picture)
  logo-integrity   the final frame equals the real logo (no deformation, shift or colour drift): ink within 1px of --source
  colour-integrity the final frame contains no accent colours left over from highlight beats
  safe-area        the logo never leaves the safe margins (default 4% each side) in any sampled frame
  static-stretch   longest stretch with no visible change (long holds are legitimate for slow archetypes — it only warns)
Also writes a contact sheet with the keyframes so a human (or Claude) can read the storyboard at a glance.
Exit code 1 if any check fails.
"""
import argparse
import io
import json
import pathlib
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _scene_browser import grab, open_scene  # noqa: E402

LINT = [
    (r"Math\.random\s*\(", "fail", "Math.random() makes frames differ between renders; use a seeded offset table instead"),
    (r"Date\.now|new Date\s*\(|performance\.now", "fail", "reads the wall clock; time must come only from the timeline"),
    (r"requestAnimationFrame|setTimeout|setInterval", "fail", "timers/rAF drive animation off the render clock"),
    (r"repeat\s*:\s*-1", "fail", "infinite repeat has no defined last frame; use a finite repeat"),
    (r"\bon(Complete|Update|Start|Repeat|Reverse)\s*:|eventCallback|\.call\s*\(", "warn", "callbacks run as the playhead passes and break random access; derive state from the timeline instead"),
    (r"gsap\.ticker", "warn", "the global ticker advances with real time"),
    (r"ScrollTrigger|Draggable|Observer", "warn", "interaction-driven plugins have no meaning in a rendered film"),
]


def to_img(png):
    return Image.open(io.BytesIO(png)).convert("RGB")


def ink_mask(img):
    g = np.array(img.convert("L"))
    return g > 128 if g[2, 2] < 128 else g < 128   # light logo on a dark background, or the usual dark on light


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--size", default="1080x1080")
    ap.add_argument("--source", help="original logo image (PNG with transparency or on white)")
    ap.add_argument("--source-mode", choices=["luminance", "alpha"], default="luminance",
                    help='"alpha" when the logo is a light/white PNG on transparency (same as "mode" in layers.config.json)')
    ap.add_argument("--fill", type=float, default=0.88, help="fraction of the limiting side the logo occupies (scene default 0.88)")
    ap.add_argument("--safe", default="0.04,0.04,0.04,0.04", help="safe insets l,t,r,b as fractions of the canvas")
    ap.add_argument("--sheet", default="contact_sheet.png")
    ap.add_argument("--report", default="validation_report.json")
    ap.add_argument("--query", default="")
    ap.add_argument("--max-xor", type=float, default=0.015, help="max fraction of ink pixels allowed to sit >1px from the source")
    args = ap.parse_args()
    W, H = (int(v) for v in args.size.lower().split("x"))
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    # ---- lint (static) ----
    src = pathlib.Path(args.scene).read_text()
    hits = []
    for pat, level, msg in LINT:
        for m in re.finditer(pat, src):
            hits.append((level, msg, src[: m.start()].count("\n") + 1))
    if not hits:
        add("lint", "pass", "no clock, randomness, timers, endless repeats or callbacks")
    else:
        worst = "fail" if any(h[0] == "fail" for h in hits) else "warn"
        add("lint", worst, "; ".join(f"line {ln}: {msg}" for _, msg, ln in hits[:6]))

    with open_scene(args.scene, W, H, args.query) as (page, info, errors):
        D, labels = info["duration"], info["labels"] or {}
        rest = labels.get("rest")
        if errors:
            add("page-errors", "fail", "; ".join(errors[:3]))

        # ---- random access ----
        times = [0.15 * D, 0.35 * D, 0.55 * D, 0.75 * D, rest if rest else 0.9 * D, D]
        fwd = {t: grab(page, t) for t in times}
        bwd = {t: grab(page, t) for t in reversed(times)}
        # "visually identical", not bit-identical: Chromium may antialias a handful of edge pixels differently after a
        # colour tween has been reverted. A real order-dependence bug (a shape left displaced, a tween that never
        # reverts) changes thousands of pixels by a lot, so we fail on the share of pixels that differ by >16/255.
        worst_share, bad = 0.0, []
        for t in times:
            dm = np.abs(np.array(to_img(fwd[t])).astype(int) - np.array(to_img(bwd[t])).astype(int)).max(axis=2)
            share = float((dm > 16).mean())
            worst_share = max(worst_share, share)
            if share > 0.0001:
                bad.append(round(t, 2))
        add("random-access (forward vs backward)", "fail" if bad else "pass",
            f"frames differ at t={bad} ({worst_share*100:.3f}% of pixels)" if bad else
            f"{len(times)} frames match in both orders (worst {worst_share*100:.4f}% of pixels differ visibly)")

        # ---- final frame checks ----
        final = to_img(fwd[D])
        fa = np.array(final).astype(int)
        sat = fa.max(axis=2) - fa.min(axis=2)
        n_col = int((sat > 40).sum())
        add("colour-integrity", "fail" if n_col > 20 else "pass",
            f"{n_col} saturated pixels left in the last frame" + (" — an accent tint never returned to ink" if n_col > 20 else ""))

        if args.source:
            layers = None
            lp = pathlib.Path(args.scene).parent / "layers.js"
            if lp.exists():
                layers = json.loads(lp.read_text().split("=", 1)[1].strip().rstrip(";"))
            vb = layers["viewBox"] if layers else None
            ratio = (vb[2] / vb[3]) if vb else None
            srcim = Image.open(args.source).convert("RGBA")
            ratio = ratio or srcim.size[0] / srcim.size[1]
            bw = min(args.fill * W, args.fill * H * ratio)
            bh = bw / ratio
            bw, bh = int(round(bw)), int(round(bh))
            if args.source_mode == "alpha":
                ref = Image.new("L", (W, H), 0)
                ref.paste(srcim.getchannel("A").resize((bw, bh), Image.LANCZOS), (int(round((W - bw) / 2)), int(round((H - bh) / 2))))
                rm = np.array(ref) > 128
            else:
                white = Image.new("RGBA", srcim.size, (255, 255, 255, 255)); white.alpha_composite(srcim)
                ref = Image.new("L", (W, H), 255)
                ref.paste(white.convert("L").resize((bw, bh), Image.LANCZOS), (int(round((W - bw) / 2)), int(round((H - bh) / 2))))
                rm = np.array(ref) < 128
            fm = ink_mask(final)
            k = np.ones((3, 3), np.uint8)          # +-1 px tolerance: resampling and sub-pixel placement are not deformation
            miss = (rm & ~(cv2.dilate(fm.astype("uint8"), k) > 0)).sum() + (fm & ~(cv2.dilate(rm.astype("uint8"), k) > 0)).sum()
            xor = float(miss) / max(1, rm.sum())
            add("logo-integrity (last frame vs source)", "pass" if xor <= args.max_xor else "fail",
                f"{xor*100:.2f}% of ink pixels lie more than 1px from the source (limit {args.max_xor*100:.1f}%)")
        else:
            add("logo-integrity (last frame vs source)", "warn", "skipped — pass --source with the original logo to compare")

        # ---- safe area ----
        l, t_, r, b = (float(v) for v in args.safe.split(","))
        out = []
        for t in sorted(set(times + [i * D / 24 for i in range(25)])):
            fr = np.array(to_img(grab(page, t))).astype(int)
            paper = fr[2, 2]
            m = np.abs(fr - paper).sum(axis=2) > 60
            if m.any():
                ys, xs = np.where(m)
                if xs.min() < l * W or xs.max() > (1 - r) * W or ys.min() < t_ * H or ys.max() > (1 - b) * H:
                    out.append(round(t, 2))
        add("safe-area", "fail" if out else "pass",
            f"content crosses the safe margins at t={out[:6]}" if out else f"inside margins {args.safe} in all sampled frames")

        # ---- motion energy / static stretch (10 fps probe) ----
        step = 0.1
        prev, still_run, worst_run, worst_at = None, 0.0, 0.0, 0.0
        n = int(D / step)
        for i in range(n + 1):
            t = min(i * step, D)
            cur = np.array(to_img(grab(page, t)).convert("L").resize((W // 4, H // 4))).astype(np.int16)
            if prev is not None:
                if np.abs(cur - prev).mean() < 0.02:
                    still_run += step
                    if still_run > worst_run:
                        worst_run, worst_at = still_run, t
                else:
                    still_run = 0.0
            prev = cur
        add("static-stretch", "warn" if worst_run > 2.5 else "pass",
            f"longest unchanged stretch {worst_run:.1f}s (ending t={worst_at:.1f}s)" + (" — intentional hold? sabio/gobernante/ancestro allow ~1s" if worst_run > 2.5 else ""))

        # ---- contact sheet ----
        k = 12
        stamps = [D * i / (k - 1) for i in range(k)]
        if rest:
            stamps[-2] = rest
        cols = 6
        tw = 270 if W <= 1080 else 360
        th = int(tw * H / W)
        rows = (k + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (30, 30, 30))
        dr = ImageDraw.Draw(sheet)
        for i, st in enumerate(stamps):
            thumb = to_img(grab(page, st)).resize((tw, th), Image.LANCZOS)
            x, y = (i % cols) * tw, (i // cols) * (th + 22)
            sheet.paste(thumb, (x, y + 22))
            tag = f"t={st:.1f}s" + ("  (rest)" if rest and abs(st - rest) < 1e-6 else "")
            dr.text((x + 6, y + 5), tag, fill=(235, 235, 235))
        sheet.save(args.sheet)

    report = {"scene": args.scene, "size": [W, H], "duration": D, "labels": labels, "checks": checks}
    pathlib.Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    icon = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    print(f"duration {D:.2f}s  size {W}x{H}  rest={rest}")
    for c in checks:
        print(f"[{icon[c['status']]}] {c['name']}: {c['detail']}")
    print("contact sheet ->", args.sheet)
    return 1 if any(c["status"] == "fail" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
