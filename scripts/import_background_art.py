"""
Background art import — turns a BackgroundForge_<slug>_variations.zip
(5 JPG variants per location) into one optimized image per backdrop CSS
class in assets/backgrounds/.

Exists for the same reason import_character_art.py does: the art arrives
as a downloaded zip, and getting it from "on the Desktop/Downloads" to
"correctly named, correctly sized, wired into the site" used to be a
manual multi-step job.

Usage (from repo root):
    python scripts/import_background_art.py            # scan raw_art/backgrounds/*.zip
    python scripts/import_background_art.py --check     # report the slug->class
                                                          # mapping without writing anything

Picks variant 1 of each zip's 5 by default -- all 5 were reviewed by eye
across a representative sample (interior and exterior) before this
script was written; not a blind choice. The other 4 variants stay in
raw_art/backgrounds/, available if a different one is ever preferred --
this script doesn't delete the source zips.
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

# BackgroundForge slug -> the site's real backdrop-<suffix> CSS class,
# confirmed against build_pipeline/render.py's actual CSS (never assumed).
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

ZIP_NAME_RE = re.compile(r"^BackgroundForge_(.+)_variations\.zip$")

TARGET_MAX_WIDTH = 960  # ~2x the site's ~640px max content width -- crisp
                         # on retina, without shipping the full 1376px original
JPEG_QUALITY = 80


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
        m = ZIP_NAME_RE.match(zp.name)
        if not m:
            skipped.append(f"{zp.name}: doesn't match the BackgroundForge_<slug>_variations.zip pattern")
            continue
        slug = m.group(1)
        css_class = SLUG_TO_CLASS.get(slug)
        if css_class is None:
            skipped.append(f"{zp.name}: slug '{slug}' has no mapped backdrop class (see script header)")
            continue

        with zipfile.ZipFile(zp) as zf:
            var1_names = sorted(
                n for n in zf.namelist() if n.lower().endswith("_var1.jpg")
            )
            if not var1_names:
                skipped.append(f"{zp.name}: no *_var1.jpg found inside")
                continue
            with TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                zf.extract(var1_names[0], tmp_path)
                src = tmp_path / var1_names[0]
                before = src.stat().st_size
                out_path = BACKGROUNDS_DIR / f"{css_class}.jpg"

                if check_only:
                    print(f"{zp.name} -> {out_path.relative_to(REPO_ROOT)} (slug '{slug}')")
                    mapped.append(css_class)
                    continue

                img = process_image(src)
                img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
                after = out_path.stat().st_size
                total_before += before
                total_after += after
                mapped.append(css_class)
                print(f"{zp.name} -> {out_path.relative_to(REPO_ROOT)}  "
                      f"({before/1024:.0f}KB -> {after/1024:.0f}KB)")

    print()
    print(f"Mapped: {len(mapped)} ({', '.join(sorted(mapped))})")
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
