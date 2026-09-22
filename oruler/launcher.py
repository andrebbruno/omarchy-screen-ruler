"""Starting the Quickshell overlay, and the environment it needs to come up.

Two things bite here and both are fixed once, in one place:

  * A Quickshell config needs a QML file path, and the file has to be the one this
    package shipped, wherever the package landed — /usr/share on Arch, inside the
    wheel for a pipx install.
  * Options reach QML through the environment rather than the command line: Quickshell
    passes no arguments through to a config, so a JSON blob in one variable is the
    honest way to hand over settings.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

ENV_OPTIONS = "OMARCHY_RULER_OPTIONS"
SHARE_DIRS = ("/usr/share/omarchy-screen-ruler/qml", "/usr/local/share/omarchy-screen-ruler/qml")


def qml_dir() -> str:
    """Where the shipped QML lives: inside the package, or in the system's share.

    Inside the package is what makes a pipx install work — the wheel carries the QML
    as package data, and there is no /usr/share to fall back on.
    """
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
    if os.path.isdir(local):
        return local
    for candidate in SHARE_DIRS:
        if os.path.isdir(candidate):
            return candidate
    return local


def qml_file(name: str) -> str:
    return os.path.join(qml_dir(), name)


def quickshell() -> str | None:
    return shutil.which("qs") or shutil.which("quickshell")


def environment(options: dict) -> dict[str, str]:
    env = dict(os.environ)
    env[ENV_OPTIONS] = json.dumps(options)
    env.setdefault("WAYLAND_DISPLAY", "wayland-1")
    return env


def build_command(path: str, binary: str | None = None) -> list[str]:
    return [binary or quickshell() or "qs", "-p", path]


def run(name: str, options: dict, wait: bool = True) -> int:
    """Launch an overlay. Returns its exit code, or 127 when Quickshell is missing."""
    binary = quickshell()
    if binary is None:
        print("omarchy-screen-ruler: quickshell is not installed (sudo pacman -S quickshell)",
              file=sys.stderr)
        return 127
    path = qml_file(name)
    if not os.path.exists(path):
        print(f"omarchy-screen-ruler: {path} is missing", file=sys.stderr)
        return 1
    command = build_command(path, binary)
    try:
        if wait:
            return subprocess.run(command, env=environment(options), check=False).returncode
        subprocess.Popen(command, env=environment(options),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    except (OSError, subprocess.SubprocessError) as e:
        print(f"omarchy-screen-ruler: {e}", file=sys.stderr)
        return 1


def already_running(namespace: str = "omarchy-screen-ruler") -> bool:
    """One overlay at a time: a second one would swallow the first one's keys."""
    try:
        r = subprocess.run(["hyprctl", "layers", "-j"], capture_output=True,
                           timeout=5, check=False)
        return namespace in r.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return False
