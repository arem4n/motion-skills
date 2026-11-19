#!/usr/bin/env python3
"""Render a motion-studio scene to MP4 (with a synthesized sound-design track) or to a single still.

    python3 -I render.py --scene project/scene.html --out out.mp4 --size 1080x1920 --fps 30
    python3 -I render.py --scene project/scene.html --out out.mp4 --music bed.mp3        # add a music bed under the SFX
    python3 -I render.py --scene project/scene.html --out out.mp4 --audio none           # silent video
    python3 -I render.py --scene project/scene.html --still 3.2 --out frame.png
    python3 -I render.py --scene p/scene.html --out draft.mp4 --size 1920x1080 --shutter 8   # motion blur
    python3 -I render.py --scene p/scene.html --out final.mp4 --size 1920x1080 --final       # 3840x2160 @ 60 fps

--audio auto (default): if the scene registered cues with MG.cue, make_sfx.py builds a track and it is muxed in.
Frames come from seeking the paused GSAP timeline, so output is reproducible and independent of machine speed.

--shutter N   real motion blur: each MOVING frame is N seeks spread across an open shutter (--shutter-angle, default 180°)
              averaged in linear light. Still frames are detected (first vs last shutter sample) and cost 2 captures.
              Use it when anything travels > ~80 px per frame (validate.py's fast-move check tells you); CSS blur is not
              a substitute. Cost: N captures per moving frame.
--final       delivery render: 60 fps and twice the --size (1920x1080 -> 3840x2160). Only after the draft is accepted.
              Implies --shutter 6 unless --shutter is given.
--workers K   K browsers in parallel processes, each encoding a contiguous chunk; chunks are joined without re-encoding.
              Default: auto = as many as free RAM and CPUs allow. A worker (python + chromium + ffmpeg) peaks at about
              0.55 GB + 0.18 GB per megapixel (measured: 0.9 GB at 1080p, 2.0 GB at 4K), +0.15 GB when the scene has a WebGL
              canvas (MG.three: measured 1.03 GB per worker at 1080x1920 with 4 workers); 1.5 GB of RAM is always left free.
              An explicit K above what the RAM allows is lowered (this machine has hung from exactly that);
              --force-workers keeps it.
--loudness L  audio master: gain to L LUFS integrated (default -14, what the platforms normalise to) and a 4x-oversampled
              limiter at -1.5 dBTP. 'off' keeps the raw mix.
After an MP4 is written, it is checked on the file itself: black stretches (blackdetect) and the measured loudness/peak.
"""
import argparse
import collections
import concurrent.futures
import io
import json
import math
import multiprocessing as mp
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _scene_browser import grab, open_scene  # noqa: E402


def _lut():
    import numpy as np
    c = np.arange(256, dtype=np.float32) / 255
    to_lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)
    x = np.linspace(0, 1, 4096, dtype=np.float32)
    to_srgb = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return to_lin, np.clip(np.round(to_srgb * 255), 0, 255).astype(np.uint8)


def _rgb(png):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))


class _Now:
    """A finished result with the Future interface, for running the frame pipeline inline."""
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value


def _inline(fn, *args):
    return _Now(fn(*args))


def _still(a, b):
    import numpy as np
    return int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max()) <= 2


def _frame(page, t, dur, fps, shutter, angle, luts, submit=_inline):
    """One output frame -> (future of an HxWx3 uint8 array, captures). Blurred across the shutter when something moves.

    The browser is the bottleneck (~75 % of a capture), so everything else - PNG decode, the linear-light sum - goes
    through `submit`, which in a render is a one-thread FIFO queue: it works while the browser takes the next capture.
    Tasks read earlier tasks' futures; FIFO order guarantees those are done.

    With a shutter, the first and last samples are taken first: if they match, nothing moved and the frame costs 2
    captures; if not, they are already 2 of the N samples (no separate probe captures). The sum runs in sample order.
    """
    if shutter <= 1:
        png = grab(page, min(t, dur))
        return submit(_rgb, png), 1
    open_s = angle / 360.0 / fps
    ts = [min(max(t - open_s / 2 + open_s * (j + 0.5) / shutter, 0.0), dur) for j in range(shutter)]
    first = submit(_rgb, grab(page, ts[0]))
    last = submit(_rgb, grab(page, ts[-1]))
    if submit(lambda: _still(first.result(), last.result())).result():
        return first, 2
    to_lin, to_srgb = luts
    acc = submit(lambda: to_lin[first.result()])

    def add(png):
        a = acc.result()
        a += to_lin[_rgb(png)]

    for tj in ts[1:-1]:
        submit(add, grab(page, tj))

    def finish():
        import numpy as np
        a = acc.result()
        a += to_lin[last.result()]
        a /= shutter
        return to_srgb[np.clip((a * 4095).astype(np.int32), 0, 4095)]

    return submit(finish), shutter


def _encoder(path, w, h, fps, crf):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-framerate", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
        stdin=subprocess.PIPE)


def _chunk(job):
    """Worker: render frames [a, b) into its own mp4 segment."""
    scene, w, h, query, fps, a, b, dur, shutter, angle, crf, out, k = job
    luts = _lut() if shutter > 1 else None
    caps = 0
    pool = concurrent.futures.ThreadPoolExecutor(1)
    queue = collections.deque()

    def submit(fn, *args):
        f = pool.submit(fn, *args)
        queue.append(f)
        while len(queue) > 24:          # backpressure: never hold more than a couple of frames' worth of captures
            queue.popleft().result()    # (also surfaces a failed task here instead of at the end)
        return f

    with open_scene(scene, w, h, query) as (page, _info, errors):
        ff = _encoder(out, w, h, fps, crf)
        try:
            t0 = time.time()
            for i in range(a, b):
                fr, c = _frame(page, i / fps, dur, fps, shutter, angle, luts, submit)
                caps += c
                submit(lambda fr=fr: ff.stdin.write(fr.result().tobytes()))
                done = i - a + 1
                if done % 150 == 0 or i == b - 1:
                    el = time.time() - t0
                    print(f"  w{k}: {done}/{b - a} frames  {el:.0f}s  ~{el / done * (b - a - done):.0f}s left", flush=True)
            while queue:
                queue.popleft().result()
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
            ff.stdin.close(); ff.wait()
    return caps, errors


def _workers(w, h, requested, force, frames, webgl=False):
    """How many browsers to run -> (K, why). Bounded by free RAM so a render cannot take the machine down."""
    per = 0.55 + 0.18 * w * h / 1e6 + (0.15 if webgl else 0)   # GB per worker, see --workers in the module docstring
    try:
        avail = next(int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemAvailable:")) / 1048576
    except (OSError, StopIteration):
        avail = None
    by_cpu = max(1, (os.cpu_count() or 2) - 2)
    by_mem = max(1, int((avail - 1.5) / per)) if avail is not None else by_cpu
    by_len = max(1, frames // 30)                        # a chunk shorter than ~30 frames is not worth a browser
    room = f"{avail:.1f} GB free, ~{per:.1f} GB per worker" if avail is not None else "free RAM unknown"
    if requested and force:
        return max(1, min(requested, by_len)), f"forced, {room}"
    if requested:
        k = max(1, min(requested, by_mem, by_len))
        return k, (f"asked for {requested}, lowered: {room}" if k < min(requested, by_len) else room)
    return max(1, min(by_cpu, by_mem, by_len)), f"auto: {room}, {os.cpu_count()} CPUs"


TRUE_PEAK = -1.5   # dBTP ceiling after mastering; AAC adds a little on top, platforms want <= -1
COMP = "acompressor=threshold=-24dB:ratio=4:attack=0.5:release=90:knee=4"   # solo si el master simple no llega al objetivo


def _ebur128(path, extra_af=""):
    """Integrated loudness (LUFS) and true peak (dBTP) of a file's audio, measured by ffmpeg's EBU R128 meter."""
    af = (extra_af + "," if extra_af else "") + "ebur128=peak=true"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    summ = r.stderr[r.stderr.rfind("Summary:"):]
    get = lambda key: next((float(l.split()[1]) for l in summ.splitlines() if l.strip().startswith(key) and len(l.split()) > 1
                            and l.split()[1].replace(".", "").replace("-", "").isdigit()), None)
    return get("I:"), get("Peak:")


def _master(wav, target, tmp):
    """Two-step master: measure, apply the gain that lands the integrated loudness on `target`, then a 4x-oversampled
    limiter so true peaks stay under TRUE_PEAK. A plain gain + limiter (not loudnorm's dynamic mode) keeps the hits'
    shape and is deterministic. Returns the mastered wav (or the input when it is silent)."""
    i, _ = _ebur128(wav)
    if i is None or i < -70:
        print("audio master: mix is silent or below -70 LUFS, left as is")
        return wav
    gain = target - i
    lim = 10 ** (TRUE_PEAK / 20)
    out = tmp / "master.wav"
    def chain(g, comp):
        af = ((COMP + ",") if comp else "") + (f"volume={g:.2f}dB,aresample=192000,"
              f"alimiter=limit={lim:.4f}:attack=5:release=80:level=disabled:latency=1,aresample=48000")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", af, "-c:a", "pcm_s24le", str(out)], check=True)
        return _ebur128(out)
    i2, p2 = chain(gain, False)
    if i2 is not None and abs(i2 - target) > 1:
        # golpes cortos y secos (muestras reales): el limitador solo no llega. Un compresor rápido les da cuerpo
        # (baja la diferencia pico/medio) y se reajusta la ganancia hasta 3 veces. Determinista.
        ic, _ = _ebur128(wav, COMP)
        gain = target - (ic if ic is not None else i)
        for _step in range(3):
            i2, p2 = chain(gain, True)
            if i2 is None or abs(i2 - target) <= 0.5:
                break
            gain += target - i2
    print(f"audio master: {i:.1f} -> {i2:.1f} LUFS (target {target:g}), true peak {p2:.1f} dBTP")
    return out


def _qa(mp4, loudness):
    """Checks on the delivered file itself: blank (black) stretches and, if it has audio, loudness and true peak."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-vf", "blackdetect=d=0.25:pix_th=0.06",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    blacks = [l.split("blackdetect")[1].strip(" ]") for l in r.stderr.splitlines() if "black_start" in l]
    print("qa black frames: " + ("none" if not blacks else "WARN " + "; ".join(blacks) + " (fine only if intended, e.g. a fade from black)"))
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", mp4],
                               capture_output=True, text=True).stdout.strip()
    if not has_audio:
        return
    i, p = _ebur128(mp4)
    msg = f"qa audio: {i:.1f} LUFS, true peak {p:.1f} dBTP"
    if loudness != "off" and (abs(i - float(loudness)) > 1 or p > -1.0):
        msg += "  WARN off target (the mix may be clipping or very peaky: lower --sfx-gain or the music and render again)"
    print(msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--still", type=float)
    ap.add_argument("--query", default="")
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--audio", choices=["auto", "none"], default="auto")
    ap.add_argument("--music")
    ap.add_argument("--music-gain", type=float, default=-18.0)
    ap.add_argument("--sfx-gain", type=float, default=0.0)
    ap.add_argument("--sfx-source", choices=["auto", "synth", "samples"], default="auto", help="auto: muestras CC0 reales donde hay, sintético donde no")
    ap.add_argument("--shutter", type=int, help="motion-blur samples per moving frame (0/1 = off; 6-10 typical)")
    ap.add_argument("--shutter-angle", type=float, default=180.0)
    ap.add_argument("--final", action="store_true", help="60 fps at twice --size")
    ap.add_argument("--workers", type=int, default=0, help="parallel browsers (default 0 = auto, from free RAM and CPUs)")
    ap.add_argument("--force-workers", action="store_true", help="use --workers as given even if free RAM does not allow it")
    ap.add_argument("--loudness", default="-14", help="integrated LUFS target for the audio master (default -14, what "
                    "YouTube/TikTok/Instagram normalise to); 'off' keeps the raw mix")
    a = ap.parse_args()
    if a.loudness != "off":
        try:
            float(a.loudness)
        except ValueError:
            ap.error("--loudness must be a number (LUFS) or 'off'")
    w, h = (int(v) for v in a.size.lower().split("x"))
    fps, shutter = a.fps, a.shutter
    if a.final:
        w, h, fps = w * 2, h * 2, 60
        if shutter is None:
            shutter = 6
    shutter = shutter or 0

    with open_scene(a.scene, w, h, a.query) as (page, info, errors):
        dur = info["duration"]
        if a.still is not None:
            if shutter > 1:
                from PIL import Image
                fr, _ = _frame(page, a.still, dur, fps, shutter, a.shutter_angle, _lut())
                Image.fromarray(fr.result()).save(a.out)
            else:
                pathlib.Path(a.out).write_bytes(grab(page, min(a.still, dur)))
            print(f"still @ {a.still:.2f}s -> {a.out}")
            return
        stepped = page.evaluate("window.__stepped || 0")
        webgl = bool(page.evaluate("document.querySelectorAll('canvas.mg-three').length"))
    n = math.floor(dur * fps + 1e-6) + 1
    K, why = _workers(w, h, a.workers, a.force_workers, n, webgl)
    print(f"{n} frames {w}x{h} @ {fps}fps, shutter {shutter or 'off'}, {K} worker(s) ({why})" + (f", stepped {stepped} fps" if stepped else ""), flush=True)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ms-render-"))
    try:
        bounds = [round(n * i / K) for i in range(K + 1)]
        jobs = [(a.scene, w, h, a.query, fps, bounds[i], bounds[i + 1], dur, shutter, a.shutter_angle, a.crf, str(tmp / f"seg{i:02d}.mp4"), i)
                for i in range(K)]
        t0 = time.time()
        if K == 1:
            res = [_chunk(jobs[0])]
        else:
            with mp.get_context("spawn").Pool(K) as pool:
                res = pool.map(_chunk, jobs)
        caps = sum(r[0] for r in res)
        errs = [e for r in res for e in r[1]]
        print(f"{n} frames, {dur:.2f}s @ {fps}fps  ({caps} captures, {time.time() - t0:.0f}s)")
        if errs:
            print("page errors:", *sorted(set(errs)), sep="\n  ")
        silent = tmp / "video.mp4"
        if K == 1:
            shutil.move(jobs[0][11], silent)
        else:
            lst = tmp / "list.txt"
            lst.write_text("".join(f"file '{j[11]}'\n" for j in jobs))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                            "-movflags", "+faststart", str(silent)], check=True)
        if a.audio == "none" or not (info["cues"] or a.music):
            shutil.move(str(silent), a.out)
        else:
            cues = tmp / "cues.json"; cues.write_text(json.dumps(info["cues"]))
            wav = tmp / "sfx.wav"
            cmd = [sys.executable, "-I", str(pathlib.Path(__file__).parent / "make_sfx.py"), "--cues", str(cues), "--duration", f"{dur:.3f}",
                   "--out", str(wav), "--sfx-gain", str(a.sfx_gain), "--sfx-source", a.sfx_source]
            if a.music:
                cmd += ["--music", a.music, "--music-gain", str(a.music_gain)]
            subprocess.run(cmd, check=True)
            if a.loudness != "off":
                wav = _master(wav, float(a.loudness), tmp)
            # -t, not -shortest: with the video copied, -shortest ended the file ~0.13 s before the last frame (979 frames in,
            # 975 out, audio 32.6 s vs video 32.63 s). -t keeps every frame and still trims an audio that runs longer.
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                            "-t", f"{n / fps:.4f}", "-movflags", "+faststart", a.out], check=True)
        print("->", a.out)
        _qa(a.out, a.loudness)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
