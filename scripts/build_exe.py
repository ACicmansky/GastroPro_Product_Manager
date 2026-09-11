"""Build script to produce a standalone Windows executable of GastroPro via PyInstaller."""

import sys
from pathlib import Path
import PyInstaller.__main__


def build():
    root_dir = Path(__file__).resolve().parents[1]
    spec_file = root_dir / "gastropro.spec"

    print(f"[build] Building GastroPro executable using {spec_file.name}...")

    args = [
        str(spec_file),
        "--noconfirm",
        "--clean",
        f"--distpath={root_dir / 'dist'}",
        f"--workpath={root_dir / 'build'}",
    ]

    try:
        PyInstaller.__main__.run(args)
        dist_exe = root_dir / "dist" / "GastroPro" / "GastroPro.exe"
        if dist_exe.exists():
            print(f"\n[build] SUCCESS: Binary created at {dist_exe}")
            return 0
        else:
            print(f"\n[build] WARNING: Build finished but {dist_exe} was not found.")
            return 1
    except Exception as e:
        print(f"\n[build] ERROR: Build failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(build())
