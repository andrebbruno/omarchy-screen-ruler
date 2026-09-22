"""Measuring: how far apart two points are, and how far a block of colour extends.

The second one is what makes a screen ruler worth having. PowerToys calls it Bounds:
you point at a button, a panel, a gap, and it works out where that thing starts and
ends by walking outwards until the colour changes. No window information, no toolkit
introspection — just pixels, which is why it works on anything on the screen.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .ppm import Image


@dataclass
class Box:
    left: int
    top: int
    right: int                     # inclusive
    bottom: int                    # inclusive

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1


def difference(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    """How different two colours are: the largest single-channel jump.

    The maximum rather than the sum, because an edge is usually one channel moving a
    long way (blue text on white) and averaging it across three hides it.
    """
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def _walk(image: Image, x: int, y: int, dx: int, dy: int,
          colour: tuple[int, int, int], tolerance: int, limit: int) -> int:
    """How many steps you can take from (x, y) before the colour changes."""
    steps = 0
    while steps < limit:
        nx, ny = x + dx * (steps + 1), y + dy * (steps + 1)
        if not (0 <= nx < image.width and 0 <= ny < image.height):
            break
        if difference(image.pixel(nx, ny), colour) > tolerance:
            break
        steps += 1
    return steps


def bounds_at(image: Image, x: int, y: int, tolerance: int = 12,
              limit: int = 4000) -> Box:
    """The extent of the colour under (x, y): left, right, up and down until it changes.

    `tolerance` is how much drift counts as the same colour — gradients and subpixel
    antialiasing mean an exact match stops one pixel in.
    """
    if not (0 <= x < image.width and 0 <= y < image.height):
        raise IndexError(f"({x}, {y}) is outside {image.width}×{image.height}")
    colour = image.pixel(x, y)
    left = x - _walk(image, x, y, -1, 0, colour, tolerance, limit)
    right = x + _walk(image, x, y, 1, 0, colour, tolerance, limit)
    top = y - _walk(image, x, y, 0, -1, colour, tolerance, limit)
    bottom = y + _walk(image, x, y, 0, 1, colour, tolerance, limit)
    return Box(left, top, right, bottom)


def distance(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.hypot(x2 - x1, y2 - y1)


# ---------------------------------------------------------------- real-world units

def millimetres(pixels: float, monitor: dict, axis: str = "x") -> float | None:
    """Pixels to millimetres, or None when the monitor will not say how big it is.

    A virtual or remote display reports 0×0mm, and inventing a DPI there would put a
    confident wrong number on the screen — so nothing is shown instead.
    """
    physical = monitor.get("physicalWidth" if axis == "x" else "physicalHeight") or 0
    resolution = monitor.get("width" if axis == "x" else "height") or 0
    if physical <= 0 or resolution <= 0:
        return None
    scale = monitor.get("scale") or 1
    # `pixels` is in layout coordinates; the panel's own pixels are `scale` times that.
    return pixels * scale * physical / resolution


def describe(pixels: float, monitor: dict | None, axis: str = "x") -> str:
    """"320 px · 8.5 cm", or just the pixels when the size is unknown."""
    text = f"{round(pixels)} px"
    if monitor is None:
        return text
    mm = millimetres(pixels, monitor, axis)
    if mm is None:
        return text
    if mm >= 10:
        return f"{text} · {mm / 10:.1f} cm"
    return f"{text} · {mm:.1f} mm"


def describe_box(box: Box, monitor: dict | None) -> str:
    """"986 × 27 px @2x · 20.6 × 0.6 cm".

    The pixels are the screen's own — the ones a designer means by "px" — which on a
    scaled display are not the coordinates anything is drawn in. Saying @2x is what
    stops the number looking twice as large as the box it came from.
    """
    text = f"{box.width} × {box.height} px"
    if not monitor:
        return text
    scale = monitor.get("scale") or 1
    if scale != 1:
        text += f" @{scale:g}x"
    if millimetres(1, monitor) is None:
        return text
    # The box is already in the monitor's own pixels, so undo the scale correction
    # that `millimetres` applies for layout coordinates.
    wide = millimetres(box.width / scale, monitor, "x")
    tall = millimetres(box.height / scale, monitor, "y")
    return f"{text} · {wide / 10:.1f} × {tall / 10:.1f} cm"
