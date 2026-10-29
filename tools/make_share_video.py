"""One command: the newest validated numbers -> a 10-second share clip (MP4) made with HyperFrames.

    python tools/make_share_video.py [--out docs/share_labour_market.mp4]

It rebuilds nothing by hand: the data come from the same validated tables as the dashboard (``data/processed/intro_payload.json``),
the composition is ``dashboard/intro.py``. Needs Node, FFmpeg and Chrome (``npx hyperframes doctor`` checks them); the first run
creates a scratch HyperFrames project in the temp folder."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import build_intro  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "share_labour_market.mp4")
    args = ap.parse_args()
    work = Path(tempfile.gettempdir()) / "lm-share-video"
    shell = sys.platform == "win32"
    if not (work / "hyperframes.json").exists() and not (work / "index.html").exists():
        work.parent.mkdir(parents=True, exist_ok=True)
        code = subprocess.call(["npx", "--yes", "hyperframes", "init", work.name, "--example", "blank"], cwd=work.parent, shell=shell)
        if code != 0:
            print("could not create the HyperFrames project (is Node installed? try `npx hyperframes doctor`)", file=sys.stderr)
            return code
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sys.argv = ["build_intro", str(work), "--render", str(args.out)]
    code = build_intro.main()
    if code == 0:
        print(f"share clip: {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)" if args.out.exists() else "render finished, but the file was not found")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
