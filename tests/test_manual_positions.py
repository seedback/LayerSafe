"""Tests for manual base placement (calculate_manual_cutout_positions)
and its dispatch through layout_engine.compute_layout.

Pure layout math: no CAD libraries required.
"""
import pytest

from shapes import get_shape
from calculate_cutout_positions.calculate_manual_cutout_positions import (
    calculate_manual_cutout_positions,
)
from functions.layout_engine import compute_layout
from functions.tray_config import TrayConfig

# Default double-tray usable area (see test_full_tray_helpers).
UA = {'min': {'x': -83.45, 'y': -31.925},
      'max': {'x': 83.45, 'y': 31.925}}
UA_SINGLE = {'min': {'x': -83.45, 'y': -31.925},
             'max': {'x': 83.45, 'y': 0}}
TOL = 0.55


def place(*pairs):
  return [{'x': x, 'edge': edge} for x, edge in pairs]


def test_manual_positions_use_given_x_and_derive_y():
  positions = calculate_manual_cutout_positions(
      UA, [24.7, 24.7], place((-50.0, 'front'), (30.0, 'back')),
      [], TOL, is_double_tray=True)

  assert positions[0]['x'] == -50.0
  assert positions[0]['y'] == pytest.approx(UA['min']['y'] + 24.7 / 2)
  assert positions[0]['flipped'] is False
  assert positions[0]['index'] == 0
  assert positions[1]['x'] == 30.0
  assert positions[1]['y'] == pytest.approx(UA['max']['y'] - 24.7 / 2)
  assert positions[1]['flipped'] is True
  assert positions[1]['index'] == 1


def test_manual_edge_defaults_to_front():
  positions = calculate_manual_cutout_positions(
      UA, [24.7], [{'x': 0.0}], [], TOL, is_double_tray=True)
  assert positions[0]['flipped'] is False
  assert positions[0]['y'] == pytest.approx(UA['min']['y'] + 24.7 / 2)


def test_manual_edge_offsets_move_bases_inward_on_both_edges():
  positions = calculate_manual_cutout_positions(
      UA, [24.7, 24.7], place((-50.0, 'front'), (30.0, 'back')),
      [0.5, 0.7], TOL, is_double_tray=True)
  # Same convention as the linear layout: offsets move the base away
  # from its resting edge, toward the middle.
  assert positions[0]['y'] == pytest.approx(UA['min']['y'] + 24.7 / 2 + 0.5)
  assert positions[1]['y'] == pytest.approx(UA['max']['y'] - 24.7 / 2 - 0.7)


def test_manual_y_matches_linear_layout_resting_y():
  # A manual placement mirroring the auto linear layout's rows must land
  # on exactly the same y values the linear layout produces.
  from calculate_cutout_positions.calculate_linear_cutout_positions import (
      calculate_linear_cutout_positions,
  )
  sizes = [24.7, 31.6, 24.7, 31.6]
  auto = calculate_linear_cutout_positions(
      UA, sizes, [0.2] * 4, TOL, is_double_tray=True)
  manual = calculate_manual_cutout_positions(
      UA, sizes,
      [{'x': pos['x'], 'edge': 'back' if pos['flipped'] else 'front'}
       for pos in sorted(auto, key=lambda p: p['index'])],
      [0.2] * 4, TOL, is_double_tray=True)
  for pos in auto:
    match = manual[pos['index']]
    assert match['x'] == pytest.approx(pos['x'])
    assert match['y'] == pytest.approx(pos['y'])
    assert match['flipped'] == pos['flipped']


def test_manual_out_of_bounds_names_the_base():
  with pytest.raises(ValueError, match=r"Base 2 .*usable area"):
    calculate_manual_cutout_positions(
        UA, [24.7, 24.7], place((0.0, 'front'), (80.0, 'front')),
        [], TOL, is_double_tray=True)


def test_manual_overlap_names_both_bases():
  with pytest.raises(ValueError, match=r"Base 1 .*overlaps.*Base 2"):
    calculate_manual_cutout_positions(
        UA, [24.7, 24.7], place((0.0, 'front'), (10.0, 'front')),
        [], TOL, is_double_tray=True)


def test_manual_overlap_uses_pair_nesting():
  # A circle and an oval nearly touching diagonally: circle tangency
  # would allow it, bounding boxes must reject it.
  circle = get_shape('circle')
  oval = get_shape('oval')
  sizes = [40.0, (40.0, 40.0)]
  layout_sizes = [circle.layout_sizes(40.0, TOL),
                  oval.layout_sizes((40.0, 40.0), TOL)]
  placements = place((-20.0, 'front'), (20.0, 'back'))

  # Circle + circle at the same spots is fine (diagonal tangency).
  calculate_manual_cutout_positions(
      UA, [40.0, 40.0], placements, [], TOL, is_double_tray=True,
      layout_sizes=[circle.layout_sizes(40.0, TOL)] * 2,
      nesting=['circle', 'circle'])

  with pytest.raises(ValueError, match="overlap"):
    calculate_manual_cutout_positions(
        UA, sizes, placements, [], TOL, is_double_tray=True,
        layout_sizes=layout_sizes, nesting=['circle', 'box'])


def test_manual_opposite_edges_may_kiss_in_the_middle():
  # The standard double tray runs opposing rows as close as ~0.1mm by
  # design (two 31.6 bases: 63.85 usable - 31.6 - 31.6 - 0.55 = 0.1mm),
  # so an opposite-edge pair at the same x must validate, matching the
  # linear layout's row rule.
  positions = calculate_manual_cutout_positions(
      UA, [31.6, 31.6], place((0.0, 'front'), (0.0, 'back')),
      [], TOL, is_double_tray=True)
  assert positions[0]['flipped'] is False
  assert positions[1]['flipped'] is True


def test_manual_opposite_edges_too_deep_must_clear_sideways():
  # Two 40mm bases are too deep to stack (40+40+0.55 > 63.85): rejected
  # at the same x, accepted when they interleave along x.
  with pytest.raises(ValueError, match=r"Base 1 .*Base 2 .*middle"):
    calculate_manual_cutout_positions(
        UA, [40.0, 40.0], place((-10.0, 'front'), (10.0, 'back')),
        [], TOL, is_double_tray=True)

  calculate_manual_cutout_positions(
      UA, [40.0, 40.0], place((-30.0, 'front'), (30.0, 'back')),
      [], TOL, is_double_tray=True)


def test_manual_back_edge_rejected_on_single_sided_tray():
  with pytest.raises(ValueError, match=r"Base 1 .*single-sided"):
    calculate_manual_cutout_positions(
        UA_SINGLE, [24.7], place((0.0, 'back')), [], TOL,
        is_double_tray=False)


def test_manual_unknown_edge_rejected():
  with pytest.raises(ValueError, match=r"Base 1 .*unknown edge 'middle'"):
    calculate_manual_cutout_positions(
        UA, [24.7], place((0.0, 'middle')), [], TOL, is_double_tray=True)


def test_manual_placement_count_must_match_sizes():
  with pytest.raises(ValueError, match="2 base sizes but 1 placements"):
    calculate_manual_cutout_positions(
        UA, [24.7, 24.7], place((0.0, 'front')), [], TOL,
        is_double_tray=True)


def test_compute_layout_dispatches_manual_placements():
  config = TrayConfig()
  base_shapes, positions = compute_layout(
      [24.7, 24.7], config,
      placements=place((-40.0, 'front'), (40.0, 'back')))
  assert [shape.name for shape in base_shapes] == ['circle', 'circle']
  assert positions[0]['x'] == -40.0
  assert positions[1]['flipped'] is True


def test_compute_layout_auto_matches_direct_dispatch():
  # Without placements, compute_layout must reproduce the automatic
  # layout exactly.
  from functions.layout_engine import (
      calculate_usable_area, calculate_cutout_positions)
  config = TrayConfig()
  sizes = [24.7, 49.6, 39.2, 49.6, 24.7]
  _, positions = compute_layout(sizes, config)
  ua = calculate_usable_area(
      config.total_width, config.total_depth, config.rail_width,
      config.safety_margin, config.tolerance, config.is_double_tray)
  shape = get_shape('circle')
  expected = calculate_cutout_positions(
      ua, sizes, [0] * 5, config.tolerance, config.is_double_tray,
      layout_sizes=[shape.layout_sizes(s, config.tolerance) for s in sizes],
      nesting=['circle'] * 5)
  assert positions == expected


def test_compute_layout_mixed_shapes_manual():
  # One oval among circles, manually placed: per-base layout sizes and
  # nesting flow through to validation.
  config = TrayConfig()
  base_shapes, positions = compute_layout(
      [(60.0, 35.0), 24.7, 24.7], config,
      shapes=['oval', None, None],
      placements=place((-45.0, 'front'), (20.0, 'back'), (50.0, 'back')))
  assert [shape.name for shape in base_shapes] == ['oval', 'circle',
                                                   'circle']
  oval_pos = positions[0]
  assert oval_pos['y'] == pytest.approx(
      -31.925 + 35.0 / 2)  # rests on the front edge with its own depth
