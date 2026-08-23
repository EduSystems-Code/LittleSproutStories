"""
Cache-bump guard — catches the README's own #1 documented bug:
forgetting to bump sw.js's CACHE_VERSION after a site-file change, so
returning visitors keep serving a stale cached copy.

Compares working-tree + staged changes against HEAD, AND (when run as a
pre-push hook) every commit about to be pushed against the upstream tip.
Checking only the working tree misses the common case where the site
changes were already committed before this hook runs — the exact way
this guard passed vacuously the first time it shipped. If any site file
changed but CACHE_VERSION didn't move, it fails loud instead of letting
a silent "I pushed a fix but it looks the same" ship.

Usage (from repo root):
    python scripts/cache_bump_guard.py

As a pre-push hook, git passes the push range on stdin ("<local ref>
<local sha> <remote ref> <remote sha>" per line); pass it through
unchanged and this script reads it. Falls back to working-tree-only
checking when run standalone with no stdin range (e.g. a pre-commit
hook, or manual invocation).
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


def pushed_range_files() -> list[str] | None:
    """Files changed across the commits about to be pushed (pre-push stdin
    range), or None if stdin has no usable range (not run as pre-push)."""
    if sys.stdin.isatty():
        return None
    stdin_data = sys.stdin.read()
    for line in stdin_data.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == "0" * 40:
            continue  # deleting the branch, nothing to check
        base = remote_sha if remote_sha != "0" * 40 else f"{local_sha}~1"
        result = subprocess.run(
            ["git", "diff", "--name-only", base, local_sha],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return [f.strip().replace("\\", "/") for f in result.stdout.splitlines() if f.strip()]
    return None


def cache_version_in(text: str) -> str | None:
    m = re.search(r"CACHE_VERSION\s*=\s*'([^']+)'", text)
    return m.group(1) if m else None


def main() -> int:
    range_files = pushed_range_files()
    mode = "push range" if range_files is not None else "working tree"
    files = range_files if range_files is not None else changed_files()

    if not files:
        print("No changes to check.")
        return 0

    # Ignore files that don't affect what the service worker serves.
    IGNORE_PREFIXES = ("scripts/", "build_pipeline/", ".git", "README.md", "CLAUDE.md")
    site_files_changed = [
        f for f in files
        if not f.startswith(IGNORE_PREFIXES) and f != "sw.js"
    ]

    if not site_files_changed:
        print(f"No site files changed in {mode} - cache version not relevant.")
        return 0

    sw_changed = "sw.js" in files
    working_version = cache_version_in(SW_JS.read_text(encoding="utf-8"))

    # Compare against the pre-push base when checking a push range (files
    # changed there are already committed, so HEAD == the tip being pushed
    # and comparing to it would always show "no change"); otherwise HEAD.
    base_ref = "HEAD"
    if range_files is not None:
        # Re-derive the same base used by pushed_range_files(); if stdin
        # already consumed, fall back to HEAD~<n commits> is unreliable,
        # so just diff sw.js content at HEAD vs the merge-base with upstream.
        upstream = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        if upstream.returncode == 0 and upstream.stdout.strip():
            base_ref = upstream.stdout.strip()

    base_sw = subprocess.run(
        ["git", "show", f"{base_ref}:sw.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    base_version = cache_version_in(base_sw.stdout) if base_sw.returncode == 0 else None

    print(f"Site files changed ({mode}): {', '.join(site_files_changed)}")

    if not sw_changed or (base_version and working_version == base_version):
        print(
            f"WARNING: site files changed but CACHE_VERSION is still '{working_version}'. "
            "Bump it in sw.js before shipping, or returning visitors keep the stale cache."
        )
        return 1

    print(f"CACHE_VERSION bumped ({base_version} -> {working_version}). OK to proceed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
