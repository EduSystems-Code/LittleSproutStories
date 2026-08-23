"""
The one command the README asks for: rebuild books/*.html from
build_pipeline/specs/*.json.

    python build_pipeline/build.py            # rebuild every book from its spec
    python build_pipeline/build.py Book1_Maya_Marcus_FireStation   # rebuild one

Round-trip verified against the real, live books at the time this pipeline
was built (2026-08-23): every one of the 14 specs, re-rendered, produced a
byte-identical file to what was already published — see git history on
build_pipeline/ for that verification run. That guarantee holds only as
long as specs/*.json and render.py are the source of truth; if a book was
hand-edited outside the pipeline since, re-run
extract_spec.py --all first to bring specs/ back in sync (and accept you
may be overwriting an edit that didn't go through the pipeline).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import main as render_main  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--all")
    else:
        name = sys.argv[1]
        spec_path = Path(__file__).resolve().parent / "specs" / f"{name}.json"
        if not spec_path.exists():
            print(f"No spec found at {spec_path}")
            raise SystemExit(1)
        sys.argv[1] = str(spec_path)
    raise SystemExit(render_main())
