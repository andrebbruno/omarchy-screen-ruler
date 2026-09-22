import json

import pytest

from oruler import cli, measure
from oruler.ppm import build

WHITE = bytes((255, 255, 255))
BLUE = bytes((60, 130, 240))


def screen(tmp_path, width=40, height=30, block=(10, 5, 19, 14)):
    """A little screen with one blue block in it, written as a PPM."""
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            inside = block[0] <= x <= block[2] and block[1] <= y <= block[3]
            pixels += BLUE if inside else WHITE
    path = tmp_path / "screen.ppm"
    path.write_bytes(build(width, height, bytes(pixels)))
    return str(path)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr(cli, "FRAME", screen(tmp_path))
    monkeypatch.setattr(cli, "accent", lambda: "#7aa2f7")
    monkeypatch.setattr(cli.menu, "notify", lambda *a, **k: None)
    monkeypatch.setattr(cli, "monitor_for", lambda x, y: None)
    return tmp_path


def out(capsys):
    return capsys.readouterr().out.strip()


# ---------------------------------------------------------------- bounds

def test_bounds_finds_the_block(home, capsys):
    assert cli.main(["bounds", "12", "8", "--json"]) == 0
    found = json.loads(out(capsys))
    assert (found["left"], found["top"]) == (10, 5)
    assert (found["width"], found["height"]) == (10, 10)


def test_bounds_in_plain_words(home, capsys):
    assert cli.main(["bounds", "12", "8"]) == 0
    assert out(capsys) == "10 × 10 px at 10, 5"


def test_bounds_needs_two_numbers(home, capsys):
    assert cli.main(["bounds"]) == 2
    assert cli.main(["bounds", "12"]) == 2
    assert cli.main(["bounds", "here", "there"]) == 2


def test_bounds_outside_the_screen_is_reported(home, capsys):
    assert cli.main(["bounds", "500", "500"]) == 1
    assert "outside" in capsys.readouterr().err


def test_bounds_without_a_capture_is_reported(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "FRAME", str(home / "nothing.ppm"))
    assert cli.main(["bounds", "1", "1"]) == 1
    assert "no screen capture" in capsys.readouterr().err


# ---------------------------------------------------------------- measure

def test_measure_gives_width_and_height(home, capsys):
    assert cli.main(["measure", "10", "10", "110", "60", "--json"]) == 0
    found = json.loads(out(capsys))
    assert found["width"] == 100 and found["height"] == 50
    assert found["diagonal"] == pytest.approx(111.8, abs=0.1)


def test_measure_works_backwards_too(home, capsys):
    cli.main(["measure", "110", "60", "10", "10", "--json"])
    found = json.loads(out(capsys))
    assert found["width"] == 100 and found["height"] == 50


def test_measure_in_plain_words(home, capsys):
    assert cli.main(["measure", "0", "0", "100", "50"]) == 0
    assert out(capsys) == "100 × 50 px"


def test_measure_reports_the_screens_own_pixels(home, monkeypatch, capsys):
    """A 100-pixel drag on a 2x display covers 200 real pixels, and says so."""
    monkeypatch.setattr(cli, "monitor_for", lambda x, y: {**MONITOR, "scale": 2})
    cli.main(["measure", "0", "0", "100", "50"])
    assert out(capsys).startswith("200 × 100 px @2x")


def test_measure_needs_four_numbers(home, capsys):
    assert cli.main(["measure", "1", "2", "3"]) == 2


# ---------------------------------------------------------------- with a monitor

MONITOR = {"name": "DP-1", "x": 0, "y": 0, "width": 2560, "height": 1440, "scale": 1,
           "physicalWidth": 600, "physicalHeight": 340}


def test_centimetres_appear_when_the_monitor_says_how_big_it_is(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "monitor_for", lambda x, y: MONITOR)
    cli.main(["measure", "0", "0", "1280", "720"])
    assert "cm" in out(capsys)


def test_a_scaled_monitor_maps_to_the_captured_pixels(home, monkeypatch, capsys):
    """grim captures a 2× monitor at its real resolution, not its layout size."""
    monkeypatch.setattr(cli, "monitor_for", lambda x, y: {**MONITOR, "scale": 2})
    assert cli.to_pixels(100, 50, {**MONITOR, "scale": 2}) == (200, 100)


def test_a_second_monitor_is_offset(home):
    second = {**MONITOR, "name": "HDMI-A-1", "x": 2560, "scale": 1}
    assert cli.to_pixels(2600, 10, second) == (2600, 10)


def test_no_monitor_means_coordinates_are_taken_as_they_are(home):
    assert cli.to_pixels(42, 24, None) == (42, 24)


# ---------------------------------------------------------------- the rest

def test_an_unknown_command(home, capsys):
    assert cli.main(["frobnicate"]) == 2


def test_status_runs(home, monkeypatch, capsys):
    monkeypatch.setattr(cli.launcher, "quickshell", lambda: "/usr/bin/qs")

    class FakeHyprland:
        def cursor(self):
            return (100, 100)
    monkeypatch.setattr(cli, "Hyprland", lambda *a, **k: FakeHyprland())
    monkeypatch.setattr(cli, "monitor_for", lambda x, y: MONITOR)
    assert cli.main(["status"]) == 0
    printed = out(capsys)
    assert "DP-1" in printed and "cm wide" in printed


def test_a_failed_capture_is_reported(home, monkeypatch, capsys):
    def boom(path=None):
        raise RuntimeError("grim failed: no outputs")
    monkeypatch.setattr(cli, "grab", boom)
    assert cli.main(["show"]) == 1
    assert "grim failed" in capsys.readouterr().err
