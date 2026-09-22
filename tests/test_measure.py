import pytest

from oruler.measure import Box, bounds_at, describe, difference, distance, millimetres
from oruler.ppm import Image, PpmError, build, parse

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (60, 130, 240)


def image(width, height, fill=WHITE):
    return Image(width, height, bytes(fill) * (width * height))


def paint(img, box, colour):
    """A filled rectangle, so the tests can build a screen to measure."""
    pixels = bytearray(img.pixels)
    for y in range(box[1], box[3] + 1):
        for x in range(box[0], box[2] + 1):
            start = (y * img.width + x) * 3
            pixels[start:start + 3] = bytes(colour)
    return Image(img.width, img.height, bytes(pixels))


# ---------------------------------------------------------------- PPM

def test_a_ppm_round_trips():
    data = build(2, 1, bytes(BLACK) + bytes(WHITE))
    img = parse(data)
    assert (img.width, img.height) == (2, 1)
    assert img.pixel(0, 0) == BLACK
    assert img.pixel(1, 0) == WHITE


def test_the_header_may_have_comments_and_odd_spacing():
    data = b"P6\n# written by grim\n  3 2\n255\n" + bytes(WHITE) * 6
    assert parse(data).width == 3


def test_a_pixel_outside_the_image_is_an_error():
    with pytest.raises(IndexError):
        image(2, 2).pixel(5, 0)


def test_anything_that_is_not_a_p6_is_refused():
    for bad in (b"", b"P3\n1 1\n255\n255 255 255", b"not an image"):
        with pytest.raises(PpmError):
            parse(bad)


def test_a_sixteen_bit_ppm_is_refused_rather_than_misread():
    with pytest.raises(PpmError):
        parse(b"P6\n1 1\n65535\n\x00\x00\x00\x00\x00\x00")


def test_a_truncated_image_is_refused():
    with pytest.raises(PpmError):
        parse(build(10, 10, bytes(WHITE) * 5))


def test_a_zero_sized_image_is_refused():
    with pytest.raises(PpmError):
        parse(b"P6\n0 0\n255\n")


# ---------------------------------------------------------------- colour distance

def test_the_difference_is_the_biggest_channel_jump():
    assert difference(WHITE, BLACK) == 255
    assert difference((10, 10, 10), (10, 10, 40)) == 30
    assert difference(BLUE, BLUE) == 0


# ---------------------------------------------------------------- bounds

def test_a_block_of_colour_is_measured():
    img = paint(image(40, 30), (10, 5, 19, 14), BLUE)
    box = bounds_at(img, 12, 8)
    assert (box.left, box.top, box.right, box.bottom) == (10, 5, 19, 14)
    assert (box.width, box.height) == (10, 10)


def test_the_gap_beside_a_block_is_measured_too():
    """Measuring the space *around* something is half of what a ruler is for."""
    img = paint(image(40, 30), (10, 5, 19, 14), BLUE)
    box = bounds_at(img, 2, 8)                 # a row that crosses the block
    assert box.left == 0
    assert box.right == 9                      # stops where the block starts
    assert box.top == 0 and box.bottom == 29   # nothing above or below at x=2


def test_a_block_touching_the_edge_stops_at_the_edge():
    img = paint(image(20, 20), (0, 0, 4, 4), BLACK)
    box = bounds_at(img, 2, 2)
    assert (box.left, box.top, box.right, box.bottom) == (0, 0, 4, 4)


def test_a_single_pixel():
    img = paint(image(10, 10), (5, 5, 5, 5), BLACK)
    box = bounds_at(img, 5, 5)
    assert (box.width, box.height) == (1, 1)


def test_tolerance_lets_a_gradient_count_as_one_colour():
    """Antialiasing and gradients mean an exact match stops one pixel in."""
    pixels = bytearray()
    for x in range(20):
        shade = 200 + (x // 4)                 # drifts by 5 across the row
        pixels += bytes((shade, shade, shade))
    img = Image(20, 1, bytes(pixels))
    assert bounds_at(img, 10, 0, tolerance=0).width < 5
    assert bounds_at(img, 10, 0, tolerance=10).width == 20


def test_the_walk_is_bounded():
    """A whole-screen sweep of one colour should not take forever."""
    img = image(500, 1, WHITE)
    box = bounds_at(img, 250, 0, limit=10)
    assert box.width == 21                     # ten either side, plus the pixel itself


def test_pointing_outside_the_image_is_an_error():
    with pytest.raises(IndexError):
        bounds_at(image(10, 10), 50, 50)


# ---------------------------------------------------------------- distance and units

def test_distance():
    assert distance(0, 0, 3, 4) == 5.0
    assert distance(10, 10, 10, 10) == 0.0


MONITOR = {"width": 2560, "height": 1440, "scale": 1,
           "physicalWidth": 600, "physicalHeight": 340}


def test_pixels_to_millimetres():
    assert round(millimetres(2560, MONITOR), 1) == 600.0
    assert round(millimetres(1280, MONITOR), 1) == 300.0


def test_scaling_is_taken_into_account():
    """A 2× display: 100 layout pixels are 200 real ones."""
    scaled = {**MONITOR, "scale": 2}
    assert round(millimetres(100, scaled), 2) == round(millimetres(200, MONITOR), 2)


def test_the_vertical_axis_uses_the_vertical_size():
    assert round(millimetres(1440, MONITOR, "y"), 1) == 340.0


def test_a_monitor_that_will_not_say_how_big_it_is():
    """A virtual or remote display reports 0×0mm; inventing a DPI would be a lie."""
    assert millimetres(100, {**MONITOR, "physicalWidth": 0}) is None
    assert millimetres(100, {}) is None


def test_describing_a_measurement():
    assert describe(1280, MONITOR) == "1280 px · 30.0 cm"
    assert describe(20, MONITOR) == "20 px · 4.7 mm"


def test_describing_without_a_physical_size():
    assert describe(1280, {"width": 2560, "height": 1440}) == "1280 px"
    assert describe(1280, None) == "1280 px"


def test_describing_a_box():
    from oruler.measure import describe_box
    box = Box(0, 0, 999, 99)                   # 1000 × 100 of the monitor's own pixels
    assert describe_box(box, MONITOR) == "1000 × 100 px · 23.4 × 2.4 cm"


def test_a_box_on_a_scaled_display_says_so():
    """The pixels are the screen's; the box is drawn in layout coordinates. Without
    the @2x the number looks twice as big as the rectangle it came from."""
    from oruler.measure import describe_box
    scaled = {**MONITOR, "scale": 2}
    assert describe_box(Box(0, 0, 999, 99), scaled).startswith("1000 × 100 px @2x")


def test_a_box_without_a_physical_size():
    from oruler.measure import describe_box
    assert describe_box(Box(0, 0, 9, 9), {"width": 100, "height": 100, "scale": 1}) \
        == "10 × 10 px"
    assert describe_box(Box(0, 0, 9, 9), None) == "10 × 10 px"
