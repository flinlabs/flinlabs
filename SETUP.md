# How this profile works

## The special repo

GitHub shows a README on your profile page only if it lives in a repo whose name
matches your username exactly. That means `flinlabs/flinlabs`, public, with
`README.md` at the root of the default branch. That's the entire mechanism. There's no
profile-editor UI; the file *is* the profile.

Everything people do with fancy profiles is downstream of that one rule.

## What GitHub lets you put in it

Less than you'd expect, which is why most profiles converge on the same look.
The README goes through a sanitizer that strips `<style>` blocks, `class`
attributes, scripts, and nearly all inline CSS. You cannot set a font, a
background colour, or a layout.

What survives:

- Images, including SVG, served from a URL.
- `<picture>` with `media="(prefers-color-scheme: dark)"`, so images can swap
  with the reader's GitHub theme.
- Links wrapped around images.
- `width` on `<img>`, including percentages. This is the only layout control you
  get, and it's how two things sit side by side.

So the way you actually theme a profile is: **put the design inside SVGs and let
the README be a thin wrapper around them.** That's what this repo does. The
typography, colour, grain, tape and paper are all baked into vector files that
GitHub just displays.

The usual profile decorations (shields.io badges, `github-readme-stats` cards, a
contribution snake) are the same trick with someone else's SVGs. They look generic
because everyone points at the same default themes. Recolouring them to
your palette gets most of the way; drawing your own gets the rest.

## What's here

```
README.md                            the profile itself
assets/*.svg                         the artwork (generated, don't hand-edit)
tools/build_assets.py                the generator: layout, copy, palette
tools/typeset.py                     outlines Archivo / IBM Plex Mono to paths
.github/workflows/contribution-graph.yml
```

Assets come in two flavours. The header, section rules and footer paint a ground
or use `--ink` directly, so there's a `-light` and `-dark` file for each and the
README swaps them with `<picture>`. The project cards and stack chips are drawn
on a transparent ground with dark ink on paper or pastel, so one file reads
correctly on both themes, same as the site, where `.desk-card-inner` stays white
no matter what.

Fonts get outlined into paths at build time. GitHub proxies README images through
its camo cache, which can't fetch Google Fonts, and an SVG `<text>` element would
fall back to whatever the reader happens to have installed. Outlining is the only
way to get real Archivo onto the page.

## Shipping it

1. Merge this branch into `main`. The README is live the moment it lands.
2. Go to **Actions → contribution graph → Run workflow** once. Until it runs,
   the `output` branch doesn't exist and the snake image in the Activity section
   is a broken link. After that it redraws itself daily at 04:17 UTC.
3. If Actions are disabled on the repo, enable them first under
   **Settings → Actions → General → Allow all actions**.

## Changing things

Copy, colours, project cards and the rotating "currently:" lines all live at the
top of `tools/build_assets.py`, mirroring the tokens in the portfolio's
`app/globals.css`. Edit, then:

```bash
cd tools
pip install -r requirements.txt
python3 build_assets.py
```

It rewrites `../assets/` in place. The first run downloads the two font subsets
into `tools/.fonts/` (gitignored).

If you change the palette on the site, change it here too. The two are meant to be
one brand, and nothing keeps them in sync automatically.

## Gotchas

**Camo caches hard.** Push a new version of an asset and GitHub may keep serving
the old one for hours. The `?v=` query on each URL in `README.md` is the lever.
It sits at `v=5` now; bump it every time you regenerate and the cache is bypassed.

**The stats cards are somebody else's server.** `github-readme-stats.vercel.app`
is a shared public instance and it rate-limits. If the two cards in the Activity
section go blank, that's why. They come back on their own. Deploying your own
instance from [that project's repo](https://github.com/anuraghazra/github-readme-stats)
fixes it permanently, and it's a five-minute Vercel deploy.

**Private contributions.** The snake and the stats cards only see public
activity unless you turn on *Include private contributions on my profile* in
[GitHub settings](https://github.com/settings/profile).

**Pinned repos still matter.** The README sits above your pinned repositories,
not instead of them. Pin the six you want read; the profile is the two of them
together.
