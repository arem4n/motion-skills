#!/usr/bin/env python3
"""Measure the real palette of an image (logo, screenshot, product photo, reference frame) instead of guessing it.

    python3 -I measure_palette.py image.png [--k 5] [--json out.json]

Prints dominant colours (k-means in Lab, deterministic seed), their share, and a suggested token set:
bg (darkest or lightest large area), fg (best contrast against bg), accent (most saturated colour with enough share),
muted. Transparent pixels are ignored. Paste the result into tokens.js / CONTENT.colors of the project.
Idea borrowed from Design DNA: measure, never eyeball.
"""
import argparse
import json

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy missing for this interpreter (-I hides user packages). Run setup.py once and use the python it prints (setup.py --print).")
from PIL import Image


def srgb2lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def rgb2lab(rgb):
    l = srgb2lin(rgb.astype(float))
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = l @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def lum(rgb):
    l = srgb2lin(np.array(rgb, float)); return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]


def contrast(a, b):
    x, y = sorted([lum(a), lum(b)], reverse=True); return (x + 0.05) / (y + 0.05)


def hexs(c): return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("image"); ap.add_argument("--k", type=int, default=6); ap.add_argument("--json")
    a = ap.parse_args()
    im = Image.open(a.image).convert("RGBA"); im.thumbnail((200, 200))
    px = np.array(im).reshape(-1, 4); px = px[px[:, 3] > 200][:, :3]
    if len(px) == 0:
        raise SystemExit("image is fully transparent")
    lab = rgb2lab(px); rng = np.random.RandomState(7)
    cen = lab[rng.choice(len(lab), a.k, replace=False)]
    for _ in range(25):
        lbl = np.argmin(((lab[:, None] - cen[None]) ** 2).sum(-1), axis=1)
        new = np.array([lab[lbl == i].mean(0) if (lbl == i).any() else cen[i] for i in range(a.k)])
        if np.allclose(new, cen, atol=0.05): break
        cen = new
    out = []
    for i in range(a.k):
        m = lbl == i
        if not m.any(): continue
        rgb = px[m].mean(0); chroma = float(np.hypot(*cen[i][1:]))
        out.append({"hex": hexs(rgb), "share": round(float(m.mean()), 3), "chroma": round(chroma, 1), "L": round(float(cen[i][0]), 1), "rgb": rgb})
    out.sort(key=lambda d: -d["share"])
    big = [d for d in out if d["share"] >= 0.04] or out
    bg = max(big[:2], key=lambda d: d["share"])
    fg = max(out, key=lambda d: contrast(d["rgb"], bg["rgb"]))
    cand = [d for d in big if d is not bg and contrast(d["rgb"], bg["rgb"]) >= 3] or [d for d in out if d is not bg]
    accent = max(cand, key=lambda d: d["chroma"]) if cand else fg
    sug = {"bg": bg["hex"], "fg": fg["hex"], "accent": accent["hex"], "muted": hexs((np.array(bg["rgb"]) * 0.45 + np.array(fg["rgb"]) * 0.55)),
           "contrast_fg_bg": round(contrast(fg["rgb"], bg["rgb"]), 2), "contrast_accent_bg": round(contrast(accent["rgb"], bg["rgb"]), 2)}
    for d in out: d.pop("rgb")
    res = {"palette": out, "suggested": sug}
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.json: open(a.json, "w").write(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
