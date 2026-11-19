#!/usr/bin/env python3
"""Read a reference video in numbers before imitating its feel.

    python3 -I analyze_ref.py ref.mp4 --out ana/            # writes ana/ref.json, ana/energy.png, ana/shots.png

Prints and saves:
  cuts        hard cuts (frame-difference spikes), shot lengths and how much they vary (max/min): a film cut on a
              metronome has a ratio near 1; launch films usually vary >= 4x
  stillness   share of the film where the picture barely changes (rests make the bursts land; ~1/3 is common)
  energy      motion per second, as a strip (energy.png): when the film moves and when it holds
  bursts      runs of >= 3 cuts less than 0.6 s apart (staccato hits)
  motion      median t80 of the moves (time to reach 80 % of their travel: ~.2-.3 = snaps/springs, ~.4 = power3,
              ~.7 = soft S-curves) and smear (share of moving frames that look motion-blurred)
  palette     5 dominant colours of the whole film
  shots.png   first/middle/last frame of up to 12 shots
Write the numbers into SPEC.md; they are what the new film must match. Analysis only: never copy a reference's assets.
"""
import argparse
import json
import pathlib
import subprocess
import sys

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy missing for this interpreter. Run setup.py once and use the python it prints (setup.py --print).")
from PIL import Image, ImageDraw


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out); s = j["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


def frames(path, w, h, fps):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", default="ana")
    ap.add_argument("--fps", type=float, default=15.0, help="analysis rate (default 15)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    W0, H0, src_fps, dur = probe(a.video)
    w = 192; h = max(2, int(round(w * H0 / W0 / 2)) * 2)
    F = list(frames(a.video, w, h, a.fps))
    if len(F) < 3:
        raise SystemExit("video too short to analyse")
    g = np.array([f.mean(axis=2) for f in F], np.float32)
    diff = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))                 # mean abs luma change between samples
    # hard cuts: big spike vs local median, and histogram changes too
    hist = np.array([np.histogram(f, bins=32, range=(0, 255))[0] / f.size for f in g])
    hd = np.abs(np.diff(hist, axis=0)).sum(axis=1)
    cuts = []
    for i in range(len(diff)):
        lo, hi = max(0, i - 7), min(len(diff), i + 8)
        med = float(np.median(diff[lo:hi])) + 0.5
        if diff[i] > 6 * med and diff[i] > 8 and hd[i] > 0.25:
            t = (i + 1) / a.fps
            if not cuts or t - cuts[-1] > 0.15:
                cuts.append(round(t, 2))
    edges = [0.0] + cuts + [round(len(F) / a.fps, 2)]
    shots = [round(b - a_, 2) for a_, b in zip(edges, edges[1:]) if b - a_ > 0.05]
    still = diff < 0.6
    for c in cuts:                                                     # a cut frame is not motion
        k = int(round(c * a.fps)) - 1
        if 0 <= k < len(still):
            still[k] = True
    stillness = float(still.mean())
    bursts, run = [], [cuts[0]] if cuts else []
    for c in cuts[1:]:
        if c - run[-1] < 0.6:
            run.append(c)
        else:
            if len(run) >= 3:
                bursts.append([run[0], run[-1], len(run)])
            run = [c]
    if len(run) >= 3:
        bursts.append([run[0], run[-1], len(run)])
    # moves: runs of motion between still frames (not crossing a cut); t80 = time to 80 % of the run's cumulative change
    cutset = {int(round(c * a.fps)) - 1 for c in cuts}
    t80s, i = [], 0
    while i < len(diff):
        if still[i] or i in cutset:
            i += 1; continue
        j = i
        while j < len(diff) and not still[j] and j not in cutset:
            j += 1
        seg = diff[i:j]
        if j - i >= 3:
            cum = np.cumsum(seg) / seg.sum()
            t80s.append(float(np.argmax(cum >= 0.8) + 1) / (j - i))
        i = j
    t80 = float(np.median(t80s)) if t80s else None
    # smear: in moving frames, edge energy drops vs the stillest frames (blurred motion has soft edges)
    def sharp(x): return float(np.abs(np.diff(x, axis=1)).mean() + np.abs(np.diff(x, axis=0)).mean())
    sh = np.array([sharp(x) for x in g])
    ref = np.percentile(sh[1:][still], 75) if still.any() else np.percentile(sh, 75)
    moving = ~still
    smear = float((sh[1:][moving] < 0.8 * ref).mean()) if moving.any() else 0.0
    # palette: k-means-ish via quantisation of all pixels
    px = np.concatenate([f[::4, ::4].reshape(-1, 3) for f in F[:: max(1, len(F) // 60)]])
    q = Image.fromarray(px.reshape(-1, 1, 3)).quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]; counts = sorted(q.getcolors(), reverse=True)
    palette = ["#%02x%02x%02x" % tuple(pal[c[1] * 3: c[1] * 3 + 3]) for c in counts]
    # energy strip
    secs = int(np.ceil(len(diff) / a.fps)); e = [float(diff[int(s * a.fps): int((s + 1) * a.fps)].mean()) for s in range(secs)]
    em = max(e) or 1; bw = 24; img = Image.new("RGB", (max(1, secs) * bw, 140), (18, 18, 18)); dr = ImageDraw.Draw(img)
    for s, v in enumerate(e):
        hh = int(110 * v / em); dr.rectangle([s * bw + 2, 120 - hh, s * bw + bw - 3, 120], fill=(79, 195, 247))
        if s % 5 == 0:
            dr.text((s * bw + 2, 124), f"{s}s", fill=(200, 200, 200))
    for c in cuts:
        x = int(c * bw); dr.line([x, 0, x, 118], fill=(255, 138, 80))
    img.save(out / "energy.png")
    # shot sheet
    sel = list(zip(edges, edges[1:]))[:12]; tw = 240; th = int(tw * H0 / W0)
    sheet = Image.new("RGB", (3 * tw, len(sel) * (th + 18) or 1), (18, 18, 18)); dr = ImageDraw.Draw(sheet)
    for r, (s0, s1) in enumerate(sel):
        for c, t in enumerate([s0 + 0.05, (s0 + s1) / 2, s1 - 0.07]):
            k = min(len(F) - 1, max(0, int(t * a.fps)))
            sheet.paste(Image.fromarray(F[k]).resize((tw, th)), (c * tw, r * (th + 18) + 18))
        dr.text((4, r * (th + 18) + 3), f"shot {r + 1}: {s0:.2f}-{s1:.2f}s ({s1 - s0:.2f}s)", fill=(230, 230, 230))
    sheet.save(out / "shots.png")
    res = {"video": str(a.video), "size": [W0, H0], "fps": round(src_fps, 2), "duration": round(dur, 2), "cuts": cuts, "shots": shots,
           "shot_ratio": round(max(shots) / min(shots), 1) if len(shots) > 1 else None, "stillness": round(stillness, 2),
           "bursts": bursts, "t80_median": round(t80, 2) if t80 else None, "smear": round(smear, 2), "palette": palette,
           "energy_per_s": [round(v, 2) for v in e]}
    (out / "ref.json").write_text(json.dumps(res, indent=1))
    print(f"{a.video}: {W0}x{H0} {src_fps:.0f}fps {dur:.1f}s")
    print(f"cuts {len(cuts)}  shots {len(shots)}  lengths {min(shots):.2f}-{max(shots):.2f}s (ratio {res['shot_ratio']})" if shots else "no shots")
    print(f"stillness {stillness * 100:.0f}%  bursts {bursts or 'none'}")
    print(f"motion: median t80 {res['t80_median']}  smear {smear * 100:.0f}% of moving frames")
    print(f"palette {palette}")
    print(f"-> {out}/ref.json, energy.png, shots.png")


if __name__ == "__main__":
    sys.exit(main())
