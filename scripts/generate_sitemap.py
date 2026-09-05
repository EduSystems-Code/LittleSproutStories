"""
Generates sitemap.xml from the real repo contents, so it can't silently
drift the way a hand-maintained list would once a book or game is added
or renamed. Also writes robots.txt (static -- just points at the
sitemap) if it doesn't already exist.

Usage (from repo root):
    python scripts/generate_sitemap.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://edusystems-code.github.io/LittleSproutStories"

# Top-level pages worth a search engine's attention. index.html's own
# in-page anchors (#library, #games, #resources) aren't separate URLs,
# so they're not listed here.
TOP_LEVEL_PAGES = [
    ("", "1.0"),  # site root -- serves the same content as index.html, so
                  # that's not listed separately (avoids a duplicate-URL
                  # signal to search engines for one page)
    ("characters.html", "0.7"),
    ("book-nook.html", "0.6"),
    ("grants.html", "0.6"),
    ("stats.html", "0.6"),
    ("privacy.html", "0.3"),
]


def main() -> int:
    books = sorted((REPO_ROOT / "books").glob("*.html"))
    games = sorted((REPO_ROOT / "games").glob("*.html"))

    urls: list[tuple[str, str]] = list(TOP_LEVEL_PAGES)
    urls += [(f"books/{f.name}", "0.8") for f in books]
    urls += [(f"games/{f.name}", "0.8") for f in games]

    entries = "\n".join(
        f'  <url><loc>{SITE_URL}/{path}</loc><priority>{priority}</priority></url>'
        for path, priority in urls
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    (REPO_ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8", newline="\n")
    print(f"sitemap.xml written with {len(urls)} URLs "
          f"({len(TOP_LEVEL_PAGES)} top-level, {len(books)} books, {len(games)} games)")

    robots_path = REPO_ROOT / "robots.txt"
    if not robots_path.exists():
        robots_path.write_text(
            "User-agent: *\n"
            "Allow: /\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n",
            encoding="utf-8", newline="\n",
        )
        print("robots.txt created")
    else:
        print("robots.txt already exists, left untouched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
