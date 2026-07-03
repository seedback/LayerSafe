"""Tests for the cutout shape registry (functions/shapes.py).

The registry itself is pure Python: importing it (and calling everything
except build()) must not require the CAD libraries.
"""
import math

import pytest

from shapes import SHAPES, get_shape, CircleShape, SquareShape, HexShape


def test_registry_contains_all_shapes():
  assert set(SHAPES) >= {'circle', 'square', 'hex'}
  assert isinstance(SHAPES['circle'], CircleShape)
  assert isinstance(SHAPES['square'], SquareShape)
  assert isinstance(SHAPES['hex'], HexShape)
  # Registry keys match the shapes' own names (used for --cutout-shape).
  for name, shape in SHAPES.items():
    assert shape.name == name


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


def test_alternating_layout_support_flags():
  assert get_shape('circle').supports_alternating is True
  # Squares and hexes must stay on the linear layout: circle-tangency
  # nesting underestimates their corner footprint.
  assert get_shape('square').supports_alternating is False
  assert get_shape('hex').supports_alternating is False


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
