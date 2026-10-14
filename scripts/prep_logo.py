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

The threshold is likewise not a free parameter. At 236 the cleared pockets are
the one crescent and the letter counters. Drop it to 228 and an extra pocket
appears inside the marble quadrant, punching a hole through the artwork.

TWO SOURCES, deliberately
-------------------------
assets/src/ holds both masters:

  logo-group-1254.png       the real Four Points *Group* lockup, 1254px.
  logo-4k-mark-source.png   a 4096px Higgsfield upscale, used for the mark only.

The 4K file carries the Four Points *Flooring* wordmark, not Group -- but its
compass mark is pixel-identical to the Group file's (verified: every differing
pixel between the two 1254px originals falls in the second wordmark line). So we
take the mark from the high-resolution file and the lockup from the Group file.
Never build logo-full.png from the 4K source or the site will say FLOORING.

Outputs (assets/img/):
  logo-full.png      full lockup, transparent          <- from the Group master
  logo-mark.png      compass mark, transparent, square <- from the 4K master
  logo-mark.webp     same, far lighter, for the big parallax element
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

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "src")
SRC_LOCKUP = os.path.join(SRC_DIR, "logo-group-1254.png")
SRC_MARK = os.path.join(SRC_DIR, "logo-4k-mark-source.png")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "img")

# Near-white cutoff. Low enough to swallow the drop-shadow fringe, high enough
# that the veined marble and brushed concrete quadrants stay well clear of it.
THRESH = 236

# Enclosed white regions smaller than this are texture specks inside the stone
# and must stay opaque; anything larger is genuine background showing through.
# Calibrated at 1254x1254 and scaled by area, since the two masters differ in
# resolution by 3.3x -- a fixed pixel count would start eating marble speckle on
# the 4K file.
MIN_HOLE_AT_1254 = 400


def min_hole_for(size):
    w, h = size
    return max(64, round(MIN_HOLE_AT_1254 * (w * h) / (1254 * 1254)))

# Gaussian radius used to soften the cut edge. Applied exactly once.
FEATHER = 0.5

# Delivered size of the big parallax mark. WebP is what essentially every
# browser actually gets, so it carries the resolution; the PNG is a fallback for
# the rare client without WebP and is kept deliberately smaller, because a
# full-size PNG of this mark is over a megabyte.
DELIVER_WEBP_PX = 1400
DELIVER_PNG_PX = 900
WEBP_QUALITY = 84


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

    # Pass 2 -- enclosed pockets (arc crescent, letter counters).
    min_hole = min_hole_for(img.size)
    pockets = []
    for i in range(n):
        if seen[i] or not near_white(data[i]):
            continue
        cells = flood(i)
        if len(cells) >= min_hole:
            xs = [c % w for c in cells]
            ys = [c // w for c in cells]
            pockets.append((len(cells), min(xs), min(ys), max(xs), max(ys)))
            for c in cells:
                keep[c] = 0

    print(f"  cleared {outer} outer px, {len(pockets)} pocket(s) "
          f"(min_hole={min_hole})")
    # Printed so a bad threshold is obvious: every pocket should sit either in
    # the wordmark band or on the compass ring. One inside a stone quadrant
    # means the cut is eating the artwork.
    for area, x0, y0, x1, y1 in sorted(pockets, reverse=True):
        print(f"    pocket {area:>7} px at ({x0},{y0})-({x1},{y1})")

    alpha = Image.new("L", (w, h))
    alpha.putdata([255 if k else 0 for k in keep])
    return alpha


def square(im):
    side = max(im.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def cutout(path):
    """Load a master and return it as RGBA with the white background removed."""
    img = Image.open(path).convert("RGB")
    print(f"{os.path.basename(path)}: {img.size[0]}x{img.size[1]}")
    alpha = cut_background(img)
    # Soften the cut edge once, here. Everything downstream is a crop or a
    # resize of this one buffer, so no region gets filtered twice.
    alpha = alpha.filter(ImageFilter.GaussianBlur(FEATHER))
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba.crop(rgba.getbbox())


def split_mark(lockup):
    """Crop the compass mark off the top of a cleaned lockup.

    The layout is three stacked blocks -- mark, "FOUR POINTS", and the second
    wordmark line -- separated by empty bands. The mark is always the top block,
    so we want the FIRST real band.

    Two traps, both of which have bitten this function:

      * The thin light seam between the four quadrants also reads as empty, so a
        naive "first empty row" cuts the mark in half. Hence a minimum band
        height -- scaled by resolution, because at 4096px that seam is 3x taller
        than it was at 1254px and sails past a fixed 5px floor.
      * The two wordmark bands are not always the same height, so "tallest band"
        picks the gap between the two text lines on some masters and drags the
        word FOUR POINTS into the mark. Hence "first band within 60% of the
        tallest" rather than the tallest outright.
    """
    fw, fh = lockup.size
    fa = list(lockup.getchannel("A").getdata())
    rows = [any(fa[y * fw + x] > 8 for x in range(fw)) for y in range(fh)]

    runs, start = [], None
    for y in range(fh):
        if not rows[y] and start is None:
            start = y
        elif rows[y] and start is not None:
            runs.append((start, y, y - start))
            start = None

    min_span = max(5, round(5 * fw / 1254))
    runs = [r for r in runs if r[2] >= min_span]
    print(f"  bands (min {min_span}px): {[(r[0], r[2]) for r in runs]}")
    if not runs:
        return None

    widest = max(r[2] for r in runs)
    lo, hi, span = next(r for r in runs if r[2] >= 0.6 * widest)
    gutter = (lo + hi) // 2
    print(f"  gutter at y={gutter} of {fh} ({span}-row band)")

    raw = lockup.crop((0, 0, fw, gutter))
    mark = raw.crop(raw.getbbox())

    # The compass mark is square to within a few percent. Anything far off means
    # we cut at the wrong band and have dragged wordmark into it.
    ratio = mark.width / mark.height
    if not 0.9 <= ratio <= 1.1:
        print(f"!! mark is {mark.width}x{mark.height} (ratio {ratio:.2f}) -- "
              f"wrong gutter, wordmark likely included", file=sys.stderr)
        return None

    return square(mark)


def main():
    for p in (SRC_LOCKUP, SRC_MARK):
        if not os.path.exists(p):
            print(f"missing source: {p}", file=sys.stderr)
            return 1

    os.makedirs(OUT_DIR, exist_ok=True)

    # --- lockup, from the Group master (correct wordmark) ------------------
    full = cutout(SRC_LOCKUP)
    full.save(os.path.join(OUT_DIR, "logo-full.png"))
    print(f"logo-full.png: {full.size}")

    # --- mark, from the 4K master (same artwork, 3.3x the detail) ----------
    hires = cutout(SRC_MARK)
    mark = split_mark(hires)
    if mark is None:
        print("!! could not separate mark from wordmark", file=sys.stderr)
        return 1

    # Ship the mark well below master resolution. The parallax element is capped
    # in CSS and peaks near 1.18x scale, so ~1400px covers a 2x display; past
    # that it is download weight for detail that sits at 13% opacity behind the
    # content and cannot be seen.
    def shrink(px):
        return mark if mark.width <= px else mark.resize((px, px), Image.LANCZOS)

    shrink(DELIVER_WEBP_PX).save(
        os.path.join(OUT_DIR, "logo-mark.webp"),
        quality=WEBP_QUALITY, method=6,
    )
    shrink(DELIVER_PNG_PX).save(
        os.path.join(OUT_DIR, "logo-mark.png"), optimize=True
    )
    print(f"  master {mark.size[0]}px -> webp {DELIVER_WEBP_PX}px, "
          f"png {DELIVER_PNG_PX}px")

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
