"""Write the intro film into a HyperFrames project and (optionally) render it to MP4.

    python tools/build_intro.py <hyperframes-project-folder> [--render out.mp4]

The composition is the same page the app plays live (``dashboard/intro.py``), filled with the latest validated numbers
(``data_processing/intro_payload.py``). Rendering needs Node, FFmpeg and Chrome (see ``npx hyperframes doctor``)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard import intro  # noqa: E402
from data_processing import intro_payload  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path, help="a HyperFrames project folder (npx hyperframes init ...)")
    ap.add_argument("--render", type=Path, default=None, help="also render to this MP4 path")
    args = ap.parse_args()

    payload = intro_payload.read()
    if payload is None:   # first run: build the validated tables once
        from data_processing.pipeline import build_dashboard_data

        build_dashboard_data()
        payload = intro_payload.read()
    if payload is None:
        print("no data to put in the intro: run the dashboard once so the tables exist", file=sys.stderr)
        return 1
    args.project.mkdir(parents=True, exist_ok=True)
    out = args.project / "index.html"
    out.write_text(intro.standalone_html(payload), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, {len(payload.get('kpis', []))} indicators, map: {bool(payload.get('map'))})")
    if args.render:
        cmd = ["npx", "--yes", "hyperframes", "render", "--workers", "2", "--output", str(args.render.resolve())]
        print(" ".join(cmd))
        return subprocess.call(cmd, cwd=args.project, shell=(sys.platform == "win32"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
