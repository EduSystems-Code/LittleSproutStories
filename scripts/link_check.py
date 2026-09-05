"""
Internal link check — since index.html must stay at repo root and every
page depends on relative paths, this walks all HTML files, extracts
local href/src targets, and flags any that don't resolve to a real file.
No network calls, no external-link checking (that's a different problem)
— just catching the broken-relative-path bug that restructuring causes.

Usage (from repo root):
    python scripts/link_check.py
"""

import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r'(?:href|src)=["\']([^"\']+)["\']')
SKIP_DIRS = {".git", "node_modules", "scripts"}


def is_local(url: str) -> bool:
    if not url or url.startswith(("#", "mailto:", "tel:", "javascript:")):
        return False
    # href/src inside a <script> that builds markup from a JS template
    # literal ("...href=\"${x}\"...") or a {{handlebars}} placeholder --
    # not a real static path, nothing to resolve on disk.
    if "${" in url or "{{" in url:
        return False
    parsed = urllib.parse.urlparse(url)
    return not parsed.scheme and not parsed.netloc


def main() -> int:
    broken: list[tuple[str, str]] = []
    checked = 0

    for path in REPO_ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for match in LINK_RE.finditer(text):
            url = match.group(1)
            if not is_local(url):
                continue
            checked += 1
            target = url.split("#")[0].split("?")[0]
            if not target:
                continue
            resolved = (path.parent / urllib.parse.unquote(target)).resolve()
            if not resolved.exists():
                rel_source = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                broken.append((rel_source, url))

    print(f"Checked {checked} local link(s) across the site.")
    if not broken:
        print("No broken internal links found.")
        return 0

    print(f"\n{len(broken)} broken link(s):")
    for source, url in broken:
        print(f"  {source} -> {url}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
