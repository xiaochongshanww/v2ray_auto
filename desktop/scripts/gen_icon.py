#!/usr/bin/env python3
"""Generate a simple 1024x1024 app icon (PNG) using only the stdlib.

Writes desktop/assets/icon.png: dark rounded square with a green "V".
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 1024
RADIUS = 200
OUT = Path(__file__).resolve().parents[1] / "assets" / "icon.png"

BG = (26, 26, 46, 255)
GREEN = (46, 204, 113, 255)


def rounded_cover(x: int, y: int) -> bool:
    cx = min(max(x, RADIUS), SIZE - 1 - RADIUS)
    cy = min(max(y, RADIUS), SIZE - 1 - RADIUS)
    dx, dy = x - cx, y - cy
    return dx * dx + dy * dy <= RADIUS * RADIUS


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


BAR1 = [(370, 210), (452, 210), (620, 814), (538, 814)]
BAR2 = [(574, 210), (656, 210), (486, 814), (404, 814)]


def pixel(x: int, y: int) -> tuple:
    if not rounded_cover(x, y):
        return (0, 0, 0, 0)
    if point_in_poly(x + 0.5, y + 0.5, BAR1) or point_in_poly(x + 0.5, y + 0.5, BAR2):
        return GREEN
    return BG


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
