"""Tests for cutout boolean-result handling (functions/cutout_generator.py).

Unlike the layout tests these need the CAD stack (build123d), but they only
build one small cutout so they stay fast.
"""
from build123d import Compound, ShapeList, Solid

from cutout_generator import _unwrap_boolean_result, generate_cutout


def test_unwrap_dimensionless_compound():
  # Boolean ops can return a plain Compound whose class-level _dim is
  # None, which cannot be fused with `+`.
  box = Solid.make_box(1, 1, 1)
  result = _unwrap_boolean_result(Compound([box]))
  assert result is not None
  assert type(result)._dim == 3


def test_unwrap_shapelist():
  box = Solid.make_box(1, 1, 1)
  result = _unwrap_boolean_result(ShapeList([box]))
  assert result is not None
  assert type(result)._dim == 3


def test_unwrap_empty_returns_none():
  assert _unwrap_boolean_result(None) is None
  assert _unwrap_boolean_result(ShapeList()) is None


def test_unwrap_keeps_all_solids():
  a = Solid.make_box(1, 1, 1)
  b = Solid.make_box(1, 1, 1).translate((2, 0, 0))
  result = _unwrap_boolean_result(Compound([a, b]))
  assert result is not None
  assert type(result)._dim == 3
  assert abs(result.volume - 2) < 1e-6


def test_unwrap_passes_through_regular_shapes():
  box = Solid.make_box(1, 1, 1)
  assert _unwrap_boolean_result(box) is box


def test_generate_cutout_small_size_with_edge_offset():
  # Regression: these parameters (--edge-offsets 0.1 --edge-adjusts 0.2 on
  # a 24.7mm base) made the edge_offset self-intersection return a
  # dimension-less Compound, and the later lip adjustor union crashed with
  # "ValueError: Only shapes with the same dimension can be added".
  cutout = generate_cutout(
      24.7,
      tolerance=0.55,
      edge_adjust=0.2,
      edge_offset=0.1,
  )
  assert cutout.volume > 0
