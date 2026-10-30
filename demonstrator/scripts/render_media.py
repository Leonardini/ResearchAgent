#!/usr/bin/env python3
"""Render a demonstration page into slide-ready media.

    render_media.py DEMO.html [--out DIR] [--size 1600x900] [--theme light|dark] [--seconds 2.5]

Opens the page in headless Chrome once per step (?step=K&present=1&capture=1), saves each step
as a PNG key frame, then joins the frames into an auto-run MP4 (H.264, each step held for --seconds,
the last held twice as long) and a GIF. Needs Google Chrome and ffmpeg.

The page must follow the player template: it reads `step`, `present`, `capture` and `theme`
from the URL and exposes the number of steps in its trace.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


def chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("Google Chrome or Chromium is needed to render frames")


def step_count(html):
    m = re.search(r'<script type="application/json" id="trace">(.*?)</script>', html, re.S)
    if not m:
        sys.exit("no <script id=\"trace\"> block: is this a demonstration page?")
    return len(json.loads(m.group(1))["steps"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("demo")
    ap.add_argument("--out", help="output folder (default: media/ next to the page)")
    ap.add_argument("--size", default="1600x900")
    ap.add_argument("--theme", default="light", choices=["light", "dark"])
    ap.add_argument("--seconds", type=float, default=2.5, help="how long each step is held in the video")
    args = ap.parse_args()
    page = Path(args.demo).resolve()
    out = Path(args.out).resolve() if args.out else page.parent / "media"
    frames = out / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    n = step_count(page.read_text())
    w, h = args.size.split("x")
    for k in range(n):
        png = frames / f"step-{k + 1:02d}.png"
        url = f"{page.as_uri()}?step={k}&present=1&capture=1&theme={args.theme}"
        subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                        "--virtual-time-budget=3000", f"--screenshot={png}", url],
                       check=True, capture_output=True)
        if not png.exists() or png.stat().st_size < 2000:
            sys.exit(f"frame {k + 1} was not rendered ({png})")
        print(f"frame {k + 1}/{n}", file=sys.stderr)
    # concat list: every frame held for --seconds, the last one twice as long
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for k in range(n):
            f.write(f"file '{frames / f'step-{k + 1:02d}.png'}'\nduration {args.seconds * (2 if k == n - 1 else 1)}\n")
        f.write(f"file '{frames / f'step-{n:02d}.png'}'\n")
        listing = f.name
    stem = page.stem
    # "auto-run": the version that plays by itself, for slides; the HTML page is the clickable one.
    mp4, gif = out / f"{stem}-auto-run.mp4", out / f"{stem}-auto-run.gif"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
                    "-vf", "fps=25,format=yuv420p,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "20", str(mp4)],
                   check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing, "-vf",
                    "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse",
                    str(gif)], check=True)
    Path(listing).unlink()
    print(f"{n} key frames in {frames}\nvideo: {mp4}\nGIF: {gif}")


if __name__ == "__main__":
    main()
