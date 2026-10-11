"""Build a clean source-code zip for the professor / team.

Includes every file Git would track (honours .gitignore, so .env, .venv, caches
and generated output are left out) and additionally drops image files and the
docs/screenshots folder. Output: dist/CareerPath_Guide_Group7_Source.zip

Usage:  python scripts/make_submission_zip.py
"""
from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "CareerPath_Guide_Group7_Source.zip"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"}
NEVER = {".env"}


def main() -> int:
    names = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    keep = []
    for n in sorted(set(names)):
        p = ROOT / n
        if not p.is_file() or p.name in NEVER or p.suffix.lower() in IMAGE_EXT:
            continue
        if n.startswith("docs/screenshots/") or n.startswith("dist/"):
            continue
        keep.append(n)
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for n in keep:
            z.write(ROOT / n, f"CareerPath_Guide/{n}")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(keep)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
