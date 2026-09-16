#!/usr/bin/env python3
"""
Prepare the Four Points Group logo for the web.

The source logo ships on solid white with a soft drop shadow. Getting a clean
cutout takes two passes, because a naive "white -> transparent" would punch
holes straight through the white marble quadrant:

  1. Flood-fill inwards from the border to clear the outer background.
  2. Clear *enclosed* near-white regions above a size floor -- the crescent
     trapped between a compass arc and the diamond, plus the counters inside the
     wordmark letters. The size floor is what protects the marble: marble is
     heavily veined (luminance ranges the full 0-255), so its near-white pixels
     only ever form small scattered specks, never a large blob.

Then feather the cut edge, once, and stop.

Do NOT choke/erode the alpha to chase the last of the drop-shadow halo. An
earlier revision eroded 2px and it visibly disfigured the mark: the compass arcs
are only ~30px thick at this resolution, so 2px off each side removed better
than a fifth of them and left every edge chewed. THRESH is low enough that the
remaining fringe is negligible.

The threshold is likewise not a free parameter. At 236 the six cleared pockets
are the one crescent and five letter counters. Drop it to 228 and a seventh
pocket appears at (648,342)-(698,455) -- inside the marble quadrant -- which
punches a hole straight through the artwork.

Outputs (assets/img/):
  logo-full.png      full lockup, transparent
  logo-mark.png      compass mark only, transparent, padded square
  logo-mark.webp     same, ~1/7th the weight, for the big parallax element
  logo-mark-220.png  pre-scaled for the ~84px service-area compass
  logo-mark-96.png   pre-scaled for the ~42px nav/footer lockups
  favicon-*.png      square mark at favicon sizes

The pre-scaled variants matter: handing the browser a 220px file to paint at
42px is a 5x downscale and it aliases the thin arcs into speckle. Downsample
properly here with LANCZOS instead.
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

# Gaussian radius used to soften the cut edge. Applied exactly once.
FEATHER = 0.5


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
    # Soften the cut edge once, here. Everything downstream is a crop or a
    # resize of this one buffer, so no region gets filtered twice.
    alpha = alpha.filter(ImageFilter.GaussianBlur(FEATHER))

    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)

    os.makedirs(OUT_DIR, exist_ok=True)

    full = rgba.crop(rgba.getbbox())
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

    # Plain crop -- the alpha was already feathered above, so no second filter.
    mark_raw = full.crop((0, 0, fw, gutter))
    mark = square(mark_raw.crop(mark_raw.getbbox()))
    mark.save(os.path.join(OUT_DIR, "logo-mark.png"), optimize=True)
    # WebP for the big parallax element -- roughly a seventh of the PNG's weight.
    mark.save(os.path.join(OUT_DIR, "logo-mark.webp"), quality=88, method=6)

    # Pre-scaled lockup marks. Roughly 2x their CSS display size so retina is
    # covered without asking the browser to do a large downscale itself.
    for px in (220, 96):
        mark.resize((px, px), Image.LANCZOS).save(
            os.path.join(OUT_DIR, f"logo-mark-{px}.png"), optimize=True
        )
    print(f"logo-mark: {mark.size} (+ .webp, + 220px, + 96px)")

    for size in (32, 180, 512):
        ico = mark.resize((size, size), Image.LANCZOS)
        ico.save(os.path.join(OUT_DIR, f"favicon-{size}.png"), optimize=True)
    print("favicons: 32, 180, 512")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
