"""Characterization tests for the alternating (nested) cutout layout.

These pin the CURRENT behavior of calculate_alternating_cutout_positions.
Tests whose names start with test_bug_ intentionally assert known-buggy
behavior (bug IDs reference the code-review findings); when a bug is fixed,
invert the assertion rather than deleting the test.
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
    gaps.append(center_dist - a['diameter'] / 2 - b['diameter'] / 2)

  # All consecutive edge-to-edge gaps are equal and respect the validator's
  # 0.4mm minimum.
  for gap in gaps:
    assert gap == pytest.approx(gaps[0], abs=0.02)
    assert gap >= 0.4


def test_single_diameter_is_centered():
  # Note (review B4): this path relies on a leftover loop variable and
  # SUBTRACTS the edge offset, while multi-diameter non-flipped positions
  # add it (see test_bug_b3_...). Pinning current output.
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0], [0.5], TOL)

  assert len(positions) == 1
  assert positions[0]['x'] == 0
  assert positions[0]['y'] == pytest.approx(-12.425)  # min_y + 20 - 0.5
  assert positions[0]['flipped'] is False


def test_bug_b3_edge_offset_sign_is_inconsistent():
  """BUG B3: the first position subtracts its edge offset, later non-flipped
  positions add it — same tray side, opposite direction. When fixed, both
  should move the cutout the same way (linear layout convention: inward)."""
  positions = calculate_alternating_cutout_positions(
      UA_DOUBLE, [40.0, 40.0, 40.0], [1.0, 1.0, 1.0], TOL)

  base_y = UA_DOUBLE['min']['y'] + 20.0  # resting on front edge
  assert positions[0]['y'] == pytest.approx(base_y - 1.0)  # offset subtracted
  assert positions[2]['y'] == pytest.approx(base_y + 1.0)  # offset added


def test_bug_b1_y_boundary_violation_not_detected():
  """BUG B1: the boundary check `break`s without flagging an error, so
  cutouts overflowing the usable area in y are silently accepted (here the
  gaps are wide, so the overlap check does not catch it either). When fixed,
  this input should raise ValueError."""
  area = {'min': {'x': -40.0, 'y': -15.0}, 'max': {'x': 40.0, 'y': 15.0}}
  positions = calculate_alternating_cutout_positions(
      area, [35.0, 35.0], [0, 0], TOL)

  top_edge = positions[0]['y'] + 35.0 / 2
  assert top_edge == pytest.approx(20.0)  # 5mm past max_y = 15.0, no error


def test_bug_b9_tolerance_has_no_effect():
  """BUG B9: alternating layout computes `full_diameters` but never uses it,
  so `tolerance` does not influence the result (linear layout does apply
  it). When fixed, larger tolerance should spread the cutouts further."""
  a = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2], [0] * 3, 0.55)
  b = calculate_alternating_cutout_positions(
      UA_DOUBLE, [24.7, 49.6, 39.2], [0] * 3, 5.0)
  assert a == b


def test_overcrowded_layout_raises():
  # Too many large circles: consecutive gaps collapse below the 0.4mm
  # minimum and the validator rejects the layout.
  with pytest.raises(ValueError, match="too wide"):
    calculate_alternating_cutout_positions(
        UA_DOUBLE, [49.6] * 5, [0] * 5, TOL)


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
