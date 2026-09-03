# LittleSprout Stories

Interactive phonics storybooks and feelings games for early readers, ages 4–7.

Fourteen storybooks and three games starring Maya, Marcus, Sophie, and James, built on a
"Double Engine" model: every page pairs decodable phonics text with a social-emotional
learning beat.

**Live site:** https://edusystems-code.github.io/LittleSproutStories/

---

## Structure

```
index.html          Home — library, games, badge shelf, Maryland resources
characters.html     Meet the Friends — all four kids, all five expressions
privacy.html        Privacy policy (no data collected)
manifest.json       PWA manifest — lets the site install to a home screen
sw.js               Service worker — offline support
assets/sprites/     87 character PNGs, shared by every page
assets/icons/       App icons for installed/home-screen use
books/              14 storybooks (~23KB each, reference assets/sprites/)
games/              3 games (currently self-contained w/ embedded art)
rewards-api/        FastAPI backend — reward box, Shop, cork board. Deploys
                    separately to Render; GitHub Pages ignores this folder.
.nojekyll           Tells GitHub Pages to serve files as-is
```

Static site — no build step, no server code, no dependencies. Plain HTML/CSS/JS.

The one exception is [`rewards-api/`](rewards-api/README.md) — a small FastAPI
backend for paid orders (the reward box and the Shop) and the community cork
board. It is **not** part of the static site: Pages serves the repo root and
ignores that folder, while the backend runs as its own Render web service from
the subdirectory (`rootDir: rewards-api`, see `rewards-api/render.yaml`). It was
previously the separate repo `EduSystems-Code/LittleSprout-Rewards`, consolidated
here on 2026-09-03.

---

## Deploying to GitHub Pages

Once pushed, go to **Settings → Pages → Source: Deploy from a branch → `main` / `(root)`**.
The site is live in about a minute at the URL above.

`index.html` must stay at the repo root. All internal links are relative, so nothing
needs to change between local preview and the live site.

**Local preview** — open `index.html` directly, or for a closer match to production:
```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

---

## Editing

**Site copy, layout, resources** — edit `index.html` or `characters.html` directly.

**Storybook content** — do *not* edit files in `books/`. They are generated and get
overwritten. Edit the page specs in the build pipeline instead, then rebuild. See
`build_pipeline/README.md`.

**Character art** — add processed sprites to `assets/sprites/` using the naming
convention `character_expression_pose.png`. Expressions: `happy`, `neutral`, `sad`,
`surprised`, `frustrated`. Poses: `standing`, `sitting`, `walking`, `running`, `jumping`,
`waving`, `kneeling`, `pointing`, `looking`, `reaching`, `giving`, `hands`.

Don't crop/resize/rename by hand. Drop the Canva/Gemini-exported
character-sheet zip in `raw_art/` (gitignored) and run:
```bash
python scripts/import_character_art.py
```
It crops each image to its real content, resizes, and writes correctly-named
files straight into `assets/sprites/`. See its module docstring for details.

---

## Suggested workflow

Work on a branch, not directly on `main`:

```bash
git checkout -b add-backgrounds
# make changes
git add -A
git commit -m "Add fire station background art"
git push -u origin add-backgrounds
```

Then open a Pull Request on GitHub. Pages keeps serving `main`, so the live site stays
working while you experiment. Merge when you're happy.

**Keep `main` deployable.** If it's on `main`, it's live.

---

## Features

- **Read-aloud.** Every story page has a "Read to me" button using the browser's built-in
  speech engine. Words highlight as they're spoken. No network calls, no cost, no API key.
  Hidden automatically on browsers without speech support.
- **Progress + badges.** Finishing a book saves a badge to `localStorage`. The home page
  shows a badge shelf and ticks finished books. Device-local only; nothing is transmitted.
  A "Clear saved progress" button wipes it.
- **Offline.** A service worker caches the shell on install and caches books, games, and
  sprites as they're opened, so anything read once opens again with no connection.
- **Installable.** `manifest.json` lets a parent add LittleSprout to a tablet home screen.
- **Accessibility.** Keyboard paging (arrow keys), Escape stops narration, visible focus
  rings, skip link, ARIA live regions on quiz feedback, `prefers-reduced-motion` respected,
  and an "Aa Easier to read" toggle that increases letter/word/line spacing.

### Bumping the cache after an update
`sw.js` has `CACHE_VERSION` near the top. **Change it whenever you change site files**
(e.g. `littlesprout-v1` → `littlesprout-v2`), otherwise returning visitors keep getting the
old cached copy. This is the single most common cause of "I pushed a fix but it looks the same."

## Known placeholders

These are real gaps, documented so nobody mistakes them for finished work:

- ~~Backgrounds~~ — done. Real illustrated art (`assets/backgrounds/`) via
  `scripts/import_background_art.py`, sourced from BackgroundForge exports in
  `raw_art/backgrounds/`. All twelve `backdrop-*` locations, including
  `backdrop-police`, now use real art instead of a flat gradient. Mr.
  Rodriguez's specific classroom (`backdrop-classroom`) is wired to Book5's
  one page that actually features him as the on-page helper; every other
  School-related page (including Book5's other rooms and Book15's
  classroom-flavored recap) stays on `backdrop-school`'s general room.
- **Helper characters.** The eleven community helpers — Alex, Jasmine, Ms. Chen,
  Dr. Patel, Mr. Rodriguez, Mr. Smith, Keisha, Tom, Rose, David, Nurse Aisha — render as
  an emoji plus a name label in a `.helper-slot` div. The series is named after these
  characters and none of them are drawn yet.
- ~~Games still embed their art~~ — done. All three games (`games/*.html`)
  now reference `assets/sprites/` instead of ~3.6MB of embedded base64 —
  the `SPRITES` lookup object's values are relative paths, not data URIs.
  Games use the `happy` expression exclusively (they're not narrative
  scenes, so only one expression per pose was ever embedded).

---

## Series note

Book 13 was scrapped during development. The series runs 1–12, 14, 15 — fourteen books.
Numbering was left as-is rather than resequencing.
