#!/usr/bin/env python3
"""Split a raster logo into semantic layers and vectorize each one to SVG path data.

Why this exists: LogocodeX logos are built from layers that carry meaning (the condor is
Manque, the mountain is Arellano AND the letter A, the tree is the lineage...). Motion graphics
need those layers as separate, crisp vector shapes so each one can be animated for a reason.

Usage:
    python3 -I split_logo_layers.py --image logo.png --config layers.config.json --out layers.json [--js layers.js] [--preview layers_preview.png]

Config (all coordinates live in a "working canvas" of `width` px wide; height follows the image ratio):
{
  "width": 2000,
  "threshold": 128,                      # luminance below this counts as ink (alpha above it in "alpha" mode)
  "mode": "luminance",                   # "alpha" for white/light logos on transparent PNGs: the opaque pixels are the ink
  "layers": [                            # processed in order; each layer claims pixels first-come
    {"name": "text", "rect": [0, 1285, 2000, 1602], "split": "components", "min_area": 5000},
    {"name": "tree", "polygon": [[x, y], ...], "rect": [x0, y0, x1, y1], "keep": "largest_component"},
    {"name": "mountain", "polygon": [...], "exclude": [{"rect": [x0, y0, x1, y1]}]},
    {"name": "condor", "rest": true, "overlap": 2}   # takes whatever ink is still unclaimed; overlap hides seams
  ]
}
A layer's `polygon` and `rect` intersect; `exclude` shapes are removed. `overlap: N` bleeds the layer N px onto
neighbouring ink so adjacent layers show no hairline seam (paint order = layer order, later layers sit on top). `split: "components"` also
returns each connected piece (e.g. the letters of a wordmark) left-to-right under `parts`.

Output JSON: {"viewBox": [0, 0, W, H], "layers": {name: {"d": svgPathData, "bbox": [x0, y0, x1, y1], "parts": [...]}}}
Paths are meant to be drawn with fill-rule="evenodd".
"""
import argparse
import json
import sys

import cv2
import numpy as np
import potrace
from PIL import Image, ImageDraw


def load_ink(path, width, threshold, mode="luminance"):
    im = Image.open(path).convert("RGBA")
    if mode == "alpha":
        # light/white logos on a transparent background: the ink IS the opaque part, whatever its colour
        height = round(im.size[1] * width / im.size[0])
        alpha = im.getchannel("A").resize((width, height), Image.LANCZOS)
        return np.array(alpha) > threshold, width, height
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)  # transparent areas count as paper, not ink
    height = round(im.size[1] * width / im.size[0])
    gray = bg.convert("L").resize((width, height), Image.LANCZOS)
    return np.array(gray) < threshold, width, height


def shape_mask(shape, w, h):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    if "polygon" in shape:
        d.polygon([tuple(p) for p in shape["polygon"]], fill=255)
    elif "rect" in shape:
        x0, y0, x1, y1 = shape["rect"]
        d.rectangle([x0, y0, x1, y1], fill=255)
    return np.array(m) > 0


def region_mask(layer, w, h):
    region = np.ones((h, w), bool)
    if "polygon" in layer:
        region &= shape_mask({"polygon": layer["polygon"]}, w, h)
    if "rect" in layer:
        region &= shape_mask({"rect": layer["rect"]}, w, h)
    for ex in layer.get("exclude", []):
        region &= ~shape_mask(ex, w, h)
    return region


def to_path(mask, tol=0.3):
    # potracer traces the *inverse* of what you pass, so hand it ~mask to get the ink outline
    curves = potrace.Bitmap(~mask).trace(turdsize=3, alphamax=1.0, opticurve=True, opttolerance=tol)
    out = []
    for c in curves:
        s = c.start_point
        out.append(f"M{s.x:.1f},{s.y:.1f}")
        for seg in c.segments:
            if seg.is_corner:
                out.append(f"L{seg.c.x:.1f},{seg.c.y:.1f}L{seg.end_point.x:.1f},{seg.end_point.y:.1f}")
            else:
                out.append(
                    f"C{seg.c1.x:.1f},{seg.c1.y:.1f} {seg.c2.x:.1f},{seg.c2.y:.1f} {seg.end_point.x:.1f},{seg.end_point.y:.1f}"
                )
        out.append("Z")
    return "".join(out)


def bbox(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return [0, 0, 0, 0]
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def components(mask, min_area):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype("uint8"), connectivity=8)
    ids = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= min_area]
    ids.sort(key=lambda i: stats[i, cv2.CC_STAT_LEFT])
    return [lab == i for i in ids]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--js", help="also write `window.LAYERS = {...}` so a scene can load it from file://")
    ap.add_argument("--preview", help="write a PNG with every layer in its own colour, to check the cuts by eye")
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    ink, w, h = load_ink(args.image, cfg.get("width", 2000), cfg.get("threshold", 128), cfg.get("mode", "luminance"))
    claimed = np.zeros_like(ink)
    result = {"viewBox": [0, 0, w, h], "layers": {}}
    palette = [(192, 57, 43), (36, 113, 163), (39, 174, 96), (142, 68, 173), (230, 126, 34), (17, 17, 17)]
    preview = np.full((h, w, 3), 255, np.uint8)

    for layer in cfg["layers"]:
        name = layer["name"]
        if layer.get("rest"):
            mask = ink & ~claimed
        else:
            mask = ink & ~claimed & region_mask(layer, w, h)
        if layer.get("keep") == "largest_component":
            n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype("uint8"), connectivity=8)
            if n > 1:
                best = max(range(1, n), key=lambda i: stats[i, cv2.CC_STAT_AREA])
                mask = lab == best
        claimed |= mask
        preview[mask] = palette[len(result["layers"]) % len(palette)]
        out_mask = mask
        if layer.get("overlap"):
            # Let this layer bleed a few px *only onto neighbouring ink*. Two vector shapes that share an edge show a
            # faint hairline from antialiasing; overlapping them hides it without thickening any stroke (white stays white).
            k = int(layer["overlap"])
            grown = cv2.dilate(mask.astype("uint8"), np.ones((3, 3), np.uint8), iterations=k) > 0
            out_mask = mask | (grown & ink)
        entry = {"d": to_path(out_mask), "bbox": bbox(out_mask)}
        if layer.get("split") == "components":
            entry["parts"] = [{"d": to_path(p), "bbox": bbox(p)} for p in components(mask, layer.get("min_area", 50))]
        result["layers"][name] = entry
        print(f"{name}: {int(mask.sum())} ink px, bbox {entry['bbox']}" + (f", {len(entry['parts'])} parts" if "parts" in entry else ""))

    if args.preview:
        Image.fromarray(preview).save(args.preview)
        print("preview ->", args.preview)
    json.dump(result, open(args.out, "w"))
    if args.js:
        open(args.js, "w").write("window.LAYERS = " + json.dumps(result) + ";\n")
    print("wrote", args.out)


if __name__ == "__main__":
    sys.exit(main())
