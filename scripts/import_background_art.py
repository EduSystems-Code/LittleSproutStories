"""
Background art import — turns a zip of 5 JPG variants per location into
optimized images in assets/backgrounds/.

Exists for the same reason import_character_art.py does: the art arrives
as a downloaded zip, and getting it from "on the Desktop/Downloads" to
"correctly named, correctly sized, wired into the site" used to be a
manual multi-step job.

Usage (from repo root):
    python scripts/import_background_art.py            # scan raw_art/backgrounds/*.zip
    python scripts/import_background_art.py --check     # report the slug->class
                                                          # mapping without writing anything

For each location zip, writes all 5 variants as assets/backgrounds/<class>_1.jpg
.. <class>_5.jpg, AND <class>.jpg = variant 1 (unsuffixed, for the existing
`backdrop-<class>` CSS in build_pipeline/render.py, which every book
references by that exact path — books need no other change to pick up new
art). The suffixed variants exist so games (and, later, individual book
pages) can use a different variant than the books' default without another
import pass.

2026-09-11: recognizes two zip naming conventions, both 5-variant batches
covering the same 12 (of 13) backdrop locations:
  - BackgroundForge_<slug>_variations.zip  (the original 2026-08-24 batch,
    now archived to raw_art/backgrounds/archive_v1_single-variant/ since
    this script previously only ever extracted variant 1 from it)
  - LittleSprout_<slug>_Backgrounds.zip     (the 2026-09-11 full-overhaul
    batch)
Internal filenames differ per batch/location (e.g. "keisha_s_bakery_
kitchen_var1.jpg", "the_fire_station_var1.jpg") -- only the "_varN.jpg"
suffix is load-bearing, matched case-insensitively.
"""

import re
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKGROUNDS_DIR = REPO_ROOT / "assets" / "backgrounds"
RAW_ART_DIR = REPO_ROOT / "raw_art" / "backgrounds"

# slug -> the site's real backdrop-<suffix> CSS class, confirmed against
# build_pipeline/render.py's actual CSS (never assumed).
#
# "classroom" -> backdrop-classroom (added 2026-08-24): Mr. Rodriguez's
# specific room, used only on the one page across all books that actually
# features him as the on-page helper (Book5 p2, confirmed against that
# spec's own helper metadata) -- everywhere else School-related stays on
# backdrop-school/"big-school", per explicit instruction: classroom art
# for the Mr. Rodriguez page specifically, the general room everywhere
# else (including Book15's classroom-flavored recap pages, which never
# actually show him on-page).
SLUG_TO_CLASS = {
    "bakery": "bakery",
    "barbershop": "barbershop",
    "big-school": "school",
    "classroom": "classroom",
    "community-center": "center",
    "crosswalk": "street",
    "doctor": "doctor",
    "fire-station": "firestation",
    "garden": "garden",
    "library": "library",
    "police-station": "police",
    "post-office": "postoffice",
    "repair-shop": "repair",
}

ZIP_NAME_PATTERNS = [
    re.compile(r"^BackgroundForge_(.+)_variations\.zip$", re.IGNORECASE),
    re.compile(r"^LittleSprout_(.+)_Backgrounds\.zip$", re.IGNORECASE),
]
VARIANT_RE = re.compile(r"_var([1-5])\.jpe?g$", re.IGNORECASE)

TARGET_MAX_WIDTH = 960  # ~2x the site's ~640px max content width -- crisp
                         # on retina, without shipping the full-res original
JPEG_QUALITY = 80


def match_slug(zip_name: str):
    for pattern in ZIP_NAME_PATTERNS:
        m = pattern.match(zip_name)
        if m:
            return m.group(1)
    return None


def process_image(src_path: Path) -> Image.Image:
    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    if w > TARGET_MAX_WIDTH:
        target_h = round(h * TARGET_MAX_WIDTH / w)
        img = img.resize((TARGET_MAX_WIDTH, target_h), Image.LANCZOS)
    return img


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)

    zips = sorted(RAW_ART_DIR.glob("*.zip"))
    if not zips:
        print(f"No zips found in {RAW_ART_DIR.relative_to(REPO_ROOT)}/")
        return 0

    total_before = total_after = 0
    mapped, skipped = [], []

    for zp in zips:
        slug = match_slug(zp.name)
        if slug is None:
            skipped.append(f"{zp.name}: doesn't match a known zip naming pattern")
            continue
        css_class = SLUG_TO_CLASS.get(slug)
        if css_class is None:
            skipped.append(f"{zp.name}: slug '{slug}' has no mapped backdrop class (see script header)")
            continue

        with zipfile.ZipFile(zp) as zf:
            variants = {}  # variant number (str) -> zip member name
            for n in zf.namelist():
                m = VARIANT_RE.search(n)
                if m:
                    variants[m.group(1)] = n
            if not variants:
                skipped.append(f"{zp.name}: no *_var[1-5].jpg found inside")
                continue

            with TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                zip_before = zip_after = 0
                for num in sorted(variants):
                    member = variants[num]
                    zf.extract(member, tmp_path)
                    src = tmp_path / member
                    before = src.stat().st_size
                    out_path = BACKGROUNDS_DIR / f"{css_class}_{num}.jpg"

                    if check_only:
                        continue

                    img = process_image(src)
                    img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
                    zip_before += before
                    zip_after += out_path.stat().st_size

                    if num == "1":
                        # unsuffixed copy: what every existing backdrop-<class>
                        # CSS rule actually points at -- books need no other
                        # change to pick up new art.
                        primary_path = BACKGROUNDS_DIR / f"{css_class}.jpg"
                        img.save(primary_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

                if check_only:
                    print(f"{zp.name} -> {css_class}_[{'/'.join(sorted(variants))}].jpg + {css_class}.jpg (slug '{slug}')")
                    mapped.append(css_class)
                    continue

                total_before += zip_before
                total_after += zip_after
                mapped.append(css_class)
                print(f"{zp.name} -> {css_class}_1..{len(variants)}.jpg + {css_class}.jpg  "
                      f"({zip_before/1024:.0f}KB -> {zip_after/1024:.0f}KB, {len(variants)} variant(s))")

    print()
    print(f"Mapped: {len(mapped)} ({', '.join(sorted(mapped))})")
    missing = sorted(set(SLUG_TO_CLASS.values()) - set(mapped))
    if missing and not check_only:
        print(f"No zip covered these backdrop classes this run (old art kept as-is): {', '.join(missing)}")
    if skipped:
        print("Skipped:")
        for s in skipped:
            print(f"  {s}")
    if not check_only and total_before:
        print(f"\nTotal: {total_before/1024/1024:.1f}MB -> {total_after/1024/1024:.1f}MB")
        print("Remember: assets/backgrounds/ is new site content, so sw.js's "
              "CACHE_VERSION needs a bump.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
