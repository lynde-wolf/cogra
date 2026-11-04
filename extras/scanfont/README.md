# Schola Scan & Heros Scan (and Soft)

The 1-bit archival-scan texture from `cogra.wear` (`--look scan`), baked into
installable TTF fonts for PowerPoint, Keynote, Canva, Word, etc.

- **Schola Scan**: TeX Gyre Schola (Century Schoolbook), the serif face of the
  mid-century text pages.
- **Heros Scan**: TeX Gyre Heros (Helvetica), the sans face of the figure labels,
  like 1980s PDP-era figures.
- **Schola Scan Soft / Heros Scan Soft**: the same letters with a faint, uneven
  grey bleed on parts of their edges (see [Soft](#soft)).

## Files

- `fonts/ScholaScan-{Regular,Italic,Bold,BoldItalic}.ttf`: the serif family, four styles.
- `fonts/HerosScan-{Regular,Italic,Bold,BoldItalic}.ttf`: the sans family, four styles.
- `fonts/ScholaScanSoft-*.ttf`, `fonts/HerosScanSoft-*.ttf`: the Soft families, four styles each.

  All 16 fonts are ready to install; there is nothing to build. Rebuild only
  to change the settings (see *Knobs*).
- `build_scan_font.py`: rebuilds them from `../../src/cogra/fonts/texgyreschola-*.otf` / `texgyreheros-*.otf`
  (Heros v2.004 from CTAN, `fonts/tex-gyre/opentype`).
- `specimen.html`: preview page (serve this folder to view it); a
  checkbox switches to the Soft families.
- `GUST-FONT-LICENSE.txt`: license, inherited from TeX Gyre.

## Installing

- **Mac:** double-click each `.ttf` and click *Install Font* (or drag them into Font Book).
  Restart PowerPoint, then pick **Schola Scan** or **Heros Scan**. Bold and italic work with ⌘B / ⌘I.
- **Canva:** needs Canva Pro (or Teams/Edu). Go to *Brand* → *Brand Kit* → *Fonts* → *Upload a font*,
  and upload all four files of each family.
- **Sending a deck:** recipients need the font too, or embed it
  (PowerPoint → Preferences → Save → *Embed fonts in the file*).

## How it works

Each glyph is rendered at 432 px/em and run through the same steps as
the scan look in `cogra.wear`: a slight edge wobble, blurring plus a noisy
threshold (copy fill-in), and a letter-scale threshold field so some letters
come out heavier than others. Each glyph is then sampled down to a 36 px/em
1-bit grid and traced along the pixel edges, so the stair-stepped edges stay
crisp at any size. Kerning and the f-ligatures come from the source font.

Every glyph has 3 noise variants. An OpenType `calt` feature rotates through them
along a line, so repeated letters do not look stamped. Browsers and Keynote
apply `calt` by default. PowerPoint and Canva may not, in which case every
letter uses variant 0, which still looks scanned.

## Soft

```bash
python3 build_scan_font.py --soft                  # Schola Scan Soft
python3 build_scan_font.py --soft --family heros   # Heros Scan Soft
```

The 1-bit glyphs are exactly those of Schola Scan / Heros Scan. Some edge
pixels next to them get a grey bleed: one scanner pixel wide, mostly on the
lower-right side of strokes (like a slight press shadow), broken up by fine
noise so long stretches of edge stay crisp, and in two greys (17% and 30%
of a warm black). Only pixels that share a side with the ink can bleed,
not ones that touch it only at a corner, so corners stay round.

A font outline can only be solid, so the greys are colour-font layers
(OpenType COLR v0 with a CPAL palette) drawn under the glyph.

| where | result |
|---|---|
| Chrome, Edge, Firefox; macOS apps that use Core Text (Keynote, Pages) | the grey bleed is drawn (tested in Chromium and Core Text) |
| Windows (DirectWrite), Safari, PowerPoint, Word, Canva | expected to work, not tested |
| apps without colour-font support | the plain 1-bit glyph, the same as Schola Scan |

Knobs:

```bash
python3 build_scan_font.py --soft --soft-amount 0.3                # less of the edge bleeds (default 0.45)
python3 build_scan_font.py --soft --soft-greys 0.14 0.25           # lighter greys (default 0.17 0.30)
```

The bleed colour is fixed (warm black at partial opacity), not the text
colour, so it reads as intended on light backgrounds only. With coloured or
white-on-dark text, use the non-soft fonts.

## Knobs

```bash
python3 build_scan_font.py --family heros     # build Heros Scan instead of Schola Scan
python3 build_scan_font.py --em-px 28      # chunkier stair-steps (coarser scan)
python3 build_scan_font.py --em-px 56      # finer scan, closer to the clean face
python3 build_scan_font.py --fill 0.33     # heavier fill-in (the scan look's value)
python3 build_scan_font.py --weight 1.6    # more letter-to-letter weight variation
python3 build_scan_font.py --strength 1.5  # rougher edges
```

Rebuilding needs `pip install "cogra[fonts]"`. A full build of one family
(four styles) takes about 8 minutes on 8 cores, and overwrites the files in `fonts/`.
All knobs combine with `--family`.

## Caveats

- Paper tone and specks are not part of the font. For the full look, set the
  text to a warm near-black (e.g. `#1E1B17`, the aged look's ink colour) on an
  off-white background, or put a paper texture behind it.
- Only glyphs mapped to Unicode are included (about 1,050 per style: Latin,
  Latin Extended, punctuation, symbols). The source's small caps and old-style
  figures are left out.
- License: TeX Gyre Schola and Heros are under the GUST Font License (LPPL 1.3c), which
  allows modified versions. As the license asks, the families are renamed
  ("Schola Scan", "Heros Scan").
