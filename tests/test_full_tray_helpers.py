"""Tests for the pure-math helpers in full_tray_generator: usable-area
computation and the linear/alternating layout dispatch.

full_tray_generator imports build123d and ocp_vscode at module level, so
this file is skipped when the CAD dependencies are not installed. The tests
themselves never build geometry.
"""
import pytest

pytest.importorskip("build123d")
pytest.importorskip("ocp_vscode")

from functions.full_tray_generator import (  # noqa: E402
    calculate_usable_area,
    calculate_cutout_positions,
    generate_full_tray,
)
from functions.tray_config import TrayConfig  # noqa: E402

# Default tray parameters.
WIDTH, DEPTH = 189.5, 66.0
RAIL_WIDTH = 4.8
MARGIN = (6.5, 0.8)
TOL = 0.55


@pytest.fixture(scope="module")
def ua_double():
  return calculate_usable_area(WIDTH, DEPTH, RAIL_WIDTH, MARGIN, TOL, True)


def test_usable_area_double():
  ua = calculate_usable_area(WIDTH, DEPTH, RAIL_WIDTH, MARGIN, TOL, True)
  # x: half width minus rail minus x-margin; y: half depth minus y-margin
  # minus half tolerance, symmetric for a double tray.
  assert ua['min']['x'] == pytest.approx(-83.45)
  assert ua['max']['x'] == pytest.approx(83.45)
  assert ua['min']['y'] == pytest.approx(-31.925)
  assert ua['max']['y'] == pytest.approx(31.925)


def test_usable_area_single_sided_caps_y_at_zero():
  ua = calculate_usable_area(WIDTH, DEPTH, RAIL_WIDTH, MARGIN, TOL, False)
  assert ua['min']['y'] == pytest.approx(-31.925)
  assert ua['max']['y'] == 0


def test_dispatch_empty_input(ua_double):
  assert calculate_cutout_positions(ua_double, [], [], TOL) == []


def test_dispatch_small_sizes_use_linear(ua_double):
  # max size <= -min_y (31.925): linear layout, rows stack at same x.
  positions = calculate_cutout_positions(
      ua_double, [25.0, 25.0], [0, 0], TOL, is_double_tray=True)
  assert [p['x'] for p in positions] == pytest.approx([0.0, 0.0])
  assert [p['flipped'] for p in positions] == [False, True]


def test_dispatch_large_sizes_use_alternating(ua_double):
  # max size > -min_y: alternating layout, nested at opposite corners.
  positions = calculate_cutout_positions(
      ua_double, [40.0, 40.0], [0, 0], TOL, is_double_tray=True)
  assert positions[0]['x'] == pytest.approx(-63.45)
  assert positions[1]['x'] == pytest.approx(63.45)
  assert [p['flipped'] for p in positions] == [False, True]


def test_dispatch_force_linear_overrides_alternating(ua_double):
  # 33mm > 31.925 would normally pick the alternating layout; the force
  # flag stacks the bases on straight rows instead (33 + 25 still fits
  # the tray depth).
  positions = calculate_cutout_positions(
      ua_double, [33.0, 25.0], [0, 0], TOL, is_double_tray=True,
      force_linear_positions=True)
  assert [p['x'] for p in positions] == pytest.approx([0.0, 0.0])
  assert [p['flipped'] for p in positions] == [False, True]


def test_dispatch_force_linear_rejects_overlapping_rows(ua_double):
  # Forcing two 40mm bases onto stacked rows of a 66mm tray would merge
  # their holes in the middle; the layout must refuse.
  with pytest.raises(ValueError, match="front and back rows overlap"):
    calculate_cutout_positions(
        ua_double, [40.0, 40.0], [0, 0], TOL, is_double_tray=True,
        force_linear_positions=True)


def test_dispatch_mixed_shapes_uses_per_pair_nesting(ua_double):
  # A circle next to an oval: alternating layout (40 > 31.925), and the
  # mixed pair must be spaced by bounding boxes, not circle tangency.
  positions = calculate_cutout_positions(
      ua_double, [40.0, (60.0, 35.0)], [0, 0], TOL, is_double_tray=True,
      layout_sizes=[(40.0, 40.0), (60.0, 35.0)],
      nesting=['circle', 'box'])
  min_dx = (40.0 + TOL) / 2 + (60.0 + TOL) / 2
  assert abs(positions[1]['x'] - positions[0]['x']) >= min_dx - 0.01
  assert [p['index'] for p in positions] == [0, 1]


def test_generate_full_tray_validation_names_the_base():
  # Per-base size validation fires before any geometry is built and
  # names the offending base.
  with pytest.raises(ValueError, match="Base 2:.*WIDTHxDEPTH"):
    generate_full_tray([24.7, 31.6], TrayConfig(),
                       shapes=[None, 'oval'])
  with pytest.raises(ValueError, match="Base 1:.*single size number"):
    generate_full_tray([(60.0, 35.0), 24.7], TrayConfig())


def test_dispatch_single_sided_always_linear():
  # Single-sided trays have no back row, so the linear layout is used
  # even for large bases (given enough depth, e.g. --depth 132).
  ua = calculate_usable_area(WIDTH, 132.0, RAIL_WIDTH, MARGIN, TOL, False)
  positions = calculate_cutout_positions(
      ua, [40.0, 40.0], [0, 0], TOL, is_double_tray=False)
  assert all(p['flipped'] is False for p in positions)
  assert all(p['y'] == pytest.approx(-44.925) for p in positions)
