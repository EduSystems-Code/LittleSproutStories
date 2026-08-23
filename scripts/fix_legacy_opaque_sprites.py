"""
One-time fix for a real bug found 2026-08-23, in two flavors:

1. A legacy asset format with NO real alpha transparency (a near-white
   background baked into the opaque pixels) — 22 "happy" sprites for
   Marcus/Sophie/James that no character-sheet batch ever included, so
   they were never touched by any import. import_character_art.py's
   crop only reads the alpha channel, so on these it found "content"
   touching every edge of the canvas and cropped nothing.
2. A file that DOES have real transparency but was simply never run
   through the crop pipeline at all — a naive bbox on it still touches
   every edge (paper-texture noise or a wide margin reaching the
   border), the exact failure mode the erosion-based robust_crop
   already exists to solve, just never applied here.

Both produce the same visible symptom: a wrong, wide/landscape aspect
ratio sitting next to every other sprite's tall/portrait crop — what
made the homepage cards look inconsistently sized, like a "poorly cut
out picture slapped on each panel."

For (1), removes the near-white background via a border-seeded flood
fill first (so light-colored details INSIDE the character, like white
shoes, are never touched — only background connected to the canvas
edge is). Either way, finishes through the same crop/resize/quantize
pipeline as every other sprite import, via import_character_art's own
functions (not a reimplementation).

Does NOT catch a file whose real content is a multi-pose reference
sheet or a duplicated panel (several found and fixed by hand
2026-08-23 — see commit history) — those need a human/visual judgment
call about which panel is correct, not a crop.

Usage (from repo root):
    python scripts/fix_legacy_opaque_sprites.py           # scan + fix all
    python scripts/fix_legacy_opaque_sprites.py --check   # report only,
                                                            # fix nothing
"""

import sys
from collections import deque
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_character_art import SPRITES_DIR, robust_crop, TARGET_MAX_HEIGHT, QUANTIZE_COLORS  # noqa: E402

# "Near enough to fully opaque" rather than an exact ==255 check — a
# real file was missed by an exact-equality check because one export
# left its background at alpha 254, not 255.
NEAR_OPAQUE_THRESHOLD = 250


def needs_bg_removal(img: Image.Image) -> bool:
    """True if the image has ~zero real transparency anywhere — the
    signature of the legacy opaque-background format."""
    alpha = img.convert("RGBA").split()[-1]
    lo, _hi = alpha.getextrema()
    return lo >= NEAR_OPAQUE_THRESHOLD


# Every correctly-cropped standing/sitting/etc. character sprite on this
# site is portrait-oriented (noticeably taller than wide — a tight crop
# on a full-body character just looks like that). A landscape or
# near-square file is the real, reliable signature of "never actually
# cropped" — NOT "does its own bbox touch every edge," which is also
# true of any already-correctly-cropped file (a tight crop's content
# fills its own canvas by definition) and produced false positives on
# fine files when tried.
WIDE_RATIO_THRESHOLD = 0.85


def needs_fixing(img: Image.Image) -> bool:
    w, h = img.size
    if h == 0:
        return False
    return (w / h) > WIDE_RATIO_THRESHOLD


def remove_near_white_background(img: Image.Image, tolerance: int = 20) -> Image.Image:
    """Border-seeded flood fill: only background pixels reachable from
    the canvas edge through other near-background pixels become
    transparent. An isolated near-white patch inside the character
    (a shoe, a highlight) is never touched, because it isn't connected
    to the edge through a chain of matching pixels."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    bg = px[0, 0][:3]

    def close(c):
        return (abs(c[0] - bg[0]) <= tolerance
                and abs(c[1] - bg[1]) <= tolerance
                and abs(c[2] - bg[2]) <= tolerance)

    visited = bytearray(w * h)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            idx = y * w + x
            if not visited[idx] and close(px[x, y][:3]):
                visited[idx] = 1
                dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            idx = y * w + x
            if not visited[idx] and close(px[x, y][:3]):
                visited[idx] = 1
                dq.append((x, y))

    while dq:
        x, y = dq.popleft()
        r, g, b, _a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx] and close(px[nx, ny][:3]):
                    visited[idx] = 1
                    dq.append((nx, ny))
    return img


def fix_one(path: Path) -> bool:
    """Returns True if it was actually fixed."""
    img = Image.open(path)
    if not needs_fixing(img):
        return False

    working = remove_near_white_background(img) if needs_bg_removal(img) else img.convert("RGBA")
    cropped = robust_crop(working)
    if cropped is None:
        print(f"  WARNING: {path.name} — nothing left after crop, skipped")
        return False

    w, h = cropped.size
    if h > TARGET_MAX_HEIGHT:
        target_w = max(1, round(w * TARGET_MAX_HEIGHT / h))
        cropped = cropped.resize((target_w, TARGET_MAX_HEIGHT), Image.LANCZOS)
    result = cropped.quantize(colors=QUANTIZE_COLORS, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)
    result.save(path)
    return True


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    fixed = []
    for f in sorted(SPRITES_DIR.glob("*.png")):
        img = Image.open(f)
        if needs_fixing(img):
            before = img.size
            reason = "opaque legacy format" if needs_bg_removal(img) else "never cropped"
            if check_only:
                print(f"{f.name}: {reason}, {before} -- would fix")
            else:
                fix_one(f)
                after = Image.open(f).size
                print(f"{f.name} ({reason}): {before} -> {after}")
            fixed.append(f.name)

    print()
    if not fixed:
        print("No files need fixing.")
    elif check_only:
        print(f"{len(fixed)} file(s) would be fixed. Run without --check to apply.")
    else:
        print(f"Fixed {len(fixed)} file(s).")
        print("Remember: assets/sprites/ changed, so sw.js's CACHE_VERSION needs a bump.")
        print("A file whose real content is a multi-pose sheet or duplicate panel won't be")
        print("caught here -- check anything with an unusually wide result by eye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
