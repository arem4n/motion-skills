#!/usr/bin/env python3
"""Render a LogocodeX scene to MP4 (or a single still) by seeking its GSAP timeline frame by frame.

    python3 -I render_frames.py --scene project/scene.html --out out.mp4 --size 1080x1920 --fps 30
    python3 -I render_frames.py --scene project/scene.html --still 6.5 --out frame.png --size 1080x1080

Options:
  --query "archetype=sabio"   forwarded to the page's query string
  --crf 16                    x264 quality (lower = better; 16-18 is visually lossless for flat vector art)
Needs: playwright + Chromium (PLAYWRIGHT_BROWSERS_PATH), ffmpeg.
"""
import argparse
import math
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _scene_browser import grab, open_scene  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--still", type=float, help="render one frame at this time (seconds) as PNG instead of a video")
    ap.add_argument("--query", default="")
    ap.add_argument("--crf", type=int, default=16)
    args = ap.parse_args()
    w, h = (int(v) for v in args.size.lower().split("x"))

    with open_scene(args.scene, w, h, args.query) as (page, info, errors):
        dur = info["duration"]
        if args.still is not None:
            pathlib.Path(args.out).write_bytes(grab(page, min(args.still, dur)))
            print(f"still @ {args.still:.2f}s -> {args.out}")
            return
        n = math.floor(dur * args.fps + 1e-6) + 1                 # include the final frame (t == duration)
        ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(args.fps), "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", args.out],
            stdin=subprocess.PIPE,
        )
        for i in range(n):
            ff.stdin.write(grab(page, min(i / args.fps, dur)))
        ff.stdin.close()
        ff.wait()
        print(f"{n} frames, {dur:.2f}s @ {args.fps}fps -> {args.out}")
        if errors:
            print("page errors:", *errors, sep="\n  ")


if __name__ == "__main__":
    sys.exit(main())
