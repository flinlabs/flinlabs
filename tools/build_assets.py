#!/usr/bin/env python3
"""Generate the profile-README artwork from the portfolio's design tokens.

Every value here traces back to app/globals.css, so the GitHub profile and the
site stay one brand. Run `python3 build_assets.py` to rewrite ../assets/.

Two kinds of asset come out of this:

  * theme-agnostic (project cards, stack chips) — transparent ground, dark ink
    on paper or pastel, so one file reads correctly on both GitHub themes.
  * light/dark pairs (header, section rules, footer) — these paint a ground or
    use --ink directly, so the README swaps them with <picture>.
"""
import math
import os

from typeset import text_path, width_of, wrap

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SITE = "https://flinportfolio.vercel.app"
W = 880  # GitHub's rendered README column on desktop

EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)"

# ————— tokens, lifted from :root in app/globals.css —————
LIGHT = {
    "name": "light",
    "bg": "#f4f1ea",
    "bg_deep": "#eae6dc",
    "ink": "#1b1a17",
    "ink_soft": "#6b665c",
    "line": "rgba(27,26,23,0.12)",
    "line_strong": "rgba(27,26,23,0.30)",
    "grain": 0.30,
}
DARK = {
    "name": "dark",
    "bg": "#1b1a17",  # --dark
    "bg_deep": "#232019",
    "ink": "#f2efe8",  # --ivory
    "ink_soft": "#a9a396",  # --ivory-soft
    "line": "rgba(242,239,232,0.13)",
    "line_strong": "rgba(242,239,232,0.28)",
    "grain": 0.20,
}

PASTELS = {
    "lav": ("#e6dff5", "#52468a"),
    "butter": ("#f3e8c2", "#6f5b1e"),
    "powder": ("#d9e5f0", "#2f5578"),
    "mint": ("#dcebdd", "#2f6440"),
    "blush": ("#f5ded2", "#8a4527"),
    "sand": ("#eee3cc", "#6e5a2e"),
}

PAPER = "#ffffff"
TAPE = "rgba(238,227,204,0.72)"
CARD_INK = "#1b1a17"
CARD_INK_SOFT = "#6b665c"


# ————— svg plumbing —————
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def p(d, fill=None, **attrs):
    bits = ['<path d="%s"' % d]
    if fill:
        bits.append('fill="%s"' % fill)
    for k, v in attrs.items():
        bits.append('%s="%s"' % (k.replace("_", "-"), v))
    return " ".join(bits) + "/>"


def txt(s, x, y, family="archivo", weight=400, size=16, tracking=0.0, fill="#000", align="left", **attrs):
    d, w = text_path(s, family, weight, size, tracking, 0, 0)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    return p(d, fill, transform="translate(%.2f %.2f)" % (x, y), **attrs), w


def label(s, x, y, fill, size=11, tracking=0.14, weight=500, align="left", **attrs):
    """The .label rule: mono, uppercase, wide tracking."""
    return txt(s.upper(), x, y, "mono", weight, size, tracking, fill, align, **attrs)


def grain(theme, w, h, uid="g"):
    return (
        '<filter id="%s" x="0" y="0" width="100%%" height="100%%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/>'
        '<feComponentTransfer><feFuncA type="linear" slope="0.05"/></feComponentTransfer>'
        "</filter>"
        '<rect width="%d" height="%d" filter="url(#%s)" opacity="%s"/>' % (uid, w, h, uid, theme["grain"])
    )


def shadow(uid, dy=18, blur=16, color="rgba(60,52,38,0.34)"):
    return '<filter id="%s" x="-25%%" y="-25%%" width="150%%" height="160%%">' \
           '<feDropShadow dx="0" dy="%d" stdDeviation="%d" flood-color="%s"/></filter>' % (uid, dy, blur, color)


def arrow_ne(x, y, size=9, stroke="#000", width=1.6, **attrs):
    """A drawn ↗ — the arrow glyph isn't in the Google Fonts latin subset."""
    extra = "".join(' %s="%s"' % (k.replace("_", "-"), v) for k, v in attrs.items())
    return (
        '<g stroke="%s" stroke-width="%s" stroke-linecap="round" fill="none"%s>'
        '<path d="M%.2f %.2f L%.2f %.2f"/><path d="M%.2f %.2f H%.2f V%.2f"/></g>'
        % (stroke, width, extra, x, y + size, x + size, y, x + size * 0.32, y, x + size, y + size * 0.68)
    )


def motif(x, y, scale=1.0, stroke="currentColor", dot="#52468a", animate=True, sw=2.6):
    """The site's brand mark: a dot cresting a drawn current (components/Motif.tsx)."""
    wave_cls = ' class="wave"' if animate else ""
    dot_cls = ' class="dot"' if animate else ""
    return (
        '<g transform="translate(%.2f %.2f) scale(%.4f)" fill="none">'
        '<path%s d="M2 16.5 C 9 5.5, 16.5 21.5, 24.5 12.5 S 39 9.5, 46 14" pathLength="100" '
        'stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
        '<g%s><circle cx="25" cy="4.5" r="3.2" fill="%s"/></g>'
        "</g>" % (x, y, scale, wave_cls, stroke, sw, dot_cls, dot)
    )


MOTIF_CSS = """
    .wave { stroke-dasharray: 100; stroke-dashoffset: 100;
            animation: draw 1.5s %(ease)s 0.2s forwards; }
    .dot  { transform-box: fill-box; transform-origin: center; transform: scale(0);
            animation: pop 0.55s %(ease)s 1.15s forwards; }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    @keyframes pop  { to { transform: scale(1); } }
""" % {"ease": EASE_OUT}

REDUCED_MOTION = """
    @media (prefers-reduced-motion: reduce) {
      .wave { animation: none; stroke-dashoffset: 0; }
      .dot  { animation: none; transform: scale(1); }
      .roll { animation: none; }
    }
"""


def svg(w, h, body, style=""):
    css = '<style>%s</style>' % style if style else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img">%s%s</svg>\n' % (w, h, w, h, css, body)
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(content)
    print("  %-28s %5.1f KB" % (name, len(content) / 1024))


# ————— header —————
DESCRIPTORS = [
    "building CompLens: address in, comps out",
    "studying econ + data science at Berkeley",
    "optimizing gacha teams for Morimens",
    "putting Claude to work on commercial leases",
    "designing my own narrative puzzle videogame",
]

FACTS = [
    ("Located", ["Berkeley, California"]),
    ("Studying", ["BA Economics, BA Data Science", "Expected May 2028"]),
]


def header(theme):
    h = 302
    pad = 44
    lav_ink = PASTELS["lav"][1]
    # the lavender rotator ink is tuned for warm paper; lift it on the dark ground
    rot_ink = lav_ink if theme["name"] == "light" else "#c9bff0"

    o = ['<rect width="%d" height="%d" fill="%s"/>' % (W, h, theme["bg"])]
    o.append(grain(theme, W, h, "hgrain"))
    o.append(motif(pad, 44, 1.3, theme["ink"], rot_ink))

    o.append(txt("Faye Lin", pad, 156, "archivo", 680, 72, -0.035, theme["ink"])[0])

    # rotator: "currently:" + descriptors cycling on a 15s loop, same as RotatingLines
    base = 198
    lead, lead_w = label("currently:", pad, base, theme["ink_soft"], 11, 0.14)
    o.append(lead)
    rx = pad + lead_w + 14
    lh = 22
    o.append('<clipPath id="rotclip"><rect x="%.1f" y="%.1f" width="360" height="%d"/></clipPath>' % (rx, base - 15, lh))
    lines = DESCRIPTORS + DESCRIPTORS[:1]  # trailing copy makes the loop seamless
    rolled = ['<g class="roll">']
    for i, line in enumerate(lines):
        rolled.append(txt(line, rx, base + i * lh, "mono", 400, 13.5, 0.005, rot_ink)[0])
    rolled.append("</g>")
    o.append('<g clip-path="url(#rotclip)">%s</g>' % "".join(rolled))

    # hero facts, right-aligned
    fy = 76
    for name, values in FACTS:
        o.append(label(name, W - pad, fy, theme["ink_soft"], 11, 0.14, align="right")[0])
        fy += 22
        for v in values:
            o.append(txt(v, W - pad, fy, "archivo", 400, 14.5, 0, theme["ink"], align="right")[0])
            fy += 21
        fy += 14

    # baseline rule
    o.append('<rect x="%d" y="238" width="%d" height="1" fill="%s"/>' % (pad, W - pad * 2, theme["line"]))
    o.append(label("flinportfolio.vercel.app", pad, 268, theme["ink_soft"], 11, 0.14)[0])
    o.append(arrow_ne(pad + width_of("FLINPORTFOLIO.VERCEL.APP", "mono", 500, 11, 0.14) + 9, 260,
                      8, theme["ink_soft"], 1.4))
    o.append(label("open to internships and builds", W - pad, 268, theme["ink_soft"], 11, 0.14, align="right")[0])

    keyframes = []
    for i in range(5):
        start, end = i * 20, i * 20 + 16
        keyframes.append("%d%%,%d%% { transform: translateY(%dpx); }" % (start, end, -lh * i))
    keyframes.append("100%% { transform: translateY(%dpx); }" % (-lh * 5))

    style = MOTIF_CSS + """
    .roll { animation: roll 15s %s infinite; }
    @keyframes roll { %s }
""" % (EASE_OUT, " ".join(keyframes)) + REDUCED_MOTION

    return svg(W, h, "".join(o), style)


# ————— section rules —————
def rule(text, index, theme):
    h = 40
    o = []
    lab, lw = label(text, 0, 26, theme["ink_soft"], 11, 0.14)
    o.append(lab)
    idx, iw = label(index, W, 26, theme["ink_soft"], 11, 0.14, align="right")
    o.append(idx)
    x1 = lw + 18
    x2 = W - iw - 18
    o.append('<rect x="%.1f" y="21" width="%.1f" height="1" fill="%s"/>' % (x1, x2 - x1, theme["line_strong"]))
    return svg(W, h, "".join(o))


# ————— project cards —————
CARDS = [
    {
        "file": "card-complens",
        "kind": "note",
        "accent": "lav",
        "period": "Jul 2026 – Present",
        "title": "CompLens",
        "blurb": "Address in, rent comp memo out. A two-model Claude pipeline sources asking rents from official leasing sites first.",
        "tag": "AI · Product · Real Estate",
        "tilt": -1.3,
    },
    {
        "file": "card-morimens",
        "kind": "paper",
        "accent": "butter",
        "period": "Jun 2026 – Present",
        "title": "Morimens Team Builder",
        "blurb": "A deterministic engine that builds five geared D-Tide teams from your roster, sharing no units.",
        "tag": "Engineering · Product · Games",
        "tilt": 1.5,
    },
    {
        "file": "card-lease-intelligence",
        "kind": "note",
        "accent": "powder",
        "period": "Jun – Aug 2026",
        "title": "Lease Intelligence",
        "blurb": "Self-serve Q&A over 880 commercial leases, built inside the Empire State Building's landlord.",
        "tag": "AI · Product · Real Estate",
        "tilt": -1.6,
    },
]

CARD_W, CARD_H = 428, 250
BOX_X, BOX_Y, BOX_W, BOX_H = 18, 16, 392, 214
FOLD = 22


def card(spec):
    wash, wash_ink = PASTELS[spec["accent"]]
    fill = wash if spec["kind"] == "note" else PAPER
    pad = 26
    o = [shadow("cs", 16, 14)]

    body = []
    if spec["kind"] == "note":
        d = "M0 0 H%d V%d L%d %d H0 Z" % (BOX_W, BOX_H - FOLD, BOX_W - FOLD, BOX_H)
        body.append(p(d, fill))
        body.append('<linearGradient id="fold" x1="1" y1="0" x2="0" y2="1">'
                    '<stop offset="0" stop-color="rgba(27,26,23,0.16)"/>'
                    '<stop offset="0.8" stop-color="rgba(27,26,23,0)"/></linearGradient>')
        body.append(p("M%d %d H%d L%d %d Z" % (BOX_W - FOLD, BOX_H - FOLD, BOX_W, BOX_W - FOLD, BOX_H), "url(#fold)"))
    else:
        body.append('<rect width="%d" height="%d" fill="%s"/>' % (BOX_W, BOX_H, fill))
        body.append('<rect x="%d" y="%d" width="22" height="2.5" fill="%s"/>' % (pad, pad - 4, wash_ink))

    y = pad + 22 if spec["kind"] == "paper" else pad + 4
    body.append(label(spec["period"], pad, y, "rgba(27,26,23,0.48)", 10.5, 0.1)[0])

    ty = y + 40
    body.append(txt(spec["title"], pad, ty, "archivo", 640, 25, -0.022, CARD_INK)[0])

    by = ty + 26
    for line in wrap(spec["blurb"], BOX_W - pad * 2, family="archivo", weight=400, size=13.5)[:3]:
        body.append(txt(line, pad, by, "archivo", 400, 13.5, 0, CARD_INK_SOFT)[0])
        by += 19

    fy = BOX_H - pad
    body.append(label(spec["tag"], pad, fy, wash_ink, 10, 0.08)[0])
    body.append(arrow_ne(BOX_W - pad - 10, fy - 9, 10, wash_ink, 1.7))

    cx, cy = BOX_W / 2, BOX_H / 2
    o.append(
        '<g transform="translate(%d %d) rotate(%.2f %.1f %.1f)" filter="url(#cs)">%s</g>'
        % (BOX_X, BOX_Y, spec["tilt"], cx, cy, "".join(body))
    )

    if spec["kind"] == "paper":
        # a strip of tape over the card's top edge, same trick as .desk-tape.
        # the card is rotated, so ride the anchor around with it.
        th = math.radians(spec["tilt"])
        tx = BOX_X + cx + cy * math.sin(th)
        ty = BOX_Y + cy - cy * math.cos(th)
        o.append(
            '<g transform="translate(%.1f %.1f) rotate(%.1f)">'
            '<rect x="-48" y="-13" width="96" height="26" fill="%s"/>'
            '<rect x="-48" y="-13" width="1" height="26" fill="rgba(27,26,23,0.10)"/>'
            '<rect x="47" y="-13" width="1" height="26" fill="rgba(27,26,23,0.10)"/></g>'
            % (tx, ty + 2, spec["tilt"] - 2.5, TAPE)
        )

    return svg(CARD_W, CARD_H, "".join(o))


# ————— stack chips —————
STACK = [
    ("TypeScript", "lav"), ("React", "powder"), ("Next.js", "sand"), ("Tailwind", "mint"),
    ("Vite", "butter"), ("Node", "blush"), ("Python", "powder"), ("FastAPI", "mint"),
    ("Claude API", "lav"), ("Postgres", "sand"), ("Supabase", "mint"), ("SQL", "butter"),
    ("GSAP", "blush"), ("Zustand", "sand"), ("Vercel", "lav"), ("Azure", "powder"),
    ("Airtable", "mint"), ("Glide", "butter"), ("Chrome Extensions", "blush"),
]

CHIP_H = 30
CHIP_PAD = 15
CHIP_GAP = 9
ROW_GAP = 11


def stack():
    x, y = 0, 0
    rows, row = [], []
    for name, accent in STACK:
        tw = width_of(name.upper(), "mono", 500, 10.5, 0.08)
        cw = tw + CHIP_PAD * 2
        if row and x + cw > W:
            rows.append(row)
            row, x = [], 0
        row.append((name, accent, x, cw, tw))
        x += cw + CHIP_GAP
    rows.append(row)

    o = []
    for r, items in enumerate(rows):
        y = r * (CHIP_H + ROW_GAP)
        for name, accent, cx, cw, tw in items:
            wash, ink = PASTELS[accent]
            o.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="%d" fill="%s"/>'
                     % (cx, y, cw, CHIP_H, CHIP_H // 2, wash))
            o.append(label(name, cx + CHIP_PAD, y + 19.5, ink, 10.5, 0.08)[0])
    h = len(rows) * (CHIP_H + ROW_GAP) - ROW_GAP
    return svg(W, h, "".join(o))


# ————— footer —————
def footer(theme):
    h = 96
    lav_ink = PASTELS["lav"][1] if theme["name"] == "light" else "#c9bff0"
    o = ['<rect y="0" width="%d" height="1" fill="%s"/>' % (W, theme["line"])]
    o.append(motif(0, 30, 0.92, theme["ink"], lav_ink, animate=False))
    o.append(label("Berkeley, CA", 0, 82, theme["ink_soft"], 11, 0.14)[0])
    o.append(txt("Let's talk", W - 26, 52, "archivo", 660, 34, -0.03, theme["ink"], align="right")[0])
    o.append(arrow_ne(W - 15, 30, 15, theme["ink"], 2.2))
    o.append(label("f.lin@berkeley.edu", W, 82, theme["ink_soft"], 11, 0.14, align="right")[0])
    return svg(W, h, "".join(o))


def main():
    print("writing to %s" % os.path.normpath(OUT))
    for theme in (LIGHT, DARK):
        t = theme["name"]
        write("header-%s.svg" % t, header(theme))
        write("footer-%s.svg" % t, footer(theme))
        for text, index, slug in (
            ("Projects · on the desk", "01", "projects"),
            ("Stack · what I reach for", "02", "stack"),
            ("Activity · the last year", "03", "activity"),
            ("Elsewhere", "04", "elsewhere"),
        ):
            write("rule-%s-%s.svg" % (slug, t), rule(text, index, theme))
    for spec in CARDS:
        write("%s.svg" % spec["file"], card(spec))
    write("stack.svg", stack())


if __name__ == "__main__":
    main()
