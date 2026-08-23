# build_pipeline

How `books/*.html` actually gets edited. The root README's rule stands:
**never hand-edit files in `books/`** — they're generated output and this
pipeline overwrites them on every rebuild. Edit a page spec, then rebuild.

## Where this came from

This pipeline didn't exist until 2026-08-23, even though the root README
referenced it — the 14 books had been hand-authored directly as HTML,
sharing an identical CSS/JS template by copy-paste rather than by any real
generator. `extract_spec.py` was run once against every existing book to
produce `specs/*.json` — pulled mechanically from the live HTML, not
retyped by hand — and `render.py` was written to reproduce that exact
template. Every one of the 14 specs, re-rendered, currently comes out
**byte-identical** to the book that shipped before this pipeline existed.
If that's no longer true (because a book was hand-edited outside the
pipeline since), running `extract_spec.py --all` again re-syncs `specs/`
from whatever is currently in `books/` — accepting that it may bring in an
edit that skipped the pipeline.

## How a book is structured

Every book is: a cover page, some number of interior pages, an end/badge
screen. Each interior page has:

- a **stage** — a background (`backdrop-<name>`, one of the classes
  already defined in the shared CSS — see `BACKGROUND-SWAP` in the root
  README for the real illustrated-art gap) and an ordered list of
  **elements** on it: character images (`img`), a community helper
  (`helper`), and/or a tappable **hotspot** (`hotspot`, plays a `pulse` or
  `ding` effect). Order matters — it's DOM order, i.e. paint order.
- `text_a` — the full sentence (the decodable-phonics engine's "engine A")
- `text_b` — the short/simplified line (engine B)
- an optional `quiz` — a question, an options list, and the correct index

The cover has just an `h1_html` (raw HTML — may contain `<br>` and
`&amp;`) and a stage. The end screen has a badge emoji + label, and the
"For Grown-Ups" guide text (feeling/skill, a question to ask, something to
try, and the Common Core standards it maps to).

See any file in `specs/` for the exact shape — they're real, not samples.

## Commands

```bash
# Rebuild every book from its spec
python build_pipeline/build.py

# Rebuild just one
python build_pipeline/build.py Book1_Maya_Marcus_FireStation

# Re-extract specs/*.json FROM books/*.html (only if a book was hand-edited
# outside the pipeline and specs/ needs to catch back up — this direction
# loses nothing since specs are structurally lossless for everything the
# template supports, but it will silently absorb any hand-edit as if it
# were the intended content)
python build_pipeline/extract_spec.py --all
```

## Editing a book

1. Open `build_pipeline/specs/<BookName>.json`.
2. Edit the field you need — a `text_a` line, a quiz answer, which sprite
   an `img` element points at, a hotspot's `emoji`. Keep sprite filenames
   matching real files in `assets/sprites/` (the pipeline doesn't validate
   that — nothing currently does; see `scripts/link_check.py` for the
   closest existing safety net, though it only checks `href`/`src`
   attributes already in rendered HTML, not sprite refs still inside a
   spec).
3. Run `python build_pipeline/build.py <BookName>`.
4. **Bump `sw.js`'s `CACHE_VERSION`** — this is a site-file change like any
   other; `scripts/cache_bump_guard.py` (wired into the `pre-push` hook)
   will block the push if you forget.
5. Commit both the spec and the regenerated `books/*.html` together.

## Adding a new book

There's no scaffold command for this yet — the 14 specs in `specs/` are
all that exist to model from. Copy the shape of an existing spec with a
similar page count, write new content into it, add a new `<option>`/entry
wherever `index.html` lists books (not handled by this pipeline), then
`python build_pipeline/build.py <NewBookName>`.

## What this pipeline does NOT do

- Doesn't touch `games/` (self-contained, embedded-art files — a
  different, not-yet-templated situation; see the root README/context.md
  on the games' v2-engine gap for what's already covered there)
- Doesn't touch `index.html`, `characters.html`, `grants.html`,
  `stats.html`, `privacy.html`, `manifest.json`, or `sw.js`
- Doesn't validate that sprite filenames referenced in a spec actually
  exist in `assets/sprites/` — a bad edit renders a broken `<img>` with no
  warning until someone looks at the page
- Doesn't add or remove pages by editing the page count alone — the spec's
  `pages` list drives `total`, but hotspot behavior, image counts per
  page, and other per-page conventions established across the 14 existing
  books aren't enforced; a wildly different page shape will still render,
  just may not look/behave like the others
