"""Tests for mixing base shapes in one tray (per-base nesting in the
alternating layout, and the 'index' key both layouts attach so the
orchestrator can map positions back to per-base inputs).

Pure layout math: no CAD libraries required.
"""
import pytest

from shapes import get_shape
from calculate_cutout_positions.calculate_alternating_cutout_positions import (
    calculate_alternating_cutout_positions,
)
from calculate_cutout_positions.calculate_linear_cutout_positions import (
    calculate_linear_cutout_positions,
)

# Default double-tray usable area (see test_full_tray_helpers).
UA = {'min': {'x': -83.45, 'y': -31.925},
      'max': {'x': 83.45, 'y': 31.925}}
TOL = 0.55


def layout_sizes_for(specs):
  """specs: list of (shape_name, size) -> per-base (x, y) layout sizes."""
  return [get_shape(name).layout_sizes(size, TOL) for name, size in specs]


def test_alternating_broadcast_matches_single_string_nesting():
  # A per-base all-circle list must place bases exactly where the old
  # single-string nesting did (backward compatibility).
  sizes = [40.0, 40.0, 40.0]
  old = calculate_alternating_cutout_positions(
      UA, sizes, [], TOL, nesting='circle')
  new = calculate_alternating_cutout_positions(
      UA, sizes, [], TOL, nesting=['circle'] * 3)
  for a, b in zip(old, new):
    assert a['x'] == b['x']
    assert a['y'] == b['y']
  # Same for all-box.
  old = calculate_alternating_cutout_positions(
      UA, sizes, [], TOL, nesting='box')
  new = calculate_alternating_cutout_positions(
      UA, sizes, [], TOL, nesting=['box'] * 3)
  for a, b in zip(old, new):
    assert a['x'] == b['x']
    assert a['y'] == b['y']


def test_alternating_positions_carry_index_in_input_order():
  positions = calculate_alternating_cutout_positions(
      UA, [40.0, 40.0, 40.0], [], TOL, nesting='circle')
  assert [p['index'] for p in positions] == [0, 1, 2]


def test_alternating_mixed_oval_among_circles():
  # The motivating use case: one oval among circles. Pairs that involve
  # the box-nested oval must be spaced by bounding boxes; circle-circle
  # pairs may still nest by tangency.
  specs = [('circle', 40.0), ('oval', (60.0, 35.0)), ('circle', 40.0)]
  sizes = [size for _, size in specs]
  ls = layout_sizes_for(specs)
  nesting = [get_shape(name).nesting for name, _ in specs]

  positions = calculate_alternating_cutout_positions(
      UA, sizes, [], TOL, layout_sizes=ls, nesting=nesting)

  assert [p['index'] for p in positions] == [0, 1, 2]
  assert [p['flipped'] for p in positions] == [False, True, False]

  # The circle-oval pairs rest on opposite edges but are too deep to
  # clear vertically, so box nesting demands full horizontal separation
  # of the toleranced holes.
  for a, b in ((0, 1), (1, 2)):
    min_dx = (ls[a][0] + TOL) / 2 + (ls[b][0] + TOL) / 2
    assert abs(positions[b]['x'] - positions[a]['x']) >= min_dx - 0.01

  # Everything stays inside the usable area.
  for pos, (fx, fy) in zip(positions, ls):
    assert pos['x'] - fx / 2 >= UA['min']['x'] - 0.1
    assert pos['x'] + fx / 2 <= UA['max']['x'] + 0.1
    assert pos['y'] - fy / 2 >= UA['min']['y'] - 0.1
    assert pos['y'] + fy / 2 <= UA['max']['y'] + 0.1


def test_alternating_mixed_pair_rejects_overcrowding():
  # Two ovals and a circle that would fit under (incorrect) circle
  # tangency but not under box spacing must be rejected.
  specs = [('oval', (60.0, 35.0)), ('circle', 40.0), ('oval', (60.0, 35.0)),
           ('circle', 40.0)]
  sizes = [size for _, size in specs]
  ls = layout_sizes_for(specs)
  nesting = [get_shape(name).nesting for name, _ in specs]
  with pytest.raises(ValueError):
    calculate_alternating_cutout_positions(
        UA, sizes, [], TOL, layout_sizes=ls, nesting=nesting)


# Two wide ovals and one circle: the second oval no longer fits the
# front row and overflows to the end of the back row, so the position
# order genuinely differs from the input order.
REORDERING_SPECS = [('oval', (100.0, 30.0)), ('oval', (100.0, 30.0)),
                    ('circle', 33.0)]


def test_linear_positions_carry_original_index():
  # The double-row linear layout can reorder bases; each position must
  # say which input base it belongs to.
  sizes = [size for _, size in REORDERING_SPECS]
  ls = layout_sizes_for(REORDERING_SPECS)
  positions = calculate_linear_cutout_positions(
      UA, sizes, [], TOL, is_double_tray=True, layout_sizes=ls)
  for pos in positions:
    assert pos['size'] == sizes[pos['index']]
  # The index key is doing real work here: position order != input order.
  assert [p['index'] for p in positions] == [0, 2, 1]


def test_linear_mixed_oval_among_circles_maps_indices():
  specs = [('circle', 24.7), ('oval', (60.0, 35.0)), ('circle', 24.7),
           ('circle', 24.7)]
  sizes = [size for _, size in specs]
  ls = layout_sizes_for(specs)
  positions = calculate_linear_cutout_positions(
      UA, sizes, [], TOL, is_double_tray=True, layout_sizes=ls)
  assert sorted(p['index'] for p in positions) == [0, 1, 2, 3]
  for pos in positions:
    assert pos['size'] == sizes[pos['index']]
    # Each base rests on its row's edge using its own depth.
    fy = ls[pos['index']][1]
    if pos['flipped']:
      assert pos['y'] == pytest.approx(UA['max']['y'] - fy / 2)
    else:
      assert pos['y'] == pytest.approx(UA['min']['y'] + fy / 2)


def test_linear_edge_offsets_follow_their_base_when_rows_reorder():
  # Regression: per-base edge offsets must stay with their base even
  # when the two rows change the position order.
  sizes = [size for _, size in REORDERING_SPECS]
  ls = layout_sizes_for(REORDERING_SPECS)
  edge_offsets = [0.1, 0.2, 0.3]
  positions = calculate_linear_cutout_positions(
      UA, sizes, edge_offsets, TOL, is_double_tray=True, layout_sizes=ls)
  assert [p['index'] for p in positions] == [0, 2, 1]
  for pos in positions:
    offset = edge_offsets[pos['index']]
    fy = ls[pos['index']][1]
    if pos['flipped']:
      assert pos['y'] == pytest.approx(UA['max']['y'] - fy / 2 - offset)
    else:
      assert pos['y'] == pytest.approx(UA['min']['y'] + fy / 2 + offset)
