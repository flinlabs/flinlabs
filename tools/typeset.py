"""Turn brand-font strings into SVG path data.

GitHub serves README images through its camo proxy, so an SVG can't pull
Archivo or IBM Plex Mono off Google Fonts at render time — and a <text>
element would fall back to whatever the reader has installed. Outlining the
text keeps the portfolio's exact typography with no font blob to embed.
"""
import io
import os
import re
import urllib.request
from functools import lru_cache

import uharfbuzz as hb
from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fonts")

# latin subsets pulled from the same Google Fonts the site loads via next/font.
# Archivo ships as a wght variable font; Plex Mono as one file per weight.
FONT_URLS = {
    "archivo": "https://fonts.gstatic.com/s/archivo/v25/k3kPo8UDI-1M0wlSV9XAw6lQkqWY8Q82sLydOxI.woff2",
    "mono-400": "https://fonts.gstatic.com/s/ibmplexmono/v20/-F63fjptAgt5VM-kVkqdyU8n1i8q1w.woff2",
    "mono-500": "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3twJwlBFgg.woff2",
    "mono-600": "https://fonts.gstatic.com/s/ibmplexmono/v20/-F6qfjptAgt5VM-kVkqdyU8n3vAOwlBFgg.woff2",
}

MONO_WEIGHTS = (400, 500, 600)


def _fetch(key):
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, key + ".woff2")
    if not os.path.exists(path):
        urllib.request.urlretrieve(FONT_URLS[key], path)
    return path


@lru_cache(maxsize=None)
def _load(family, weight):
    if family == "mono":
        key = "mono-%d" % min(MONO_WEIGHTS, key=lambda w: abs(w - weight))
    else:
        key = "archivo"

    tt = TTFont(_fetch(key))
    if "fvar" in tt:
        tt = instancer.instantiateVariableFont(tt, {"wght": weight}, inplace=False)
    tt.flavor = None
    buf = io.BytesIO()
    tt.save(buf)
    raw = buf.getvalue()

    face = hb.Face(raw)
    font = hb.Font(face)
    font.scale = (face.upem, face.upem)
    return TTFont(io.BytesIO(raw)), font, face.upem


def _round(d, places=1):
    return re.sub(r"-?\d+\.\d+", lambda m: ("%.*f" % (places, float(m.group()))).rstrip("0").rstrip("."), d)


def text_path(s, family="archivo", weight=400, size=16, tracking=0.0, x=0.0, y=0.0):
    """SVG path data for `s` with its baseline starting at (x, y).

    `tracking` is letter-spacing in em, matching the CSS values in globals.css.
    Returns (path_data, advance_width).
    """
    tt, hbfont, upem = _load(family, weight)
    glyphset = tt.getGlyphSet()
    order = tt.getGlyphOrder()

    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf)

    scale = size / upem
    track = tracking * size
    pen_x = x
    parts = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        if info.codepoint == 0:
            raise ValueError("%r has a character missing from the %s latin subset" % (s, family))
        pen = SVGPathPen(glyphset)
        glyphset[order[info.codepoint]].draw(
            TransformPen(pen, Transform(scale, 0, 0, -scale, pen_x + pos.x_offset * scale, y - pos.y_offset * scale))
        )
        if pen.getCommands():
            parts.append(pen.getCommands())
        pen_x += pos.x_advance * scale + track

    width = pen_x - x - (track if s else 0)
    return _round(" ".join(parts)), width


def width_of(s, family="archivo", weight=400, size=16, tracking=0.0):
    return text_path(s, family, weight, size, tracking)[1]


def wrap(s, limit, **kw):
    """Greedy word wrap against a pixel width."""
    lines, line = [], ""
    for word in s.split():
        trial = (line + " " + word).strip()
        if line and width_of(trial, **kw) > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines
