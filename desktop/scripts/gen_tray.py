#!/usr/bin/env python3
"""Generate macOS tray template icons from assets/tray.svg.

Writes desktop/assets/trayTemplate.png (32px) and
trayTemplate@2x.png (64px). The SVG is rendered at high resolution via
Electron/Chromium, then downsampled with LANCZOS so edges stay smooth
(no jaggies) in the menu bar, including Retina displays.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SRC = ASSETS / "tray.svg"
TMP = ASSETS / ".tray_template_raw.png"
OUT_1X = ASSETS / "trayTemplate.png"
OUT_2X = ASSETS / "trayTemplate@2x.png"
RENDER_SIZE = 256
SIZES = {32: OUT_1X, 64: OUT_2X}

ELECTRON = Path(__file__).resolve().parents[1] / "node_modules" / ".bin" / "electron"


def main() -> None:
    subprocess.run(
        [str(ELECTRON), str(Path(__file__).parent / "svg-to-png.js"), str(SRC), str(TMP), str(RENDER_SIZE)],
        check=True,
        cwd=str(ELECTRON.parents[1]),
    )
    with Image.open(TMP).convert("RGBA") as img:
        for size, out in SIZES.items():
            img.resize((size, size), Image.LANCZOS).save(out)
            print(f"wrote {out} ({size}x{size})")
    TMP.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
