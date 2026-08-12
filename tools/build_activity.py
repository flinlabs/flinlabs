#!/usr/bin/env python3
"""Render the Activity numbers from activity.json, in the portfolio's type.

Four figures across a rule, then a mono footer line. Same shape language as
the hero facts on the site: mono label, big Archivo numeral, hairline between.

    python3 build_activity.py activity.json ../assets

Numbers GitHub already draws on the profile page are deliberately absent. The
contribution graph sits a few hundred pixels below the README, so repeating it
here in a prettier form would be the same year twice. Streaks and lifetime
totals appear nowhere on the page, which is why these are the four.
"""
import json
import os
import sys
from datetime import date

from build_assets import DARK, LIGHT, W, label, svg, txt, write

PAD = 0
CELL_H = 152
FOOT_H = 46


def human_date(iso):
    if not iso:
        return "n/a"
    y, m, d = (int(p) for p in iso.split("-"))
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return "%d %s %d" % (d, months[m - 1], y)


def cells(data):
    return [
        ("Current streak", "{:,}".format(data["current_streak"]),
         "day" if data["current_streak"] == 1 else "days"),
        ("Longest streak", "{:,}".format(data["longest_streak"]),
         "day" if data["longest_streak"] == 1 else "days"),
        ("Commits", "{:,}".format(data["total_commits"]), "all time"),
        ("Contributions", "{:,}".format(data["year_contributions"]), "past year"),
    ]


def activity(data, theme):
    h = CELL_H + FOOT_H
    col = W / 4.0
    o = ['<rect y="0" width="%d" height="1" fill="%s"/>' % (W, theme["line_strong"])]

    for i, (name, value, unit) in enumerate(cells(data)):
        x = i * col
        if i:
            o.append('<rect x="%.1f" y="18" width="1" height="%d" fill="%s"/>'
                     % (x, CELL_H - 46, theme["line"]))
        tx = x + (0 if i == 0 else 26)
        o.append(label(name, tx, 34, theme["ink_soft"], 11, 0.14)[0])
        # the unit sits under the figure rather than beside it: a wide number
        # plus a long unit overran the canvas and clipped, and stacking makes
        # every column safe no matter how the numbers grow
        o.append(txt(value, tx, 100, "archivo", 680, 52, -0.035, theme["ink"])[0])
        o.append(label(unit, tx, 126, theme["ink_soft"], 10.5, 0.1)[0])

    y = CELL_H
    o.append('<rect y="%d" width="%d" height="1" fill="%s"/>' % (y, W, theme["line"]))
    left = "busiest day · %s on %s" % (data["busiest_count"], human_date(data["busiest_date"]))
    o.append(label(left, 0, y + 28, theme["ink_soft"], 11, 0.12)[0])
    right = "%s active days · updated %s" % (data["active_days"], human_date(data["updated"]))
    o.append(label(right, W, y + 28, theme["ink_soft"], 11, 0.12, align="right")[0])

    return svg(W, h, "".join(o))


SAMPLE = {
    "current_streak": 0, "longest_streak": 0, "total_commits": 0,
    "year_contributions": 0, "busiest_count": 0, "busiest_date": "",
    "active_days": 0, "updated": date.today().isoformat(),
}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "activity.json"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("..", "assets")

    if os.path.exists(src):
        with open(src) as f:
            data = json.load(f)
    else:
        print("no %s, rendering zeroes" % src)
        data = SAMPLE

    import build_assets
    build_assets.OUT = out
    for theme in (LIGHT, DARK):
        write("activity-%s.svg" % theme["name"], activity(data, theme))


if __name__ == "__main__":
    main()
