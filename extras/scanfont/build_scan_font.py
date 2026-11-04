#!/usr/bin/env python3
"""
build_scan_font.py: turn TeX Gyre Schola (serif) or TeX Gyre Heros (sans,
the Helvetica-like face of the figure labels) into an installable "scanned"
font (TTF) with the same look vintage.py gives a whole page in its
default `scan` mode.

Each glyph is rendered large, run through the scan degradation (edge
wobble, copy fill-in, letter-to-letter weight variation), sampled down to
a coarse 1-bit scanner grid, and traced back into an outline along the
pixel edges, so the stair-stepped edges survive at any size.

Every glyph gets VARIANTS versions with different noise. An OpenType
`calt` feature cycles through them along a line, so repeated letters do
not look rubber-stamped in apps that apply contextual alternates
(browsers, Canva, Keynote, recent PowerPoint). Apps that do not apply
`calt` show variant 0 everywhere, which still looks scanned.

Kerning and the f-ligatures are carried over from the source font.

--soft builds a "Soft" family ("Schola Scan Soft", "Heros Scan Soft"): the
same 1-bit glyphs with a faint, uneven grey bleed along part of the edge,
one scanner pixel wide, mostly on the lower-right side of strokes (like a
slight press shadow) and broken up by fine noise, in two greys. Outlines
can only be solid, so the greys are colour-font layers (COLR v0) drawn
under the glyph. Apps without colour-font support draw the plain 1-bit
glyph instead, identical to the non-soft font.

Usage:
  python3 build_scan_font.py                       # Schola, all four styles
  python3 build_scan_font.py --family heros        # Heros
  python3 build_scan_font.py --styles regular --em-px 36
  python3 build_scan_font.py --weight 1.4 --strength 1.2
  python3 build_scan_font.py --soft                # Schola Scan Soft
  python3 build_scan_font.py --soft --soft-amount 0.3 --soft-greys 0.14 0.25   # less bleed

The output families are renamed ("Schola Scan", "Heros Scan"), as the GUST Font License
asks of derived works.
"""
import argparse, os
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, shift
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "..", "..", "src", "cogra", "fonts")
UPM = 1000

FAMILIES = {
    #  key       source prefix     source name         output family
    "schola": ("texgyreschola", "TeX Gyre Schola", "Schola Scan"),
    "heros":  ("texgyreheros",  "TeX Gyre Heros",  "Heros Scan"),
}
SOFT_INK = (30 / 255, 27 / 255, 23 / 255)   # the fade's colour: the aged look's warm black

STYLES = {
    #  key          file suffix     style name     weight  fsSelection  macStyle
    "regular":    ("regular",       "Regular",     400,    0x40,        0),
    "italic":     ("italic",        "Italic",      400,    0x01,        2),
    "bold":       ("bold",          "Bold",        700,    0x20,        1),
    "bolditalic": ("bolditalic",    "Bold Italic", 700,    0x21,        3),
}


def noise(rng, shape, sigma):
    """Unit-variance smooth noise (as in vintage.py)."""
    n = gaussian_filter(rng.standard_normal(shape), sigma)
    return (n - n.mean()) / (n.std() + 1e-8)


def degrade_glyph(ink, rng, em, strength, weight, fill):
    """vintage.degrade_scan on one glyph image. `em` is the em size in
    pixels of `ink`; lengths are expressed relative to 10 pt text rendered
    at 300 dpi (em = 41.7 px), the setting vintage.py was tuned at."""
    k = em / 41.7
    s = strength
    h, w = ink.shape

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    amp = 0.35 * k * s
    dx = noise(rng, (h, w), 1.8 * k) * amp
    dy = noise(rng, (h, w), 1.8 * k) * amp
    ink = map_coordinates(ink, [yy + dy, xx + dx], order=1, mode="nearest")

    # Copy fill-in. A whole-glyph offset plus a letter-scale field make
    # some letters heavier than their neighbours.
    blur = gaussian_filter(ink, 0.8 * k)
    thr = (fill - 0.06 * weight * noise(rng, (h, w), 7 * k)
                - 0.03 * weight * rng.standard_normal()
                + 0.02 * s * noise(rng, (h, w), 0.8 * k))
    thr = np.clip(thr, 0.18, 0.5)
    ink = 1.0 / (1.0 + np.exp(-(blur - thr) / 0.05))
    ink[blur < 0.02] = 0.0
    return ink


def trace_pixels(bw):
    """Outline a bitmap (rows = y going UP, True = ink) along pixel edges.
    Returns closed polygons in pixel units, clockwise around ink and
    counter-clockwise around holes (TrueType winding)."""
    h, w = bw.shape
    p = np.pad(bw, 1)
    core = p[1:-1, 1:-1]
    edges = {}

    def add(mask, d0, d1):
        ys, xs = np.nonzero(mask)
        for y, x in zip(ys.tolist(), xs.tolist()):
            a = (x + d0[0], y + d0[1]); b = (x + d1[0], y + d1[1])
            edges.setdefault(a, []).append(b)

    add(core & ~p[2:, 1:-1], (0, 1), (1, 1))     # top open: left -> right
    add(core & ~p[1:-1, 2:], (1, 1), (1, 0))     # right open: down
    add(core & ~p[:-2, 1:-1], (1, 0), (0, 0))    # bottom open: right -> left
    add(core & ~p[1:-1, :-2], (0, 0), (0, 1))    # left open: up

    polys = []
    while edges:
        start = next(iter(edges))
        poly = [start]
        cur = start
        prev_dir = None
        while True:
            outs = edges[cur]
            if len(outs) > 1 and prev_dir is not None:
                # Diagonal touch: take the right-most turn so pixels that
                # only meet at a corner stay separate contours.
                def turn(b):
                    d = (b[0] - cur[0], b[1] - cur[1])
                    return prev_dir[0] * d[1] - prev_dir[1] * d[0]   # <0 = right
                outs.sort(key=turn)
            nxt = outs.pop(0)
            if not outs:
                del edges[cur]
            prev_dir = (nxt[0] - cur[0], nxt[1] - cur[1])
            cur = nxt
            if cur == start:
                break
            poly.append(cur)
        # drop collinear points
        n = len(poly)
        keep = []
        for i in range(n):
            a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
            if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                keep.append(b)
        if len(keep) >= 3:
            polys.append(keep)
    return polys


# Worker state, set once per process
_W = {}


def _init(src_path, em_px, oversample, strength, weight, fill, seed, soft):
    _W.update(src_path=src_path, em_px=em_px, f=oversample,
              strength=strength, weight=weight, fill=fill, seed=seed, soft=soft,
              pil=ImageFont.truetype(src_path, em_px * oversample),
              gs=TTFont(src_path).getGlyphSet())


def make_glyph(job):
    """job = (glyph name, character, variant). Returns a list of contour
    sets in font units: the 1-bit ink, then (for --soft) the darker and the
    lighter bleed pixels."""
    name, ch, variant = job
    em, f = _W["em_px"], _W["f"]
    R = em * f                       # render em size in px
    unit = UPM / em                  # font units per scan pixel
    bp = BoundsPen(_W["gs"])
    _W["gs"][name].draw(bp)
    if bp.bounds is None:
        return name, variant, [[]]
    xmin, ymin, xmax, ymax = bp.bounds
    # Canvas in scan pixels, aligned to the glyph origin so the baseline
    # falls on a pixel boundary in every glyph.
    m = 4
    gx0 = int(np.floor(xmin / unit)) - m; gx1 = int(np.ceil(xmax / unit)) + m
    gy0 = int(np.floor(ymin / unit)) - m; gy1 = int(np.ceil(ymax / unit)) + m
    W, H = (gx1 - gx0) * f, (gy1 - gy0) * f
    img = Image.new("L", (W, H), 0)
    ImageDraw.Draw(img).text((-gx0 * f, gy1 * f), ch, font=_W["pil"], fill=255, anchor="ls")
    ink = np.asarray(img, np.float32) / 255.0

    rng = np.random.default_rng([_W["seed"], variant, sum(map(ord, name)), len(name)])
    ink = degrade_glyph(ink, rng, R, _W["strength"], _W["weight"], _W["fill"])

    small = ink.reshape(H // f, f, W // f, f).mean(axis=(1, 3))
    bw = small >= 0.45               # rows go down (image order)
    masks = [bw]
    if _W["soft"] and bw.any():
        # Separate noise stream, so the ink matches the non-soft font exactly.
        frng = np.random.default_rng([_W["seed"], variant, sum(map(ord, name)), len(name), 7])
        masks += bleed(bw, frng, _W["soft"]["amount"])
    masks = [mk[::-1] for mk in masks]   # rows now go up from gy0
    out = [[[((x + gx0) * unit, (y + gy0) * unit) for x, y in poly] for poly in trace_pixels(mk)]
           for mk in masks]
    return name, variant, out


def vname(g, v):
    return g if v == 0 else f"{g}.v{v}"


def bleed(bw, rng, amount):
    """--soft: the bleed pixels of a 1-bit glyph (rows going down), as two
    masks (darker grey, lighter grey). A pixel can bleed if it touches the
    ink (4-neighbour, so corners stay rounded); it does when fine noise plus
    a bias toward the lower-right side of strokes beats a threshold. A
    second noise field picks which of the two greys it gets.
    amount: about 0.3 to 0.6; higher = more bleed (0.45 = G1 of the specimens)."""
    d = distance_transform_edt(~bw)
    edge = (d > 0) & (d <= 1.25)
    moved = lambda dy, dx: shift(bw.astype(np.uint8), (dy, dx), order=0, cval=0).astype(bool)
    lower_right = moved(1, 1) | moved(1, 0) | moved(0, 1)
    bias = np.where(lower_right, 0.7, -0.5)
    keep = edge & (noise(rng, bw.shape, 0.9) + bias > 0.9 - amount)
    dark = noise(rng, bw.shape, 1.2) > 0
    return [keep & dark, keep & ~dark]


def build_style(key, a):
    suffix, style_name, weight_class, fs_sel, mac_style = STYLES[key]
    prefix, src_name, family = FAMILIES[a.family]
    soft = {"amount": a.soft_amount} if a.soft else None
    if a.soft:
        family += " Soft"
    src_path = os.path.join(SRC_DIR, f"{prefix}-{suffix}.otf")
    src = TTFont(src_path)
    cmap = src.getBestCmap()
    by_glyph = {}
    for cp, g in sorted(cmap.items()):
        by_glyph.setdefault(g, chr(cp))
    base = [g for g in src.getGlyphOrder() if g in by_glyph]

    jobs = [(g, by_glyph[g], v) for v in range(a.variants) for g in base]
    with Pool(a.jobs, initializer=_init,
              initargs=(src_path, a.em_px, a.oversample, a.strength, a.weight, a.fill, a.seed,
                        soft)) as pool:
        results = pool.map(make_glyph, jobs, chunksize=16)

    order = [".notdef"] + [vname(g, v) for v in range(a.variants) for g in base]
    glyphs, metrics, layers = {}, {}, {}
    hmtx = src["hmtx"].metrics
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph(); metrics[".notdef"] = (500, 0)

    def outline(polys):
        pen = TTGlyphPen(None)
        for poly in polys:
            pen.moveTo(poly[0])
            for pt in poly[1:]:
                pen.lineTo(pt)
            pen.closePath()
        gl = pen.glyph()
        gl.recalcBounds(None)
        return gl

    for g, v, sets in results:
        n = vname(g, v)
        for k, polys in enumerate(sets):
            ln = n if k == 0 else f"{n}.s{k}"
            if k:
                order.append(ln)
            gl = outline(polys)
            glyphs[ln] = gl
            metrics[ln] = (hmtx[g][0], getattr(gl, "xMin", 0))
        if len(sets) > 1:
            # grey layers (palette 0 = darker, 1 = lighter), then the glyph
            # itself in the text colour (0xFFFF)
            layers[n] = [(f"{n}.s1", 0), (f"{n}.s2", 1), (n, 0xFFFF)]

    ps = f"{family.replace(' ', '')}-{style_name.replace(' ', '')}"
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({cp: g for cp, g in cmap.items() if g in by_glyph})
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    if layers:
        fb.setupCOLR(layers, version=0)
        lighter, darker = a.soft_greys
        fb.setupCPAL([[(*SOFT_INK, darker), (*SOFT_INK, lighter)]])
    hh = src["hhea"]
    fb.setupHorizontalHeader(ascent=hh.ascent, descent=hh.descent, lineGap=hh.lineGap)
    fb.setupNameTable({
        "copyright": f"Derived from {src_name} (c) GUST e-foundry, GUST Font License. "
                     "Scan degradation added; renamed per the license's request.",
        "familyName": family,
        "styleName": style_name,
        "uniqueFontIdentifier": f"{ps};1.0",
        "fullName": f"{family} {style_name}",
        "version": "Version 1.000",
        "psName": ps,
        "description": f"{src_name} with a 1-bit archival-scan texture"
                       + (", with an uneven grey bleed (COLR layers)." if a.soft else "."),
        "licenseDescription": "GUST Font License (LPPL 1.3c). See GUST-FONT-LICENSE.txt.",
    })
    os2 = src["OS/2"]
    fb.setupOS2(
        usWeightClass=weight_class, fsSelection=fs_sel,
        sTypoAscender=os2.sTypoAscender, sTypoDescender=os2.sTypoDescender,
        sTypoLineGap=os2.sTypoLineGap, usWinAscent=os2.usWinAscent,
        usWinDescent=os2.usWinDescent, sxHeight=os2.sxHeight,
        sCapHeight=os2.sCapHeight, achVendID="NONE", fsType=0,
        panose=os2.panose, ulUnicodeRange1=os2.ulUnicodeRange1,
        ulUnicodeRange2=os2.ulUnicodeRange2, ulCodePageRange1=os2.ulCodePageRange1,
    )
    fb.setupPost(italicAngle=src["post"].italicAngle,
                 underlinePosition=src["post"].underlinePosition,
                 underlineThickness=src["post"].underlineThickness)
    fb.font["head"].macStyle = mac_style

    fb.font.save(os.path.join(a.out, "_tmp.ttf"))
    font = TTFont(os.path.join(a.out, "_tmp.ttf"))
    addOpenTypeFeaturesFromString(font, features(src, base, a.variants))
    out_path = os.path.join(a.out, f"{ps}.ttf")
    font.save(out_path)
    os.remove(os.path.join(a.out, "_tmp.ttf"))
    print(f"  {out_path}  ({len(order)} glyphs, {os.path.getsize(out_path) // 1024} KB)")


def features(src, base, variants):
    have = set(base)
    alts = lambda g: " ".join(vname(g, v) for v in range(variants))
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", ""]

    # f-ligatures from the source (only those whose glyphs we built)
    ligs = []
    gsub = src["GSUB"].table
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag != "liga":
            continue
        for li in fr.Feature.LookupListIndex:
            for st in gsub.LookupList.Lookup[li].SubTable:
                for first, ls in getattr(st, "ligatures", {}).items():
                    for lig in ls:
                        comp = [first] + lig.Component
                        if lig.LigGlyph in have and all(c in have for c in comp):
                            ligs.append(f"  sub {' '.join(comp)} by {lig.LigGlyph};")
    if ligs:
        lines += ["feature liga {"] + sorted(set(ligs)) + ["} liga;", ""]

    # cycle variants 0 -> 1 -> 2 -> 0 ... along the run
    if variants > 1:
        for v in range(variants):
            lines.append(f"@V{v} = [{' '.join(vname(g, v) for g in base)}];")
        lines.append("feature calt {")
        lines.append("  lookup cycle {")
        for v in range(variants - 1):
            lines.append(f"    sub @V{v} @V0' by @V{v + 1};")
        lines.append("  } cycle;")
        lines.append("} calt;")
        lines.append("")

    # kerning: source glyph pairs, expanded to every variant pair
    gpos = src["GPOS"].table
    pairs = []
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag != "kern":
            continue
        for li in fr.Feature.LookupListIndex:
            for st in gpos.LookupList.Lookup[li].SubTable:
                if st.Format != 1:
                    continue
                for left, ps in zip(st.Coverage.glyphs, st.PairSet):
                    if left not in have:
                        continue
                    for pv in ps.PairValueRecord:
                        val = getattr(pv.Value1, "XAdvance", 0) if pv.Value1 else 0
                        if pv.SecondGlyph in have and val:
                            pairs.append((left, pv.SecondGlyph, val))
        break
    if pairs:
        lines.append("feature kern {")
        for l, r, val in sorted(set(pairs)):
            lines.append(f"  enum pos [{alts(l)}] [{alts(r)}] {val};")
        lines.append("} kern;")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", choices=FAMILIES, default="schola")
    ap.add_argument("--styles", nargs="+", choices=STYLES, default=list(STYLES))
    ap.add_argument("--em-px", type=int, default=36,
                    help="scanner pixels per em: lower = chunkier stair-steps (24 to 60)")
    ap.add_argument("--oversample", type=int, default=12, help="render px per scanner px")
    ap.add_argument("--strength", type=float, default=1.0, help="edge roughness (0 to 2)")
    ap.add_argument("--weight", type=float, default=1.0, help="letter-to-letter weight variation")
    ap.add_argument("--fill", type=float, default=0.38,
                    help="ink threshold: lower = heavier copy fill-in (vintage.py uses 0.33)")
    ap.add_argument("--variants", type=int, default=3, help="noise versions per glyph cycled by calt")
    ap.add_argument("--seed", type=int, default=1956)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--soft", action="store_true",
                    help='build the "Soft" family: an uneven 1-pixel grey bleed (colour-font layers)')
    ap.add_argument("--soft-amount", type=float, default=0.45,
                    help="--soft: how much of the edge bleeds, about 0.3 to 0.6")
    ap.add_argument("--soft-greys", type=float, nargs=2, default=(0.17, 0.30), metavar=("LIGHT", "DARK"),
                    help="--soft: opacity of the two bleed greys")
    ap.add_argument("--out", default=os.path.join(HERE, "fonts"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for key in a.styles:
        print(f"Building {FAMILIES[a.family][2]}{' Soft' if a.soft else ''} {key} ...")
        build_style(key, a)


if __name__ == "__main__":
    main()
