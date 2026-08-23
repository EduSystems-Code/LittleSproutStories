"""
Cache-bump guard — catches the README's own #1 documented bug:
forgetting to bump sw.js's CACHE_VERSION after a site-file change, so
returning visitors keep serving a stale cached copy.

Compares working-tree + staged changes against HEAD. If any site file
changed but CACHE_VERSION didn't move, it fails loud instead of letting
a silent "I pushed a fix but it looks the same" ship.

Usage (from repo root):
    python scripts/cache_bump_guard.py

Wire it into a pre-commit hook or run it manually before pushing.
Exit 0 = safe to proceed, exit 1 = bump CACHE_VERSION first.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SW_JS = REPO_ROOT / "sw.js"


def changed_files() -> list[str]:
    """Files changed vs HEAD, staged or not (git status --porcelain)."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for line in result.stdout.splitlines():
        # format: "XY path" — path starts at column 4
        path = line[3:].strip()
        if path:
            files.append(path.replace("\\", "/"))
    return files


def cache_version_in(text: str) -> str | None:
    m = re.search(r"CACHE_VERSION\s*=\s*'([^']+)'", text)
    return m.group(1) if m else None


def main() -> int:
    files = changed_files()
    if not files:
        print("No changes to check.")
        return 0

    # Ignore files that don't affect what the service worker serves.
    IGNORE_PREFIXES = ("scripts/", ".git", "README.md", "CLAUDE.md")
    site_files_changed = [
        f for f in files
        if not f.startswith(IGNORE_PREFIXES) and f != "sw.js"
    ]

    if not site_files_changed:
        print("No site files changed - cache version not relevant.")
        return 0

    sw_changed = "sw.js" in files
    working_version = cache_version_in(SW_JS.read_text(encoding="utf-8"))

    head_sw = subprocess.run(
        ["git", "show", "HEAD:sw.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    head_version = cache_version_in(head_sw.stdout) if head_sw.returncode == 0 else None

    print(f"Site files changed: {', '.join(site_files_changed)}")

    if not sw_changed or (head_version and working_version == head_version):
        print(
            f"WARNING: site files changed but CACHE_VERSION is still '{working_version}'. "
            "Bump it in sw.js before shipping, or returning visitors keep the stale cache."
        )
        return 1

    print(f"CACHE_VERSION bumped ({head_version} -> {working_version}). OK to proceed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
