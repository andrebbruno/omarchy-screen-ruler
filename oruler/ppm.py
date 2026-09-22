"""Reading the screen as pixels, without a single dependency.

`grim -t ppm` hands back a binary P6 file: a short text header and then three bytes
per pixel. That is the cheapest possible way to get the screen into Python — PNG would
mean zlib and a filter machine, or Pillow, for the sake of reading a few pixels.
"""
from __future__ import annotations

from dataclasses import dataclass


class PpmError(ValueError):
    pass


@dataclass
class Image:
    width: int
    height: int
    pixels: bytes                  # three bytes per pixel, row by row

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"({x}, {y}) is outside {self.width}×{self.height}")
        start = (y * self.width + x) * 3
        return tuple(self.pixels[start:start + 3])

    def __repr__(self) -> str:      # a whole screen is not a useful repr
        return f"Image({self.width}×{self.height})"


def _token(data: bytes, at: int) -> tuple[bytes, int]:
    """The next header token, skipping whitespace and # comments."""
    while at < len(data):
        if data[at:at + 1].isspace():
            at += 1
        elif data[at:at + 1] == b"#":
            while at < len(data) and data[at:at + 1] not in (b"\n", b"\r"):
                at += 1
        else:
            break
    start = at
    while at < len(data) and not data[at:at + 1].isspace():
        at += 1
    if start == at:
        raise PpmError("the header ended early")
    return data[start:at], at


def parse(data: bytes) -> Image:
    """A binary P6 image. Anything else is refused rather than half-read."""
    if not data.startswith(b"P6"):
        raise PpmError("not a binary PPM (P6)")
    at = 2
    width, at = _token(data, at)
    height, at = _token(data, at)
    maxval, at = _token(data, at)
    try:
        width, height, maxval = int(width), int(height), int(maxval)
    except ValueError as e:
        raise PpmError(f"unreadable header: {e}") from e
    if width <= 0 or height <= 0:
        raise PpmError(f"a {width}×{height} image is not an image")
    if maxval != 255:
        raise PpmError(f"only 8-bit PPMs are supported (this one says {maxval})")

    at += 1                        # exactly one whitespace byte after the header
    expected = width * height * 3
    pixels = data[at:at + expected]
    if len(pixels) < expected:
        raise PpmError(f"truncated: {len(pixels)} bytes of pixels, expected {expected}")
    return Image(width, height, pixels)


def build(width: int, height: int, pixels: bytes) -> bytes:
    """The other direction — used by the tests to make an image to read back."""
    return f"P6\n{width} {height}\n255\n".encode("ascii") + pixels
