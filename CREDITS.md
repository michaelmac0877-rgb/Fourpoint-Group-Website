# Image credits

## Logo

`assets/img/logo-*.png|webp` and `favicon-*.png` are derived from the client's
own logo artwork in `assets/src/`, by `scripts/prep_logo.py`.

- `logo-group-1254.png` — the supplied Four Points Group lockup (1254px).
- `logo-4k-mark-source.png` — the Four Points Flooring logo enlarged to 4096px
  with [Higgsfield](https://higgsfield.ai) (ByteDance upscale model). Used only
  as a higher-resolution source for the compass mark, which is pixel-identical
  between the two lockups. The upscale was checked against the original before
  use: silhouette IoU 0.977 and mean pixel difference 1.83 over the mark, i.e.
  sharper detail with no change to the artwork's geometry.

No AI-generated artwork appears in the logo — the upscale enhances the client's
existing mark, it does not redraw it.

## Placeholder photography

Every `.jpg` in `assets/img/` is **temporary stock photography** standing in
until Four Points Group has photographs of its own completed projects. None of
these images depict Four Points Group work, and the page says so in the gallery
section.

Source: [Unsplash](https://unsplash.com). The [Unsplash
License](https://unsplash.com/license) permits free commercial use without
attribution; credited here anyway as good practice.

| File | Unsplash photo ID |
| --- | --- |
| `hero-1920.jpg`, `hero-960.jpg` | `photo-1778869290979-6f09567a0eee` |
| `service-residential.jpg` | `photo-1694885186013-5aa7d91ae5d5` |
| `service-commercial.jpg` | `photo-1700689807667-82630348b301` |
| `gallery-1.jpg` | `photo-1782914674090-e137795d8dc3` |
| `gallery-2.jpg` | `photo-1761637823941-0ffae96ec487` |
| `gallery-3.jpg` | `photo-1762117361035-5cd4f9c24795` |
| `gallery-4.jpg` | `photo-1501668343018-9234e3ee801a` |
| `gallery-5.jpg` | `photo-1780337675943-f63d92324e7b` |
| `gallery-6.jpg` | `photo-1777666145684-209b6a390f83` |

Each resolves to `https://images.unsplash.com/<id>`. Re-download them all with
`python3 scripts/fetch_photos.py`.

## Fonts

Montserrat and Inter, served from Google Fonts under the SIL Open Font License.
