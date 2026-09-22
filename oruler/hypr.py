"""Hyprland's IPC socket, spoken directly.

`hyprctl cursorpos` costs about 25 ms — a process spawn, a connection and a parse. The
same question asked straight down the socket costs 0.16 ms, and a spotlight that
follows the pointer has to ask sixty times a second. That difference is the whole
reason this file exists rather than a subprocess call.
"""
from __future__ import annotations

import json
import os
import socket

SOCKET_NAME = ".socket.sock"


class HyprlandError(Exception):
    pass


def socket_path(runtime: str | None = None, signature: str | None = None) -> str:
    """$XDG_RUNTIME_DIR/hypr/<instance>/.socket.sock, working out the instance if needed."""
    runtime = runtime or os.environ.get("XDG_RUNTIME_DIR") or "/run/user/1000"
    signature = signature or os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    base = os.path.join(runtime, "hypr")
    if not signature:
        try:
            instances = sorted(os.listdir(base))
        except OSError as e:
            raise HyprlandError(f"no Hyprland instance in {base}: {e}") from e
        if not instances:
            raise HyprlandError(f"no Hyprland instance in {base}")
        signature = instances[0]
    path = os.path.join(base, signature, SOCKET_NAME)
    if not os.path.exists(path):
        raise HyprlandError(f"{path} does not exist — is Hyprland running?")
    return path


def parse_position(text: str) -> tuple[int, int]:
    """"488, 274" -> (488, 274). Anything else is not a position."""
    parts = [p.strip() for p in (text or "").strip().split(",")]
    if len(parts) != 2:
        raise HyprlandError(f"{text!r} is not a cursor position")
    try:
        return int(float(parts[0])), int(float(parts[1]))
    except ValueError as e:
        raise HyprlandError(f"{text!r} is not a cursor position") from e


class Hyprland:
    """One question, one connection — which is how Hyprland's IPC works."""

    def __init__(self, path: str | None = None):
        self._path = path

    @property
    def path(self) -> str:
        if self._path is None:
            self._path = socket_path()
        return self._path

    def ask(self, command: str) -> str:
        try:
            with socket.socket(socket.AF_UNIX) as s:
                s.settimeout(2.0)
                s.connect(self.path)
                s.sendall(command.encode("utf-8"))
                chunks = []
                while True:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
        except OSError as e:
            raise HyprlandError(f"talking to Hyprland: {e}") from e
        return b"".join(chunks).decode("utf-8", "replace").strip()

    def cursor(self) -> tuple[int, int]:
        return parse_position(self.ask("cursorpos"))

    def monitors(self) -> list[dict]:
        try:
            return json.loads(self.ask("j/monitors"))
        except ValueError as e:
            raise HyprlandError(f"unreadable monitor list: {e}") from e

    def monitor_at(self, x: int, y: int) -> dict | None:
        """Which monitor a point is on — the cursor is in layout coordinates."""
        for monitor in self.monitors():
            left, top = monitor.get("x", 0), monitor.get("y", 0)
            scale = monitor.get("scale", 1) or 1
            width = monitor.get("width", 0) / scale
            height = monitor.get("height", 0) / scale
            if left <= x < left + width and top <= y < top + height:
                return monitor
        return None
