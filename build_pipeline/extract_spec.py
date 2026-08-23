"""
Extracts a per-book JSON spec from an existing books/*.html file.

Exists to bootstrap build_pipeline/specs/*.json FROM the real, already-
published books — not from guessed content. Every field below was pulled
out of the live HTML by pattern, not typed by hand. Run once per book (or
via build.py --extract-all) whenever a book was hand-edited outside the
pipeline and specs/ needs to catch back up.

Usage:
    python build_pipeline/extract_spec.py books/Book1_Maya_Marcus_FireStation.html
    python build_pipeline/extract_spec.py --all
"""

import json
import re
import sys
from pathlib import Path

from common import find_balanced

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = REPO_ROOT / "books"
SPECS_DIR = Path(__file__).resolve().parent / "specs"


def extract_images(html: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r'<img class="char" src="\.\./assets/sprites/([^"]+)" alt="([^"]*)" loading="lazy">',
        html,
    ):
        out.append({"sprite": m.group(1), "alt": m.group(2)})
    return out


def extract_hotspots(html: str) -> list[dict]:
    out = []
    for m in re.finditer(
        r'<button class="hotspot ([\w\d]+)" onclick="(\w+)\(this\)" aria-label="([^"]*)" type="button">(.*?)</button>',
        html,
    ):
        out.append({
            "position": m.group(1),
            "effect": m.group(2),
            "aria_label": m.group(3),
            "emoji": m.group(4),
        })
    return out


def extract_helper(html: str) -> dict | None:
    m = re.search(
        r'<div class="helper-slot" role="img" aria-label="([^"]*)">(.*?)<div class="helper-label">[^<]*</div></div>',
        html,
    )
    if not m:
        return None
    return {"name": m.group(1), "emoji": m.group(2)}


def extract_quiz(html: str) -> dict | None:
    m = re.search(
        r'<div class="quiz" data-answer="(\d+)" role="group" aria-label="Question">\s*'
        r'<p class="quiz-q">(.*?)</p>\s*<div class="quiz-opts">(.*?)</div>\s*'
        r'<p class="quiz-feedback" role="status" aria-live="polite"></p>\s*</div>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    answer = int(m.group(1))
    question = m.group(2)
    opts_html = m.group(3)
    options = re.findall(
        r'<button type="button" onclick="checkAnswer\(this,(\d+)\)">(.*?)</button>',
        opts_html,
    )
    options_sorted = [text for _, text in sorted(options, key=lambda p: int(p[0]))]
    return {"question": question, "options": options_sorted, "answer": answer}


STAGE_ELEMENT_RE = re.compile(
    r'<img class="char" src="\.\./assets/sprites/(?P<img_sprite>[^"]+)" alt="(?P<img_alt>[^"]*)" loading="lazy">'
    r'|<div class="helper-slot" role="img" aria-label="(?P<helper_name>[^"]*)">(?P<helper_emoji>.*?)'
    r'<div class="helper-label">[^<]*</div></div>'
    r'|<button class="hotspot (?P<hs_pos>[\w\d]+)" onclick="(?P<hs_effect>\w+)\(this\)" '
    r'aria-label="(?P<hs_label>[^"]*)" type="button">(?P<hs_emoji>.*?)</button>',
    re.DOTALL,
)


def extract_stage(section_html: str) -> dict:
    m = re.search(r'<div class="stage ([\w-]+)">', section_html)
    if not m:
        return {"backdrop": None, "elements": []}
    cstart, cend = find_balanced(section_html, m.start(), "div")
    stage_html = section_html[cstart:cend]

    elements = []
    for em in STAGE_ELEMENT_RE.finditer(stage_html):
        if em.group("img_sprite") is not None:
            elements.append({"type": "img", "sprite": em.group("img_sprite"), "alt": em.group("img_alt")})
        elif em.group("helper_name") is not None:
            elements.append({"type": "helper", "name": em.group("helper_name"), "emoji": em.group("helper_emoji")})
        elif em.group("hs_pos") is not None:
            elements.append({
                "type": "hotspot", "position": em.group("hs_pos"), "effect": em.group("hs_effect"),
                "aria_label": em.group("hs_label"), "emoji": em.group("hs_emoji"),
            })
    return {"backdrop": m.group(1), "elements": elements}


def extract_text(section_html: str, cls: str) -> str | None:
    m = re.search(rf'<div class="{cls}">(.*?)</div>', section_html, re.DOTALL)
    return m.group(1) if m else None


def extract_book(html: str) -> dict:
    title = re.search(r"<title>(.*?) \| Little Sprout Stories</title>", html).group(1)
    book_id = re.search(r'const BOOK_ID = "([^"]+)"', html).group(1)
    book_title = re.search(r'const BOOK_TITLE = "([^"]+)"', html).group(1)
    book_badge = re.search(r'const BOOK_BADGE = "([^"]+)"', html).group(1)

    # cover (p0)
    cover_m = re.search(r'<div class="page-wrap" id="p0"[^>]*>', html)
    cs, ce = find_balanced(html, cover_m.start(), "div")
    cover_html = html[cs:ce]
    cover_h1 = re.search(r"<h1>(.*?)</h1>", cover_html, re.DOTALL).group(1)
    cover_stage = extract_stage(cover_html)

    # interior pages p1..p8 (however many exist)
    pages = []
    for pm in re.finditer(r'<div class="page-wrap" id="p(\d+)"[^>]*>', html):
        idx = int(pm.group(1))
        if idx == 0:
            continue
        ps, pe = find_balanced(html, pm.start(), "div")
        page_html = html[ps:pe]
        if 'class="page end-screen"' in page_html:
            continue
        pages.append({
            "index": idx,
            "stage": extract_stage(page_html),
            "text_a": extract_text(page_html, "text-a"),
            "text_b": extract_text(page_html, "text-b"),
            "quiz": extract_quiz(page_html),
        })
    pages.sort(key=lambda p: p["index"])

    # end screen (last page)
    end_m = re.search(r'<div class="page-wrap" id="p\d+"[^>]*>\s*<section class="page end-screen">', html)
    es, ee = find_balanced(html, end_m.start(), "div")
    end_html = html[es:ee]
    badge_m = re.search(
        r'<div class="badge"><span aria-hidden="true">(.*?)</span><div>(.*?)</div></div>',
        end_html,
    )
    feeling = re.search(r"<p><b>Feeling/skill:</b> (.*?)</p>", end_html).group(1)
    ask = re.search(r"<p><b>Ask your child:</b> (.*?)</p>", end_html).group(1)
    try_this = re.search(r"<p><b>Try this:</b> (.*?)</p>", end_html).group(1)
    standards = re.search(r'<p class="standards">Standards: (.*?)</p>', end_html).group(1)

    return {
        "book_id": book_id,
        "title": title,
        "book_title": book_title,
        "book_badge": book_badge,
        "cover": {
            "h1_html": cover_h1,
            "stage": cover_stage,
        },
        "pages": pages,
        "end_screen": {
            "badge_emoji": badge_m.group(1),
            "badge_label_html": badge_m.group(2),
            "feeling": feeling,
            "ask": ask,
            "try_this": try_this,
            "standards": standards,
        },
    }


def main() -> int:
    SPECS_DIR.mkdir(exist_ok=True)
    if len(sys.argv) == 2 and sys.argv[1] == "--all":
        targets = sorted(BOOKS_DIR.glob("*.html"))
    elif len(sys.argv) == 2:
        targets = [Path(sys.argv[1])]
    else:
        print("Usage: python extract_spec.py <books/BookN_....html> | --all")
        return 1

    for path in targets:
        html = path.read_text(encoding="utf-8")
        spec = extract_book(html)
        out_path = SPECS_DIR / (path.stem + ".json")
        out_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.name} -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
