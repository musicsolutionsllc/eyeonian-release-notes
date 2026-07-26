# EyeOnian™ Release Notes

Source for the GitHub Pages site at
<https://musicsolutionsllc.github.io/eyeonian-release-notes/>

**This repo is the source of truth for this document.** Edit it here, by hand,
through the GitHub web UI — that is the intended workflow and it needs no local
toolchain. The EyeOnian app *vendors* a pinned copy; the flow is this repo → the
app, never the reverse.

## Layout

| Path | Purpose |
|---|---|
| `index.md` | **The current document.** This is the URL referenced by the app stores — it must always serve the document itself, never an index. |
| `vN.N/index.md` | A pinned version, for citing, printing and for the app to vendor. |
| `archive/index.md` | Every version with its effective date. |

## The one rule

**Once a version directory has shipped in an app build, it is frozen.**
Corrections go into a *new* version directory — never into a released one.
CI (`.github/workflows/docs.yml`) fails the push if a released version is
modified.

Publishing a new version:

1. Create the next `vN.N/index.md` and edit it.
2. Copy it to `index.md` at the root so the root stays current.
3. Add the version to `archive/index.md`.
4. In the app repo, re-vendor and bump the manifest:
   `python3 tools/vendor_legal.py --doc releases --version N.N --effective YYYY-MM-DD`

Steps 1–3 are all that is needed for a web-only correction. Step 4 happens when
an app build ships.
