"""
Character art import — turns a Canva/Gemini-generated character sheet
zip into properly-named, properly-sized files in assets/sprites/, with
no manual cropping/renaming/resizing step.

Exists because that whole chain used to be manual: generate art in
Canva, download a zip, drop it on the Desktop, then someone (a person or
an agent) has to find it, unzip it, figure out which files are new vs
upgrades, crop each to its real content (a naive alpha bbox breaks on a
source image whose drop-shadow touches the canvas edge — this uses an
erosion-based crop that doesn't), resize, and get the naming convention
right. This script is that whole chain, run as one command.

Usage (from repo root):
    python scripts/import_character_art.py                 # scan raw_art/*.zip
    python scripts/import_character_art.py path/to/one.zip  # or specific zip(s)
    python scripts/import_character_art.py --skip-existing  # only fill real
                                                              # gaps; never
                                                              # overwrite a
                                                              # sprite that's
                                                              # already there
                                                              # (for a batch
                                                              # that's a full
                                                              # re-generation,
                                                              # not a
                                                              # deliberate
                                                              # resolution
                                                              # upgrade)

Expects source filenames matching the character-sheet export pattern:
    {Character}_{pose}_{expression}_{index}.png
e.g. Sophie_standing_neutral_9.png — where {pose} is always one of the
site's known poses (single word) and {expression} can be one word
(neutral, sad, ...) OR a multi-word label a batch sometimes uses
instead of the site's plain name (e.g. a real export used
"big_happy_smile" for what the site calls "happy" — see EXPRESSION_ALIASES
below; that's a normalization, not a guess, since the other four
expressions in that same batch matched the site's plain names exactly).

Writes to assets/sprites/{character}_{expression}_{pose}.png (lowercase),
matching the naming convention the root README documents. A file whose
pose isn't recognized, or whose expression doesn't normalize to one of
the site's five, is skipped and reported — never silently guessed at.
"""

import re
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = REPO_ROOT / "assets" / "sprites"
RAW_ART_DIR = REPO_ROOT / "raw_art"

FILENAME_RE = re.compile(r"^([A-Za-z]+)_(.+)_(\d+)\.png$")

# The site's full documented vocabulary (root README, "Character art"),
# used both to parse pose/expression out of a filename and to report
# what's still missing after an import.
CHARACTERS = ["maya", "marcus", "sophie", "james"]
EXPRESSIONS = ["happy", "neutral", "sad", "surprised", "frustrated"]

# Real-world export labels seen that don't match the site's plain
# expression names, mapped to what they actually mean. Add to this only
# when a batch's other files already confirm the pattern (e.g. this one
# batch's neutral/sad/surprised/frustrated all matched exactly, and
# "big_happy_smile" was clearly the 5th, filling the "happy" slot).
EXPRESSION_ALIASES = {
    "big_happy_smile": "happy",
}
POSES = ["standing", "sitting", "walking", "running", "jumping", "waving",
         "kneeling", "pointing", "looking", "reaching", "giving", "hands"]

TARGET_MAX_HEIGHT = 660  # 3x the site's 220px CSS display height — plenty for retina
QUANTIZE_COLORS = 256


def robust_crop(img: Image.Image) -> Image.Image | None:
    """Crop to real content, ignoring thin/isolated edge artifacts (a
    faint drop-shadow touching the canvas edge broke a naive alpha bbox
    on one real source file — this erodes those away first)."""
    alpha = img.split()[-1]
    eroded = alpha.filter(ImageFilter.MinFilter(5))
    bbox = eroded.getbbox()
    if bbox is None:
        return None
    pad = 8
    w, h = img.size
    x0, y0 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
    x1, y1 = min(w, bbox[2] + pad), min(h, bbox[3] + pad)
    return img.crop((x0, y0, x1, y1))


def process_image(src_path: Path) -> Image.Image | None:
    img = Image.open(src_path).convert("RGBA")
    cropped = robust_crop(img)
    if cropped is None:
        return None
    w, h = cropped.size
    if h > TARGET_MAX_HEIGHT:
        target_w = max(1, round(w * TARGET_MAX_HEIGHT / h))
        cropped = cropped.resize((target_w, TARGET_MAX_HEIGHT), Image.LANCZOS)
    return cropped.quantize(colors=QUANTIZE_COLORS, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG)


def parse_filename(name: str) -> tuple[str, str, str] | None:
    """Returns (char, expr, pose), all lowercase, or None if the pose
    isn't recognized or the expression doesn't normalize to one of the
    site's five (see EXPRESSION_ALIASES) — never a guess."""
    m = FILENAME_RE.match(name)
    if not m:
        return None
    char, middle, _index = m.groups()
    tokens = middle.lower().split("_")

    pose = tokens[0]
    if pose not in POSES:
        return None
    expr_raw = "_".join(tokens[1:])
    if not expr_raw:
        return None
    expr = EXPRESSION_ALIASES.get(expr_raw, expr_raw)
    if expr not in EXPRESSIONS:
        return None
    return char.lower(), expr, pose


def import_zip(zip_path: Path, skip_existing: bool = False) -> tuple[int, int, list[str]]:
    """Returns (upgraded_count, added_count, skipped_reasons).

    skip_existing=True never overwrites a sprite that's already there —
    for a batch that's a full re-generation (not a deliberate resolution
    upgrade), where the point is only to fill real gaps and the existing
    file is already known to be as good or better. In that mode
    upgraded_count is always 0 by definition; skipped_reasons notes how
    many existing files were left untouched instead."""
    upgraded, added, skipped = 0, 0, []
    kept_existing = 0

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".png")]
            parsed = {n: parse_filename(Path(n).name) for n in names}
            matched = [n for n in names if parsed[n] is not None]
            unmatched = [n for n in names if parsed[n] is None]
            if not matched:
                skipped.append(f"{zip_path.name}: no files matched the expected "
                                f"Character_pose_expression_N.png pattern, skipped entirely")
                return 0, 0, skipped
            for n in unmatched:
                skipped.append(f"{Path(n).name}: unrecognized pose or expression, skipped")
            zf.extractall(tmp_path, members=matched)

        seen_keys = {}
        for n in matched:
            char, expr, pose = parsed[n]
            key = (char, expr, pose)
            seen_keys[key] = tmp_path / n  # last one wins; content is identical for true dupes

        for (char, expr, pose), src in sorted(seen_keys.items()):
            out_path = SPRITES_DIR / f"{char}_{expr}_{pose}.png"
            existed = out_path.exists()
            if existed and skip_existing:
                kept_existing += 1
                continue
            result = process_image(src)
            if result is None:
                skipped.append(f"{src.name}: fully transparent, no content found")
                continue
            result.save(out_path)
            if existed:
                upgraded += 1
            else:
                added += 1

    if kept_existing:
        skipped.append(f"{zip_path.name}: kept {kept_existing} existing sprite(s) untouched "
                        f"(--skip-existing)")

    return upgraded, added, skipped


def report_missing() -> list[str]:
    missing = []
    for c in CHARACTERS:
        for e in EXPRESSIONS:
            for p in POSES:
                if not (SPRITES_DIR / f"{c}_{e}_{p}.png").exists():
                    missing.append(f"{c}_{e}_{p}")
    return missing


def main() -> int:
    args = sys.argv[1:]
    skip_existing = "--skip-existing" in args
    args = [a for a in args if a != "--skip-existing"]

    if args:
        targets = [Path(a) for a in args]
    else:
        RAW_ART_DIR.mkdir(exist_ok=True)
        targets = sorted(RAW_ART_DIR.glob("*.zip"))
        if not targets:
            print(f"No zips found in {RAW_ART_DIR.relative_to(REPO_ROOT)}/ — "
                  f"drop a character-sheet zip there, or pass a path directly.")
            return 0

    total_upgraded = total_added = 0
    all_skipped = []
    for zp in targets:
        if not zp.exists():
            print(f"Not found: {zp}")
            continue
        up, add, skipped = import_zip(zp, skip_existing=skip_existing)
        total_upgraded += up
        total_added += add
        all_skipped.extend(skipped)
        print(f"{zp.name}: {up} upgraded, {add} added")

    print()
    print(f"Total: {total_upgraded} upgraded, {total_added} added")
    if all_skipped:
        print("\nSkipped:")
        for s in all_skipped:
            print(f"  {s}")

    missing = report_missing()
    if missing:
        print(f"\nStill missing ({len(missing)} of {len(CHARACTERS)*len(EXPRESSIONS)*len(POSES)} "
              f"in the full character x expression x pose grid):")
        by_char = {}
        for m in missing:
            c = m.split("_")[0]
            by_char.setdefault(c, []).append(m)
        for c, items in by_char.items():
            print(f"  {c}: {len(items)} missing")

    if total_upgraded or total_added:
        print("\nRemember: assets/sprites/ changed, so sw.js's CACHE_VERSION needs a bump "
              "before this ships (scripts/cache_bump_guard.py, on the pre-push hook, will "
              "catch it if you forget).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
