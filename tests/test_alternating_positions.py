"""Tests for the alternating (nested) cutout layout.

Pinned coordinates were captured from real runs. Several tests document
fixes for review findings B1-B4 and B9 (see comments); they originally
pinned the buggy behavior and were inverted when the bugs were fixed.
"""
import pytest

from calculate_cutout_positions.calculate_alternating_cutout_positions import (
    calculate_alternating_cutout_positions,
    _side_from_hyp,
)

# Usable area for the default double tray (width 189.5, depth 66,
# rail_width 4.8, safety_margin (6.5, 0.8), tolerance 0.55).
UA_DOUBLE = {'min': {'x': -83.45, 'y': -31.925},
             'max': {'x': 83.45, 'y': 31.925}}

TOL = 0.55


def test_two_large_circles_nest_at_opposite_corners():
  positions = calculate_alternating_cutout_positions(
      {'min': {'x': -82.9, 'y': -31.65}, 'max': {'x': 82.9, 'y': 31.65}},
      [40, 40], [0, 0], TOL)

  assert positions[0]['x'] == pytest.approx(-62.9)   # min_x + d/2
  assert positions[0]['y'] == pytest.approx(-11.65)  # min_y + d/2
  assert positions[0]['flipped'] is False
  assert positions[1]['x'] == pytest.approx(62.9)    # max_x - d/2
  assert positions[1]['y'] == pytest.approx(11.65)   # max_y - d/2
  assert positions[1]['flipped'] is True


def test_five_mixed_diameters_pinned_layout():
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2, 49.6, 24.7], [0] * 5, TOL)

  expected = [
      (-71.1, -19.575, 24.7, False),
      (-42.278744, 7.125, 49.6, True),
      (0.0, -12.325, 39.2, False),
      (42.278744, 7.125, 49.6, True),
      (71.1, -19.575, 24.7, False),
  ]
  assert len(positions) == len(expected)
  for got, (x, y, d, flipped) in zip(positions, expected):
    assert got['x'] == pytest.approx(x, abs=1e-5)
    assert got['y'] == pytest.approx(y, abs=1e-5)
    assert got['diameter'] == d
    assert got['flipped'] is flipped


def test_flipped_flag_alternates():
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0, 40.0, 40.0], [0] * 3, TOL)
  assert [p['flipped'] for p in positions] == [False, True, False]


def test_redistribution_equalizes_edge_gaps():
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2, 49.6, 24.7], [0] * 5, TOL)

  gaps = []
  for a, b in zip(positions, positions[1:]):
    center_dist = ((b['x'] - a['x']) ** 2 + (b['y'] - a['y']) ** 2) ** 0.5
    # Physical clearance between the holes: subtract the toleranced radii.
    gaps.append(center_dist
                - (a['diameter'] + TOL) / 2 - (b['diameter'] + TOL) / 2)

  # All consecutive edge-to-edge gaps are equal and respect the validator's
  # 0.4mm minimum.
  for gap in gaps:
    assert gap == pytest.approx(gaps[0], abs=0.02)
    assert gap >= 0.4


def test_single_diameter_is_centered():
  # Review B4: this path used to rely on a leftover loop variable and
  # subtracted the edge offset; it now adds it (inward), matching the
  # multi-diameter and linear-layout convention.
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0], [0.5], TOL)

  assert len(positions) == 1
  assert positions[0]['x'] == 0
  assert positions[0]['y'] == pytest.approx(-11.425)  # min_y + 20 + 0.5
  assert positions[0]['flipped'] is False


def test_single_diameter_without_edge_offsets():
  # Review B4: an empty edge_offsets list used to raise IndexError here.
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0], [], TOL)
  assert positions[0]['y'] == pytest.approx(-11.925)  # min_y + 20


def test_edge_offsets_move_cutouts_inward_consistently():
  """Review B3 (fixed): every position moves inward, away from its resting
  edge — +y on the front row, -y on the back row, matching the linear
  layout convention."""
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0, 40.0, 40.0], [1.0, 1.0, 1.0], TOL)

  front_y = UA_DOUBLE['min']['y'] + 20.0 + 1.0
  back_y = UA_DOUBLE['max']['y'] - 20.0 - 1.0
  assert positions[0]['y'] == pytest.approx(front_y)
  assert positions[1]['y'] == pytest.approx(back_y)
  assert positions[2]['y'] == pytest.approx(front_y)


def test_y_boundary_violation_raises():
  """Review B1 (fixed): cutouts overflowing the usable area in y used to be
  silently accepted (the old boundary check `break`ed without flagging an
  error). 35mm bases in a 30mm-deep area must be rejected."""
  area = {'min': {'x': -40.0, 'y': -15.0}, 'max': {'x': 40.0, 'y': 15.0}}
  with pytest.raises(ValueError, match="does not fit"):
    calculate_alternating_cutout_positions(
        area, [35.0, 35.0], [0, 0], TOL)


def test_tolerance_affects_layout():
  """Review B9 (fixed): tolerance used to be ignored entirely by the
  alternating layout. It now sizes the physical holes, so a (much) larger
  tolerance produces a different layout when space is tight."""
  a = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2], [0] * 3, 0.55)
  b = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2], [0] * 3, 5.0)
  assert a != b


def test_overcrowded_layout_raises():
  # Too many large circles: they cannot all be placed inside the usable
  # area with the required clearance.
  with pytest.raises(ValueError, match="does not fit|too wide"):
    calculate_alternating_cutout_positions(
        UA_DOUBLE, [49.6] * 5, [0] * 5, TOL)


def test_non_consecutive_overlap_raises():
  """Review B2 (fixed): the overlap check only compared consecutive pairs,
  so two same-side circles (i and i+2) could overlap undetected. Here the
  tray is deep and narrow: consecutive gaps are fine (~0.6mm) but the two
  30mm circles both land on the front row almost on top of each other."""
  area = {'min': {'x': -22.0, 'y': -32.2}, 'max': {'x': 22.0, 'y': 32.2}}
  with pytest.raises(ValueError, match="too wide"):
    calculate_alternating_cutout_positions(
        area, [30.0, 34.0, 30.0], [0, 0, 0], TOL)


def test_circles_too_small_to_nest_raise_with_hint():
  # Two 10mm circles on opposite sides cannot touch across the tray depth;
  # the error should point the user at --force-linear-positions.
  with pytest.raises(ValueError, match="force-linear-positions"):
    calculate_alternating_cutout_positions(
        UA_DOUBLE, [10.0, 10.0], [0, 0], TOL)


def test_side_from_hyp_math():
  assert _side_from_hyp(5, 3) == pytest.approx(4.0)
  with pytest.raises(ValueError):
    _side_from_hyp(3, 5)
