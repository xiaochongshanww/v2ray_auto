#!/usr/bin/env python3
"""Generate a monochrome tray template icon (macOS) using only the stdlib.

Writes desktop/assets/trayTemplate.png: 32x32 black "V" on transparent.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 32
OUT = Path(__file__).resolve().parents[1] / "assets" / "trayTemplate.png"

BLACK = (0, 0, 0, 255)
TRANSPARENT = (0, 0, 0, 0)


def point_in_poly(x: float, y: float, poly) -> bool:
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


BAR1 = [(11, 5), (15, 5), (22, 27), (18, 27)]
BAR2 = [(17, 5), (21, 5), (14, 27), (10, 27)]


def pixel(x: int, y: int) -> tuple:
    if point_in_poly(x + 0.5, y + 0.5, BAR1) or point_in_poly(x + 0.5, y + 0.5, BAR2):
        return BLACK
    return TRANSPARENT


def chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        for x in range(SIZE):
            raw.extend(pixel(x, y))
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    OUT.write_bytes(png)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
