# Screen Ruler for Omarchy

Measure anything on the screen. A port of
[PowerToys Screen Ruler](https://learn.microsoft.com/windows/powertoys/screen-ruler) to
[Omarchy](https://omarchy.org).

*[Leia em português](README.pt-BR.md)*

```bash
omarchy-screen-ruler            # drag to measure; click to measure what is under you
omarchy-screen-ruler bounds 320 240
omarchy-screen-ruler measure 100 100 500 400
```

- **Drag** for a distance: a box with guide lines out to the edges of the screen and a
  live readout that follows the pointer.
- **Click** for *bounds*: the extent of whatever is under the pointer — a button, a
  panel, the gap between two things — worked out from the pixels themselves.
- **Right click** clears the box, **Ctrl+C** copies the measurement, **Escape** leaves.

Measurements are in the screen's own pixels, and in centimetres when the monitor says
how big it is.

## How bounds works

The screen is captured the moment the ruler opens — before the overlay covers it — and
the measurement walks outwards from the point you clicked until the colour changes by
more than a tolerance. No window information, no toolkit introspection: it works on
anything that is on the screen, including a video, a screenshot or another machine over
VNC.

The capture is `grim -t ppm`, a binary header and three bytes per pixel, which Python
reads with no dependency at all. PNG would have meant zlib and a filter machine, or
Pillow, to read a few pixels.

## ⚠️ Pixels, scale, and what "px" means

On a display at scale 2, a 100-pixel drag covers 200 of the screen's own pixels. The
readout gives you the screen's — the ones a designer means by "px" — and marks them
`@2x` so the number never looks twice as large as the box it came from.

A virtual or remote display reports its physical size as 0×0mm. Rather than invent a
DPI and put a confident wrong centimetre figure on the screen, the ruler just leaves
it out.

## Install

### Arch / Omarchy

```bash
sudo pacman -U omarchy-screen-ruler-*-any.pkg.tar.zst   # from Releases
omarchy-screen-ruler setup
```

In `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + R", "Screen ruler", "omarchy-screen-ruler")
```

Settings in `~/.config/omarchy-screen-ruler/config.json`:

```json
{ "colour": "", "tolerance": 12, "thickness": 2 }
```

`tolerance` is how much colour drift still counts as the same region — raise it for
gradients, lower it to pick out antialiased edges.

### Elsewhere

`pipx install git+https://github.com/andrebbruno/omarchy-screen-ruler`, with
`quickshell` and `grim`.

## Commands

```
omarchy-screen-ruler                     the ruler
omarchy-screen-ruler bounds <x> <y>      the extent of the colour there  (--json)
omarchy-screen-ruler measure <x1> <y1> <x2> <y2>
omarchy-screen-ruler status              the pointer, the monitor and its real size
```

`bounds` and `measure` are what the overlay itself calls, so anything else can call
them too.

## Development

```bash
python -m pytest tests -q     # 42 tests, no screen needed
```

The PPM reader and the measuring are pure functions over a pixel buffer, so the tests
build little screens — a blue block on white — and check the bounds, the tolerance,
the edges, the scaling and the unit conversion exactly. The overlay was then driven on
a real desktop: a drag measured, and a click on a panel found its edges.

## License

MIT © Andre Bruno
