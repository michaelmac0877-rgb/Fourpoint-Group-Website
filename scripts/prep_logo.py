#!/usr/bin/env python3
"""
Prepare the Four Points Group logo for the web.

The source logo ships on solid white with a soft drop shadow. Getting a clean
cutout takes three passes, because a naive "white -> transparent" would punch
holes straight through the white marble quadrant:

  1. Flood-fill inwards from the border to clear the outer background.
  2. Clear *enclosed* near-white regions above a size floor -- the two crescents
     trapped between the compass arcs and the diamond, plus the counters inside
     the wordmark letters. The size floor is what protects the marble: marble is
     heavily veined (luminance ranges the full 0-255), so its near-white pixels
     only ever form small scattered specks, never a large blob.
  3. Choke the edge inwards a touch to eat the drop-shadow halo, then feather.

Outputs (assets/img/):
  logo-full.png   full lockup, transparent
  logo-mark.png   compass mark only, transparent, padded square
  favicon-*.png   square mark at favicon sizes
"""

from collections import deque
import os
import sys

from PIL import Image, ImageFilter

SRC = os.path.expanduser("~/Downloads/four-points-group-alt-short-rules.png")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "img")

# Near-white cutoff. Low enough to swallow the drop-shadow fringe, high enough
# that the veined marble and brushed concrete quadrants stay well clear of it.
THRESH = 236

# Enclosed white regions smaller than this are texture specks inside the stone
# and must stay opaque; anything larger is genuine background showing through.
MIN_HOLE = 400


def near_white(px):
    r, g, b = px
    return r >= THRESH and g >= THRESH and b >= THRESH


def cut_background(img):
    """Return an L mask: 0 where background (outer + enclosed) should be."""
    w, h = img.size
    data = list(img.getdata())
    n = w * h

    keep = bytearray(b"\x01" * n)  # 1 = opaque
    seen = bytearray(n)

    def neighbours(i):
        x, y = i % w, i // w
        if x > 0:
            yield i - 1
        if x < w - 1:
            yield i + 1
        if y > 0:
            yield i - w
        if y < h - 1:
            yield i + w

    def flood(start):
        """Collect one near-white connected component from `start`."""
        dq = deque([start])
        seen[start] = 1
        cells = []
        while dq:
            i = dq.popleft()
            cells.append(i)
            for j in neighbours(i):
                if not seen[j] and near_white(data[j]):
                    seen[j] = 1
                    dq.append(j)
        return cells

    # Pass 1 -- outer background, seeded from every border pixel.
    outer = 0
    for i in [x for x in range(w)] + [(h - 1) * w + x for x in range(w)] + \
             [y * w for y in range(h)] + [y * w + w - 1 for y in range(h)]:
        if not seen[i] and near_white(data[i]):
            for c in flood(i):
                keep[c] = 0
                outer += 1

    # Pass 2 -- enclosed pockets (arc crescents, letter counters).
    holes = 0
    for i in range(n):
        if seen[i] or not near_white(data[i]):
            continue
        cells = flood(i)
        if len(cells) >= MIN_HOLE:
            for c in cells:
                keep[c] = 0
            holes += 1

    print(f"  cleared {outer} outer px, {holes} enclosed pocket(s)")

    alpha = Image.new("L", (w, h))
    alpha.putdata([255 if k else 0 for k in keep])
    return alpha


def finish(rgba, choke, feather=0.8):
    """Choke the alpha inwards by `choke` px to kill the shadow halo."""
    a = rgba.getchannel("A")
    if choke:
        a = a.filter(ImageFilter.MinFilter(choke * 2 + 1))
    a = a.filter(ImageFilter.GaussianBlur(feather))
    out = rgba.copy()
    out.putalpha(a)
    return out.crop(out.getbbox())


def square(im):
    side = max(im.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def main():
    if not os.path.exists(SRC):
        print(f"missing source logo: {SRC}", file=sys.stderr)
        return 1

    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    print(f"source: {w}x{h}")

    alpha = cut_background(img)
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)

    os.makedirs(OUT_DIR, exist_ok=True)

    # Full lockup: the wordmark strokes are thin, so only a 1px choke.
    full = finish(rgba, choke=1)
    full.save(os.path.join(OUT_DIR, "logo-full.png"))
    print(f"logo-full.png: {full.size}")

    # Split the mark off the wordmark. Measured on the cleaned lockup, the
    # layout is three stacked blocks -- mark, "FOUR POINTS", "GROUP" -- divided
    # by two equally wide empty bands, so we take the *earliest* widest band.
    # (Measuring on the raw mask instead would find the thin light seam between
    # the four quadrants and cut the mark in half.)
    fw, fh = full.size
    fa = list(full.getchannel("A").getdata())
    rows = [any(fa[y * fw + x] > 8 for x in range(fw)) for y in range(fh)]

    runs, start = [], None
    for y in range(fh):
        if not rows[y] and start is None:
            start = y
        elif rows[y] and start is not None:
            runs.append((start, y, y - start))
            start = None
    runs = [r for r in runs if r[2] >= 5]
    if not runs:
        print("!! could not separate mark from wordmark", file=sys.stderr)
        return 1

    widest = max(r[2] for r in runs)
    lo, hi, span = next(r for r in runs if r[2] == widest)
    gutter = (lo + hi) // 2
    print(f"mark/wordmark gutter at y={gutter} of {fh} ({span}-row band)")

    # Mark shapes are chunky, so one more choke pass is safe and tidies the edge.
    mark = square(finish(full.crop((0, 0, fw, gutter)), choke=1))
    mark.save(os.path.join(OUT_DIR, "logo-mark.png"), optimize=True)
    # WebP for the big parallax element -- roughly a fifth of the PNG's weight.
    mark.save(os.path.join(OUT_DIR, "logo-mark.webp"), quality=88, method=6)
    # Small raster for the nav and footer lockups.
    mark.resize((220, 220), Image.LANCZOS).save(
        os.path.join(OUT_DIR, "logo-mark-220.png"), optimize=True
    )
    print(f"logo-mark: {mark.size} (+ .webp, + 220px)")

    for size in (32, 180, 512):
        ico = mark.resize((size, size), Image.LANCZOS)
        ico.save(os.path.join(OUT_DIR, f"favicon-{size}.png"), optimize=True)
    print("favicons: 32, 180, 512")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
