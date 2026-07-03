"""Characterization tests for the linear cutout layout.

These pin the CURRENT behavior of calculate_linear_cutout_positions so the
upcoming shape-abstraction refactor can be done safely. Tests whose names
start with test_bug_ document known-buggy behavior on purpose; when the bug
is fixed, invert the assertion rather than deleting the test.
"""
import pytest

from calculate_cutout_positions.calculate_linear_cutout_positions import (
    calculate_linear_cutout_positions,
    calculate_line_positions,
    _line_fits,
)

# Usable area for the default tray: width 189.5, depth 66, rail_width 4.8,
# safety_margin (6.5, 0.8), tolerance 0.55 (matches calculate_usable_area).
UA_DOUBLE = {'min': {'x': -83.45, 'y': -31.925},
             'max': {'x': 83.45, 'y': 31.925}}
UA_SINGLE = {'min': {'x': -83.45, 'y': -31.925},
             'max': {'x': 83.45, 'y': 0}}

TOL = 0.55
MIN_SPACING = 2.0


def test_single_sided_row_is_centered_and_evenly_spaced():
  positions = calculate_linear_cutout_positions(
      UA_SINGLE, [31.6, 31.6, 31.6], [0, 0, 0], TOL, is_double_tray=False)

  assert [p['x'] for p in positions] == pytest.approx([-49.9, 0.0, 49.9])
  # y is always resting on the front edge: min_y + size/2
  assert all(p['y'] == pytest.approx(-16.125) for p in positions)
  assert all(p['flipped'] is False for p in positions)
  assert all(p['size'] == 31.6 for p in positions)


def test_single_item_is_centered():
  positions = calculate_linear_cutout_positions(
      UA_SINGLE, [40.0], [0], TOL, is_double_tray=False)

  assert len(positions) == 1
  assert positions[0]['x'] == pytest.approx(0.0)
  assert positions[0]['y'] == pytest.approx(-11.925)  # min_y + 20


def test_empty_input_returns_empty_list():
  assert calculate_linear_cutout_positions(
      UA_SINGLE, [], [], TOL, is_double_tray=False) == []


def test_double_tray_splits_into_front_and_back_rows():
  positions = calculate_linear_cutout_positions(
      UA_DOUBLE, [31.6] * 6, [0] * 6, TOL, is_double_tray=True)

  front = [p for p in positions if not p['flipped']]
  back = [p for p in positions if p['flipped']]
  assert len(front) == 3 and len(back) == 3

  # Front row rests on the front edge, back row on the back edge (mirrored y),
  # and back-row cutouts are marked flipped so the lip is rotated 180.
  assert all(p['y'] == pytest.approx(-16.125) for p in front)
  assert all(p['y'] == pytest.approx(16.125) for p in back)
  # Both rows use the same x pattern.
  assert [p['x'] for p in front] == pytest.approx([-49.9, 0.0, 49.9])
  assert [p['x'] for p in back] == pytest.approx([-49.9, 0.0, 49.9])


def test_double_tray_row_assignment_and_edge_offsets():
  """Pins row assignment order (alternately taken from list start/end) and
  that edge offsets are indexed by ORIGINAL input position, pushing cutouts
  inward (+y on front row, -y on back row)."""
  positions = calculate_linear_cutout_positions(
      UA_DOUBLE,
      [25.4, 25.4, 31.6, 40.0],
      [0.5, 0.6, 0.7, 0.8],
      TOL,
      is_double_tray=True)

  expected = [
      # front row: input indices 0 and 1, y = -31.925 + d/2 + offset
      {'x': -32.233333, 'y': -18.725, 'size': 25.4, 'flipped': False},
      {'x': 32.233333, 'y': -18.625, 'size': 25.4, 'flipped': False},
      # back row: input indices 2 and 3, y = 31.925 - d/2 - offset
      {'x': -36.066667, 'y': 15.425, 'size': 31.6, 'flipped': True},
      {'x': 31.866667, 'y': 11.125, 'size': 40.0, 'flipped': True},
  ]
  assert len(positions) == len(expected)
  for got, want in zip(positions, expected):
    assert got['x'] == pytest.approx(want['x'], abs=1e-5)
    assert got['y'] == pytest.approx(want['y'], abs=1e-5)
    assert got['size'] == want['size']
    assert got['flipped'] is want['flipped']


def test_short_edge_offsets_list_is_safe():
  """Review B8 (fixed): an edge_offsets list shorter than the sizes list
  used to IndexError on the back row (guard checked the wrong length).
  Missing offsets are now treated as 0."""
  positions = calculate_linear_cutout_positions(
      UA_DOUBLE, [30.0, 30.0], [0.5], TOL, is_double_tray=True)

  assert positions[0]['y'] == pytest.approx(-31.925 + 15.0 + 0.5)
  assert positions[1]['y'] == pytest.approx(31.925 - 15.0)  # no offset


def test_line_positions_symmetric_margins_and_tolerance_gap():
  positions = calculate_line_positions(UA_DOUBLE, [40.0, 40.0], TOL,
                                       MIN_SPACING)

  xs = [p['x'] for p in positions]
  assert xs == pytest.approx([-34.666667, 34.666667], abs=1e-5)

  # Outer margins are equal (leftover space distributed evenly)...
  left_margin = (xs[0] - 20.0) - (-83.45)
  right_margin = 83.45 - (xs[1] + 20.0)
  assert left_margin == pytest.approx(right_margin)
  # ...and the interior edge-to-edge gap gets the margin plus one tolerance.
  interior_gap = (xs[1] - 20.0) - (xs[0] + 20.0)
  assert interior_gap == pytest.approx(left_margin + TOL)


@pytest.mark.parametrize("sizes", [
    [31.6, 31.6, 31.6, 31.6],
    [25.4, 40.0, 25.4],
    [49.6, 24.7, 39.2],
])
def test_row_stays_in_bounds_with_min_spacing(sizes):
  positions = calculate_line_positions(UA_DOUBLE, sizes, TOL, MIN_SPACING)

  edges = []
  for p in positions:
    left = p['x'] - p['size'] / 2
    right = p['x'] + p['size'] / 2
    assert left >= UA_DOUBLE['min']['x'] - 1e-9
    assert right <= UA_DOUBLE['max']['x'] + 1e-9
    edges.append((left, right))
  for (_, right_a), (left_b, _) in zip(edges, edges[1:]):
    assert left_b - right_a >= MIN_SPACING - 1e-9


def test_overflow_raises_single_sided():
  with pytest.raises(ValueError, match="too wide"):
    calculate_linear_cutout_positions(
        UA_SINGLE, [40.0] * 5, [0] * 5, TOL, is_double_tray=False)


def test_overflow_raises_double_when_both_rows_full():
  with pytest.raises(ValueError, match="too wide"):
    calculate_linear_cutout_positions(
        UA_DOUBLE, [40.0] * 9, [0] * 9, TOL, is_double_tray=True)


def test_line_fits_boundary_is_inclusive():
  # One item: total + 2 * min_spacing must be <= max_width.
  # 162.9 + 2 * 2.0 == 166.9 -> exactly fits; 163.0 does not.
  assert _line_fits(0, 0, 162.9, 166.9, TOL, MIN_SPACING) is True
  assert _line_fits(0, 0, 163.0, 166.9, TOL, MIN_SPACING) is False
