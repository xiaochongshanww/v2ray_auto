#!/usr/bin/env python3
"""Generate icon.icns (macOS) and icon.ico (Windows) from assets/icon.png.

Requires Pillow (present in desktop/runtime). Run after svg-to-png.js so
icon.png reflects the current assets/icon.svg design.
"""

from __future__ import annotations

import struct
import subprocess
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SRC = ASSETS / "icon.png"
ICNS = ASSETS / "icon.icns"
ICO = ASSETS / "icon.ico"

MAC_SIZES = [16, 32, 128, 256, 512]
WIN_SIZES = [16, 32, 48, 256]


def make_icns() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        with Image.open(SRC) as base:
            for s in MAC_SIZES:
                img = base.resize((s, s), Image.LANCZOS)
                img.save(iconset / f"icon_{s}x{s}.png")
                d = s * 2
                img2 = base.resize((d, d), Image.LANCZOS)
                img2.save(iconset / f"icon_{s}x{s}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS)], check=True)
    print(f"wrote {ICNS} ({ICNS.stat().st_size} bytes)")


def make_ico() -> None:
    images = []
    with Image.open(SRC) as base:
        for s in WIN_SIZES:
            images.append(base.resize((s, s), Image.LANCZOS))

    def byte_for(size: int) -> int:
        return 0 if size >= 256 else size

    with open(ICO, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(images)))
        offset = 6 + 16 * len(images)
        entries = []
        for img in images:
            buf = img.tobytes()
            import io

            png_buf = io.BytesIO()
            img.save(png_buf, format="PNG")
            data = png_buf.getvalue()
            entries.append((byte_for(img.width), byte_for(img.height), data, offset))
            offset += len(data)
        for w, h, data, off in entries:
            f.write(struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), off))
        for _, _, data, _ in entries:
            f.write(data)
    print(f"wrote {ICO} ({ICO.stat().st_size} bytes)")


def main() -> None:
    make_icns()
    make_ico()


if __name__ == "__main__":
    main()
