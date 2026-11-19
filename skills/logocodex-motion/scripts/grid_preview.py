#!/usr/bin/env python3
"""Overlay a coordinate grid on a logo so you can read polygon/rect coordinates for layers.config.json.

    python3 -I grid_preview.py --image logo.png --out grid.png [--width 2000] [--crop x0,y0,x1,y1] [--step 50]

Coordinates printed on the grid are in the working canvas (`--width` px wide, same as split_logo_layers.py's
`width`), so what you read is exactly what you type into the config. Use --crop to zoom into a region
(e.g. the area where two layers overlap) and read precise points.
"""
import argparse

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=2000)
    ap.add_argument("--crop", help="x0,y0,x1,y1 in canvas coordinates")
    ap.add_argument("--step", type=int, default=50)
    ap.add_argument("--view", type=int, default=1100, help="output image width in px")
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    S = a.width / im.size[0]
    h = round(im.size[1] * S)
    canvas = bg.convert("RGB").resize((a.width, h), Image.LANCZOS)
    x0, y0, x1, y1 = (int(v) for v in a.crop.split(",")) if a.crop else (0, 0, a.width, h)
    view = canvas.crop((x0, y0, x1, y1))
    k = a.view / view.size[0]
    view = view.resize((a.view, int(view.size[1] * k)), Image.LANCZOS)
    d = ImageDraw.Draw(view)
    for gx in range((x0 // a.step + 1) * a.step, x1, a.step):
        X = (gx - x0) * k
        major = gx % (a.step * 2) == 0
        d.line([(X, 0), (X, view.size[1])], fill=(255, 0, 0) if major else (255, 170, 170), width=1)
        if major:
            d.text((X + 2, 2), str(gx), fill=(255, 0, 0))
    for gy in range((y0 // a.step + 1) * a.step, y1, a.step):
        Y = (gy - y0) * k
        major = gy % (a.step * 2) == 0
        d.line([(0, Y), (view.size[0], Y)], fill=(0, 0, 255) if major else (170, 170, 255), width=1)
        if major:
            d.text((2, Y + 2), str(gy), fill=(0, 0, 255))
    view.save(a.out)
    print(f"canvas {a.width}x{h}; wrote {a.out}")


if __name__ == "__main__":
    main()
