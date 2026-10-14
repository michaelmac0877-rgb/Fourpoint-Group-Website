# Four Points Group — website

Single-page marketing site for Four Points Group, a residential and commercial
hardscaping and landscaping company serving the Dallas–Fort Worth metroplex.

Plain HTML, CSS and JavaScript. No build step, no framework, no dependencies —
open `index.html` and it runs.

```
index.html              the whole page
assets/css/styles.css   all styling
assets/js/main.js       scroll effects, nav, contact form
assets/img/             logo derivatives + photography
scripts/                asset prep + local preview helpers
```

## Preview it locally

```bash
python3 scripts/serve.py        # -> http://localhost:4173
```

Opening `index.html` directly from Finder also works.

## The rotating logo

The compass mark sits in a fixed layer behind every section and rotates further
as you scroll. It runs on **CSS 3D transforms**, not Three.js — the logo is a
flat raster image rather than a vector that could be extruded, so a transformed
image is both the correct tool and dramatically cheaper.

`main.js` picks one of three tiers at runtime:

| Tier | When | Behaviour |
| --- | --- | --- |
| `full` | Desktop, motion allowed | Scroll-driven 3D rotation, eased |
| `simple` | Screens ≤ 62rem, or ≤ 2 CPU cores | Slow CSS idle spin, zero scroll work |
| `still` | `prefers-reduced-motion: reduce` | No animation |

Everything scroll-linked runs in **one** `requestAnimationFrame` loop and only
ever writes `transform`, so the work stays on the compositor. A frame-rate
watchdog samples real frame times and drops `full` → `simple` if the machine
cannot hold roughly 45fps, so a weak GPU degrades instead of stuttering.

The mark rotates mainly on the Z axis. A full `rotateY` sweep would turn the
flat image edge-on — and briefly invisible — every 90°; spinning a compass in
plane reads as intentional and never disappears.

### Never scale the mark above 1

`will-change: transform` promotes the pivot to its own compositor layer, and a
composited layer is **rastered once, at its layout size**. Scaling it past 1
does not re-raster — it stretches that cached bitmap, so the artwork visibly
degrades part-way through the rotation while looking fine at rest. This shipped
once and is exactly what "the background loses quality when it turns" meant.

So the pivot's CSS box is sized to the *largest* the mark is ever painted, and
`--logo-scale-min` (0.85) scales it down from there. One variable drives three
things that must agree:

- `.logo-stage__pivot` width — sized so `--logo-scale-min` reproduces the
  intended on-screen size (`width ÷ scale-min` = the old width).
- `@keyframes drift` — pins the mobile tier at the minimum so it matches.
- `main.js` — reads the variable back and ramps scale from it up to exactly 1.

If you change the mark's size, change the variable, not the multiplier in the
script. And don't add a `filter` to `.logo-stage__mark`: a filter forces its own
rasterised pass that the 3D transform then resamples again, compounding the
same problem.

## Replacing the photography

**The photos are placeholders.** They are stock images standing in until Four
Points has its own project shots — see `CREDITS.md`. The gallery copy says so
on the page, which is deliberate: nothing implies these are completed Four
Points projects.

To swap one in, drop a file with the same name and roughly the same dimensions
into `assets/img/` — no code changes needed:

| File | Size | Used for |
| --- | --- | --- |
| `hero-1920.jpg` / `hero-960.jpg` | 1920×1080 / 960×540 | Hero background |
| `service-residential.jpg` | 1000×750 | Residential card |
| `service-commercial.jpg` | 1000×750 | Commercial card |
| `gallery-1…6.jpg` | 900×675 | Gallery grid |

`python3 scripts/fetch_photos.py` re-downloads the current placeholders.

## Logo assets

`scripts/prep_logo.py` generates every logo derivative from the original
`four-points-group-alt-short-rules.png`. It cuts the white background in two
passes — flood-fill from the border, then clear enclosed pockets above a size
floor (the crescent inside a compass arc, plus the counters in the wordmark
letters) — and feathers the edge once. The size floor is what protects the white
marble quadrant, which is veined enough that its near-white pixels never form a
large blob.

Two parameters in there are load-bearing, and both are commented in the script:

- **Never erode/choke the alpha.** An earlier version shaved 2px to chase the
  last of the drop-shadow halo. The compass arcs are only ~30px thick at this
  resolution, so that removed better than a fifth of them and left every edge
  chewed — the mark visibly fell apart at nav size.
- **Keep `THRESH` at 236.** At 228 an extra "pocket" is detected inside the
  marble quadrant and punched straight through the artwork.

Outputs: `logo-full.png`, `logo-mark.png` / `.webp`, `logo-mark-220.png`,
`logo-mark-96.png`, and favicons. The pre-scaled marks exist because handing the
browser a 220px file to paint at 42px is a 5× downscale that aliases the thin
arcs into speckle — they are sized at roughly 2× their CSS display size instead.

### Two masters, on purpose

`assets/src/` holds both source files, and the script takes different parts from
each:

| File | Used for | Why |
| --- | --- | --- |
| `logo-group-1254.png` | The full lockup | It is the only file with the correct **GROUP** wordmark |
| `logo-4k-mark-source.png` | The compass mark + favicons | 4096px, so the mark is 2193px native instead of 674px |

The 4K file is a Higgsfield upscale of the Four Points **Flooring** logo. Its
compass mark is pixel-identical to the Group file's — verified, every differing
pixel between the two 1254px originals falls in the second wordmark line — so
the mark can safely come from it while the lockup comes from the Group master.
**Never build `logo-full.png` from the 4K source** or the site will read
FLOORING. The script enforces the split; the sanity check in `split_mark()`
will also refuse a crop that is not roughly square, which is what catches a
mis-detected gutter dragging wordmark into the mark.

The delivered mark is deliberately much smaller than the master: 1400px WebP
(what every modern browser gets) and a 900px PNG fallback. A full-resolution PNG
of this mark is over a megabyte, for an element that sits at 13% opacity behind
the content.

## Contact form

There is no backend. Submitting composes a pre-filled email and hands it to the
visitor's mail client, so the form works on static hosting with nothing to
maintain. Phone and email are also plain links, which is how most people will
actually get in touch.

To move to a real endpoint (Formspree, Netlify Forms, a serverless function),
give the `<form>` an `action` and `method` and delete the submit handler at the
bottom of `main.js`. Nothing else depends on it.

## Deploying

Any static host works — Netlify, Vercel, Cloudflare Pages, GitHub Pages, S3.
Upload the folder; there is nothing to build.

## Before it goes live

- [ ] Replace placeholder photos with real project work
- [ ] Confirm the contact email — the site uses `michael@fourpointsflooring.com`
      while the company is Four Points **Group**
- [ ] Point a form backend at a real inbox if you want submissions logged
- [ ] Add the live domain to the `og:image` meta tag as an absolute URL
- [ ] Set up Google Business Profile / analytics if wanted
