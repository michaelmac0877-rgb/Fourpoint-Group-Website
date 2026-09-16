#!/usr/bin/env python3
"""
Download the placeholder stock photography into assets/img/.

These are Unsplash photos standing in until Four Points has its own completed
project shots. The Unsplash License allows commercial use without attribution;
CREDITS.md records the sources anyway. Swap any file here for a real project
photo of the same dimensions and the page picks it up with no code changes.

Re-run:  python3 scripts/fetch_photos.py
"""

import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "img")
CTX = ssl.create_default_context()

# name -> (unsplash photo id, width, height)
PHOTOS = {
    # Hero, served at two widths for mobile.
    "hero-1920":           ("1778869290979-6f09567a0eee", 1920, 1080),
    "hero-960":            ("1778869290979-6f09567a0eee", 960, 540),

    # Services split
    "service-residential": ("1694885186013-5aa7d91ae5d5", 1000, 750),
    "service-commercial":  ("1700689807667-82630348b301", 1000, 750),

    # Gallery
    "gallery-1": ("1782914674090-e137795d8dc3", 900, 675),  # stone wall + fire
    "gallery-2": ("1761637823941-0ffae96ec487", 900, 675),  # retaining wall
    "gallery-3": ("1762117361035-5cd4f9c24795", 900, 675),  # outdoor kitchen
    "gallery-4": ("1501668343018-9234e3ee801a", 900, 675),  # paver walkway
    "gallery-5": ("1780337675943-f63d92324e7b", 900, 675),  # patio string lights
    "gallery-6": ("1777666145684-209b6a390f83", 900, 675),  # commercial plaza
}


def grab(item):
    name, (pid, w, h) = item
    path = os.path.join(OUT, f"{name}.jpg")
    # Default (centre) crop -- `crop=entropy` re-frames onto whatever it scores
    # as busiest, which zoomed these shots well past the composition we chose.
    url = (f"https://images.unsplash.com/photo-{pid}"
           f"?w={w}&h={h}&fit=crop&q=80&fm=jpg")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=60, context=CTX).read()
        with open(path, "wb") as f:
            f.write(data)
        return f"  {name}.jpg  {w}x{h}  {len(data)//1024} KB"
    except Exception as e:
        return f"  !! {name}: {e}"


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"fetching {len(PHOTOS)} photos -> assets/img/")
    with ThreadPoolExecutor(max_workers=8) as ex:
        for line in ex.map(grab, PHOTOS.items()):
            print(line)


if __name__ == "__main__":
    main()
