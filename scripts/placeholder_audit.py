"""
Placeholder audit — counts real, documented placeholder markers
(BACKGROUND-SWAP, HERO-ART-SWAP, and any *-SWAP convention that gets
added later) across the site, so "what's still placeholder" stays a
grounded count instead of a guess in context.md.

Usage (from repo root):
    python scripts/placeholder_audit.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER_RE = re.compile(r"[A-Z][A-Z0-9_-]*-SWAP")
SCAN_EXTS = {".html", ".js", ".css"}
SKIP_DIRS = {".git", "node_modules", "scripts"}


def main() -> int:
    counts: dict[str, list[str]] = {}

    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in SCAN_EXTS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in MARKER_RE.finditer(text):
            marker = match.group(0)
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            counts.setdefault(marker, []).append(rel)

    if not counts:
        print("No placeholder markers found — art backlog is clear.")
        return 0

    total = sum(len(v) for v in counts.values())
    print(f"{total} placeholder marker(s) found:\n")
    for marker, files in sorted(counts.items()):
        print(f"  {marker}: {len(files)}")
        for f in files[:10]:
            print(f"    - {f}")
        if len(files) > 10:
            print(f"    ... and {len(files) - 10} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
