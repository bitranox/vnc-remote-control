"""Tests for crosshair and grid drawing on a captured image."""

from __future__ import annotations

import pytest
from PIL import Image

from vnc_remote_control.adapters import rfb

#: Crosshair/box color the drawing code uses (magenta), kept here so the test
#: does not reach into the adapter's private module constants.
_MARK = (255, 0, 255)
#: Half-size of the hollow box the crosshair draws around the marked point.
_BOX_HALF = 6


def _blank(width: int, height: int) -> Image.Image:
    """Return an all-black RGB image."""
    return Image.new("RGB", (width, height), (0, 0, 0))


@pytest.mark.os_agnostic
def test_crosshair_marks_full_row_and_column() -> None:
    """A crosshair colors the whole row and column through the point."""
    w, h = 20, 16
    img = _blank(w, h)
    rfb.draw_crosshair(img, 10, 8)

    for x in range(w):
        assert img.getpixel((x, 8)) == _MARK
    for y in range(h):
        assert img.getpixel((10, y)) == _MARK


@pytest.mark.os_agnostic
def test_crosshair_leaves_other_pixels_untouched() -> None:
    """Pixels off the crosshair lines and box stay black."""
    w, h = 30, 30
    img = _blank(w, h)
    rfb.draw_crosshair(img, 15, 15)
    assert img.getpixel((0, 0)) == (0, 0, 0)


@pytest.mark.os_agnostic
def test_crosshair_box_corners_are_marked() -> None:
    """The hollow box edges around the point are drawn."""
    w, h = 40, 40
    img = _blank(w, h)
    cx, cy = 20, 20
    rfb.draw_crosshair(img, cx, cy)
    top = cy - _BOX_HALF
    left = cx - _BOX_HALF
    assert img.getpixel((left, top)) == _MARK


@pytest.mark.os_agnostic
def test_crosshair_ignores_out_of_bounds_point() -> None:
    """Marking a point outside the image does not raise and changes nothing."""
    w, h = 10, 10
    img = _blank(w, h)
    rfb.draw_crosshair(img, 100, 100)
    assert img.getpixel((0, 0)) == (0, 0, 0)
    assert img.getpixel((w - 1, h - 1)) == (0, 0, 0)


@pytest.mark.os_agnostic
def test_grid_marks_only_step_columns_and_rows() -> None:
    """Gridlines fall on multiples of the step, not between them."""
    w, h = 24, 24
    step = 8
    img = _blank(w, h)
    rfb.draw_grid(img, step)

    assert img.getpixel((8, 0)) != (0, 0, 0)
    assert img.getpixel((1, 0)) == (0, 0, 0)
    assert img.getpixel((0, 16)) != (0, 0, 0)
    assert img.getpixel((1, 3)) == (0, 0, 0)


@pytest.mark.os_agnostic
def test_grid_is_blended_not_opaque() -> None:
    """Gridlines are composited at half strength, not full gray."""
    img = _blank(16, 16)
    rfb.draw_grid(img, 8)
    # Over a black background, a half-strength medium-gray line lands near 64,
    # not the full 128, confirming the alpha blend rather than an opaque draw.
    pixel = img.getpixel((8, 0))
    assert isinstance(pixel, tuple)
    assert 0 < pixel[0] < 128


@pytest.mark.os_agnostic
def test_grid_zero_step_is_noop() -> None:
    """A non-positive step draws nothing."""
    img = _blank(10, 10)
    rfb.draw_grid(img, 0)
    assert img.getpixel((5, 5)) == (0, 0, 0)
