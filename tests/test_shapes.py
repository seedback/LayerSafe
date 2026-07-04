"""Tests for the cutout shape registry (functions/shapes.py).

The registry itself is pure Python: importing it (and calling everything
except build()) must not require the CAD libraries.
"""
import math

import pytest

from shapes import (SHAPES, get_shape, parse_size, format_size,
                    CircleShape, SquareShape, HexShape, OvalShape)


def test_registry_contains_all_shapes():
  assert set(SHAPES) >= {'circle', 'square', 'hex', 'oval'}
  assert isinstance(SHAPES['circle'], CircleShape)
  assert isinstance(SHAPES['square'], SquareShape)
  assert isinstance(SHAPES['hex'], HexShape)
  assert isinstance(SHAPES['oval'], OvalShape)
  # Registry keys match the shapes' own names (used for --cutout-shape).
  for name, shape in SHAPES.items():
    assert shape.name == name


def test_parse_size():
  assert parse_size('31.6') == 31.6
  assert parse_size('60x35') == (60.0, 35.0)
  assert parse_size('60X35') == (60.0, 35.0)
  with pytest.raises(ValueError, match="WIDTHxDEPTH"):
    parse_size('60x35x2')
  with pytest.raises(ValueError, match="WIDTHxDEPTH"):
    parse_size('60x')
  with pytest.raises(ValueError):
    parse_size('big')


def test_format_size_roundtrip():
  assert format_size(31.6) == '31.6'
  assert format_size((60.0, 35.0)) == '60.0x35.0'


def test_validate_size():
  get_shape('circle').validate_size(31.6)          # no raise
  get_shape('oval').validate_size((60.0, 35.0))    # no raise
  with pytest.raises(ValueError, match="single size number"):
    get_shape('circle').validate_size((60.0, 35.0))
  with pytest.raises(ValueError, match="WIDTHxDEPTH"):
    get_shape('oval').validate_size(31.6)


def test_oval_footprint_and_layout_sizes():
  oval = get_shape('oval')
  assert oval.footprint((60.0, 35.0), 0.55) == pytest.approx((60.55, 35.55))
  assert oval.layout_sizes((60.0, 35.0), 0.55) == (60.0, 35.0)
  # Circumradius covers the long axis.
  assert oval.circumradius((60.0, 35.0), 0.55) == pytest.approx(30.275)


def test_get_shape_unknown_name_lists_available():
  with pytest.raises(ValueError, match="circle.*square|square.*circle"):
    get_shape('hexagon')


def test_circle_circumradius_and_footprint():
  circle = get_shape('circle')
  assert circle.circumradius(40.0, 0.55) == pytest.approx(20.275)
  assert circle.footprint(40.0, 0.55) == pytest.approx((40.55, 40.55))


def test_square_circumradius_is_half_diagonal():
  square = get_shape('square')
  assert square.circumradius(40.0, 0.55) == pytest.approx(
      40.55 * math.sqrt(2) / 2)
  assert square.footprint(40.0, 0.55) == pytest.approx((40.55, 40.55))


def test_min_center_distance_circle_circle_matches_layout_math():
  # Must equal the alternating layout's nesting distance: the toleranced
  # radii sum plus the clearance gap.
  circle = get_shape('circle')
  d = circle.min_center_distance(24.7, circle, 49.6, 0.55, gap=0.4)
  assert d == pytest.approx((24.7 + 0.55) / 2 + (49.6 + 0.55) / 2 + 0.4)


def test_min_center_distance_squares_is_conservative():
  # Two 40mm squares corner-to-corner need more room than two 40mm
  # circles: the default circumscribed-circle math must reflect that.
  circle = get_shape('circle')
  square = get_shape('square')
  assert (square.min_center_distance(40.0, square, 40.0, 0.55)
          > circle.min_center_distance(40.0, circle, 40.0, 0.55))


def test_nesting_styles():
  # Circles use exact tangency; every other shape uses conservative
  # bounding-box spacing in the alternating layout.
  assert get_shape('circle').nesting == 'circle'
  assert get_shape('square').nesting == 'box'
  assert get_shape('hex').nesting == 'box'
  assert get_shape('oval').nesting == 'box'


def test_hex_footprint_is_wider_across_corners():
  # size is measured across the flats (y); the corners point along x and
  # stick out by a factor of 2/sqrt(3).
  hex_shape = get_shape('hex')
  fx, fy = hex_shape.footprint(25.0, 0.55)
  assert fy == pytest.approx(25.55)
  assert fx == pytest.approx(25.55 * 2 / math.sqrt(3))
  assert hex_shape.circumradius(25.0, 0.55) == pytest.approx(
      25.55 / math.sqrt(3))


def test_layout_sizes_default_and_hex():
  # Circle and square lay out as size x size...
  assert get_shape('circle').layout_sizes(40.0, 0.55) == pytest.approx(
      (40.0, 40.0))
  assert get_shape('square').layout_sizes(40.0, 0.55) == pytest.approx(
      (40.0, 40.0))
  # ...but a hex must reserve its across-corners width along x, so that
  # layout_size + tolerance equals the physical footprint per axis.
  hx, hy = get_shape('hex').layout_sizes(25.0, 0.55)
  assert hy == pytest.approx(25.0)
  assert hx == pytest.approx(25.55 * 2 / math.sqrt(3) - 0.55)
