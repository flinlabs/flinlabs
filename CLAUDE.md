# flinlabs/flinlabs

The profile README repo. `SETUP.md` explains how a profile README works, what
GitHub allows in one, and how to regenerate the artwork.

## Commits

Author commits as the repo owner, not as Claude:

```bash
git config user.name "Felix Lin"
git config user.email "242888529+flinlabs@users.noreply.github.com"
```

The noreply address is GitHub's per-account alias. It attributes to @flinlabs
with the right avatar and keeps a real address out of a public commit log.

Do not add a `Claude-Session:` trailer to commit messages or pull request
bodies. `Co-Authored-By: Claude` is fine.

## Artwork

`assets/*.svg` is generated. Edit `tools/build_assets.py` and re-run it rather
than hand-editing the SVGs, and bump the `?v=` query on every asset URL in
`README.md` afterwards or GitHub's image cache keeps serving the old files.
