"""omarchy-screen-ruler — measure anything on the screen, in pixels or in centimetres.

    omarchy-screen-ruler              drag to measure; click to measure what is under you
    omarchy-screen-ruler bounds X Y   the extent of the colour at that point
    omarchy-screen-ruler measure X1 Y1 X2 Y2
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from . import __version__, launcher, measure, menu, ppm
from .hypr import Hyprland, HyprlandError

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                          "omarchy-screen-ruler")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATE_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "omarchy-screen-ruler")
FRAME = os.path.join(STATE_DIR, "screen.ppm")

DEFAULTS = {"colour": "", "tolerance": 12, "thickness": 2}
ICONS = {"ruler": "", "bounds": "", "copy": ""}


def config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def accent() -> str:
    chosen = config().get("colour") or ""
    if chosen:
        return chosen
    try:
        r = subprocess.run(["omarchy-theme-color", "accent"], capture_output=True,
                           timeout=10, check=False)
        value = r.stdout.decode("utf-8", "replace").strip()
    except (OSError, subprocess.SubprocessError):
        value = ""
    return value if value.startswith("#") else "#ff5555"


# ---------------------------------------------------------------- the screen

def grab(path: str | None = None) -> str:
    """The screen as pixels, before the overlay covers it.

    PPM rather than PNG because grim can write it and Python can read it with no
    dependency at all — see oruler/ppm.py.
    """
    # Looked up at call time, not bound as a default: the path is configuration, and
    # a default argument freezes whatever it was when this module was imported.
    path = path or FRAME
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "wb") as f:
            r = subprocess.run(["grim", "-t", "ppm", "-"], stdout=f,
                               stderr=subprocess.PIPE, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"grim: {e}") from e
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip() or "grim failed")
    return path


def frame(path: str | None = None) -> ppm.Image:
    path = path or FRAME
    try:
        with open(path, "rb") as f:
            return ppm.parse(f.read())
    except OSError as e:
        raise RuntimeError(f"no screen capture to measure ({e})") from e


def monitor_for(x: int, y: int) -> dict | None:
    try:
        return Hyprland().monitor_at(x, y)
    except HyprlandError:
        return None


def to_pixels(x: int, y: int, monitor: dict | None) -> tuple[int, int]:
    """Layout coordinates to coordinates in the captured image.

    grim captures every output at its own resolution, side by side in layout order,
    so a scaled monitor's pixels are `scale` times its layout coordinates.
    """
    if not monitor:
        return x, y
    scale = monitor.get("scale") or 1
    left, top = monitor.get("x", 0), monitor.get("y", 0)
    return int((x - left) * scale + left * scale), int((y - top) * scale + top * scale)


# ---------------------------------------------------------------- commands

def cmd_bounds(args) -> int:
    if args.a is None or args.b is None:
        print("Usage: omarchy-screen-ruler bounds <x> <y>", file=sys.stderr)
        return 2
    try:
        x, y = int(args.a), int(args.b)
    except ValueError:
        print("omarchy-screen-ruler: x and y have to be numbers", file=sys.stderr)
        return 2
    try:
        image = frame()
    except RuntimeError as e:
        print(f"omarchy-screen-ruler: {e}", file=sys.stderr)
        return 1
    monitor = monitor_for(x, y)
    px, py = to_pixels(x, y, monitor)
    try:
        box = measure.bounds_at(image, px, py, tolerance=int(config()["tolerance"]))
    except IndexError as e:
        print(f"omarchy-screen-ruler: {e}", file=sys.stderr)
        return 1
    scale = (monitor.get("scale") or 1) if monitor else 1
    # Back to layout coordinates, which is what the overlay draws in.
    payload = {"left": round(box.left / scale), "top": round(box.top / scale),
               "width": round(box.width / scale), "height": round(box.height / scale),
               "label": measure.describe_box(box, monitor)}
    print(json.dumps(payload) if args.json else
          f"{payload['width']} × {payload['height']} px at "
          f"{payload['left']}, {payload['top']}")
    return 0


def cmd_measure(args) -> int:
    values = [args.a, args.b, args.c, args.d]
    if any(v is None for v in values):
        print("Usage: omarchy-screen-ruler measure <x1> <y1> <x2> <y2>", file=sys.stderr)
        return 2
    try:
        x1, y1, x2, y2 = [int(v) for v in values]
    except ValueError:
        print("omarchy-screen-ruler: the coordinates have to be numbers", file=sys.stderr)
        return 2
    monitor = monitor_for(x1, y1)
    # The overlay drags in layout coordinates; "px" means the screen's own pixels, and
    # on a scaled display those are not the same number. `bounds` reports the screen's,
    # so this does too — with the same @2x marker to say which is which.
    scale = (monitor.get("scale") or 1) if monitor else 1
    width, height = abs(x2 - x1), abs(y2 - y1)
    box = measure.Box(0, 0, round(width * scale) - 1, round(height * scale) - 1)
    payload = {
        "width": width, "height": height,
        "diagonal": round(measure.distance(x1, y1, x2, y2), 1),
        "label": measure.describe_box(box, monitor),
    }
    print(json.dumps(payload) if args.json else payload["label"])
    return 0


def cmd_show(args) -> int:
    try:
        grab()
    except RuntimeError as e:
        print(f"omarchy-screen-ruler: {e}", file=sys.stderr)
        menu.notify("Screen ruler", str(e))
        return 1
    settings = config()
    options = {"accent": accent(), "thickness": int(settings["thickness"])}
    return launcher.run("Ruler.qml", options)


def cmd_status(args) -> int:
    print(f"quickshell     {launcher.quickshell() or 'NOT FOUND'}")
    print(f"colour         {accent()}")
    try:
        x, y = Hyprland().cursor()
        monitor = monitor_for(x, y)
        print(f"pointer        {x}, {y}")
        if monitor:
            physical = measure.millimetres(monitor.get("width", 0), monitor)
            print(f"monitor        {monitor['name']} "
                  f"{monitor.get('width')}×{monitor.get('height')} "
                  f"at scale {monitor.get('scale')}")
            print(f"physical size  "
                  f"{f'{physical / 10:.1f} cm wide' if physical else 'not reported'}")
    except HyprlandError as e:
        print(f"pointer        unavailable ({e})")
    return 0


def cmd_menu(args) -> int:
    rows = [(ICONS["ruler"], "Measure the screen", "Drag to measure, click for bounds")]
    pick = menu.select("Screen ruler", rows, width=560)
    if not pick:
        return 1
    return cmd_show(args)


def cmd_setup(args) -> int:
    print("Add this to ~/.config/hypr/bindings.lua:\n")
    print('  o.bind("SUPER + SHIFT + R", "Screen ruler", "omarchy-screen-ruler")\n')
    missing = [name for name in ("grim", "qs") if not launcher.shutil.which(name)]
    if missing:
        print(f"Missing: {', '.join(missing)}")
        return 1
    print("Everything it needs is installed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="omarchy-screen-ruler",
        description="Measure anything on the screen, in pixels or in centimetres.",
        epilog="With no command the ruler opens; Escape closes it.")
    p.add_argument("command", nargs="?", help="show, bounds, measure, status, setup, menu")
    p.add_argument("a", nargs="?")
    p.add_argument("b", nargs="?")
    p.add_argument("c", nargs="?")
    p.add_argument("d", nargs="?")
    p.add_argument("-j", "--json", action="store_true", help="machine-readable output")
    p.add_argument("-V", "--version", action="version",
                   version=f"omarchy-screen-ruler {__version__}")
    args = p.parse_args(argv)

    commands = {"show": cmd_show, "bounds": cmd_bounds, "measure": cmd_measure,
                "status": cmd_status, "setup": cmd_setup, "menu": cmd_menu}
    if args.command is None:
        return cmd_show(args)
    if args.command not in commands:
        print(f"omarchy-screen-ruler: unknown command {args.command!r}", file=sys.stderr)
        return 2
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
