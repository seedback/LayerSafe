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
      UA_SINGLE, [30.0], [0], TOL, is_double_tray=False)

  assert len(positions) == 1
  assert positions[0]['x'] == pytest.approx(0.0)
  assert positions[0]['y'] == pytest.approx(-16.925)  # min_y + 15


def test_single_sided_base_deeper_than_tray_raises():
  # A 40mm base on a default-depth single-sided tray would overhang the
  # tray's open back edge (usable depth 31.925mm); needs --depth.
  with pytest.raises(ValueError, match="too deep"):
    calculate_linear_cutout_positions(
        UA_SINGLE, [40.0], [0], TOL, is_double_tray=False)


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
      [25.4, 25.4, 31.6, 30.0],
      [0.5, 0.6, 0.7, 0.8],
      TOL,
      is_double_tray=True)

  expected = [
      # front row: input indices 0 and 1, y = -31.925 + d/2 + offset
      {'x': -32.233333, 'y': -18.725, 'size': 25.4, 'flipped': False},
      {'x': 32.233333, 'y': -18.625, 'size': 25.4, 'flipped': False},
      # back row: input indices 2 and 3, y = 31.925 - d/2 - offset
      {'x': -32.733333, 'y': 15.425, 'size': 31.6, 'flipped': True},
      {'x': 33.533333, 'y': 16.125, 'size': 30.0, 'flipped': True},
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


def test_layout_sizes_widen_spacing_and_set_y():
  """Shapes wider than their measured size (hexes across corners) pass
  per-axis layout_sizes: x spacing must use the wide extent while the
  'size' key and the y resting extent keep their own values."""
  wide = 30.0 * 2 / (3 ** 0.5)  # hex-like: ~34.64 across corners
  positions = calculate_linear_cutout_positions(
      UA_SINGLE, [30.0, 30.0], [0, 0], TOL, is_double_tray=False,
      layout_sizes=[(wide, 30.0), (wide, 30.0)])

  # 'size' stays the measured scalar; y rests on the y extent.
  assert all(p['size'] == 30.0 for p in positions)
  assert all(p['y'] == pytest.approx(-31.925 + 15.0) for p in positions)

  # The physical edge-to-edge gap along x (using the wide extent) must
  # still respect min_spacing.
  gap = (positions[1]['x'] - positions[0]['x']) - wide
  assert gap >= MIN_SPACING - 1e-9

  # And the wide extent must actually spread the centers further apart
  # than the same bases laid out with their scalar size.
  narrow = calculate_linear_cutout_positions(
      UA_SINGLE, [30.0, 30.0], [0, 0], TOL, is_double_tray=False)
  assert (positions[1]['x'] - positions[0]['x']
          > narrow[1]['x'] - narrow[0]['x'])


def test_stacked_deep_bases_raise():
  """Two 40mm bases resting on opposite edges of a 66mm tray overlap by
  ~16mm in the middle at the same x. This used to be silently accepted
  (producing merged, unusable holes)."""
  with pytest.raises(ValueError, match="front and back rows overlap"):
    calculate_linear_cutout_positions(
        UA_DOUBLE, [40.0, 40.0], [0, 0], TOL, is_double_tray=True)


def test_deep_bases_allowed_when_rows_interleave_in_x():
  # On a wide-enough tray, deep bases may exceed half the depth as long
  # as front and back rows do not share x.
  wide = {'min': {'x': -120.0, 'y': -31.925}, 'max': {'x': 120.0, 'y': 31.925}}
  positions = calculate_linear_cutout_positions(
      wide, [40.0, 40.0, 40.0], [0] * 3, TOL, is_double_tray=True)

  front_xs = sorted(p['x'] for p in positions if not p['flipped'])
  back_xs = [p['x'] for p in positions if p['flipped']]
  assert len(front_xs) == 2 and len(back_xs) == 1
  # back base sits between the two front bases with real clearance
  assert front_xs[0] + 20.275 < back_xs[0] - 20.275
  assert back_xs[0] + 20.275 < front_xs[1] - 20.275


def test_oval_pair_sizes_flow_through_layout():
  # Oval bases carry (width, depth) pairs in 'size'; layout_sizes drive
  # both packing and y resting.
  positions = calculate_linear_cutout_positions(
      UA_SINGLE, [(60.0, 30.0), (60.0, 30.0)], [0, 0], TOL,
      is_double_tray=False, layout_sizes=[(60.0, 30.0), (60.0, 30.0)])

  assert all(p['size'] == (60.0, 30.0) for p in positions)
  assert all(p['y'] == pytest.approx(-31.925 + 15.0) for p in positions)
  gap = (positions[1]['x'] - positions[0]['x']) - 60.0
  assert gap >= MIN_SPACING - 1e-9


def test_line_fits_boundary_is_inclusive():
  # One item: total + 2 * min_spacing must be <= max_width.
  # 162.9 + 2 * 2.0 == 166.9 -> exactly fits; 163.0 does not.
  assert _line_fits(0, 0, 162.9, 166.9, TOL, MIN_SPACING) is True
  assert _line_fits(0, 0, 163.0, 166.9, TOL, MIN_SPACING) is False
