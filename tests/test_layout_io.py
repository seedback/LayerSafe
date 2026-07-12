"""Tests for the layout file format (functions/layout_io.py): parsing,
validation errors, export, and the auto-layout -> export -> import
round-trip that the UI flow depends on.

Pure math and JSON: no CAD libraries required.
"""
import json

import pytest

from functions.layout_io import (
    parse_layout, load_layout, build_layout, save_layout, LAYOUT_VERSION,
)
from functions.layout_engine import compute_layout
from functions.tray_config import TrayConfig


def minimal(**overrides):
  data = {
      'bases': [
          {'size': 24.7, 'x': -40.0, 'edge': 'front'},
          {'size': 24.7, 'x': 40.0, 'edge': 'back'},
      ],
  }
  data.update(overrides)
  return data


def test_parse_minimal_layout():
  layout = parse_layout(minimal())
  assert layout['sizes'] == [24.7, 24.7]
  assert layout['shapes'] == [None, None]
  assert layout['placements'] == [{'x': -40.0, 'edge': 'front'},
                                  {'x': 40.0, 'edge': 'back'}]
  assert layout['edge_offsets'] == [0, 0]
  assert layout['edge_adjusts'] == [0, 0]
  assert layout['tray'] == {}
  assert layout['default_shape'] is None


def test_parse_full_layout():
  layout = parse_layout({
      'version': LAYOUT_VERSION,
      'tray': {'width': 200.0, 'depth': 70.0, 'double_sided': False},
      'defaults': {'shape': 'hex'},
      'bases': [
          {'shape': 'oval', 'size': [60, 35], 'x': -45.0,
           'edge': 'front', 'edge_offset': 0.5, 'edge_adjust': 0.2},
          {'size': '29.8', 'x': 30.0},
      ],
  })
  assert layout['tray'] == {'width': 200.0, 'depth': 70.0,
                            'double_sided': False}
  assert layout['default_shape'] == 'hex'
  assert layout['sizes'] == [(60.0, 35.0), 29.8]
  assert layout['shapes'] == ['oval', None]
  assert layout['edge_offsets'] == [0.5, 0]
  assert layout['edge_adjusts'] == [0.2, 0]
  # edge defaults to front
  assert layout['placements'][1] == {'x': 30.0, 'edge': 'front'}


def test_parse_rejects_y_key_with_phase2_message():
  data = minimal()
  data['bases'][0]['y'] = -10.0
  with pytest.raises(ValueError, match=r"Base 1: free y placement"):
    parse_layout(data)


@pytest.mark.parametrize("mutate, match", [
    (lambda d: d.update(extra=1), "Unknown layout key"),
    (lambda d: d['tray'].update(color='red'), "Unknown tray key"),
    (lambda d: d['bases'][0].update(rotation=90), "Base 1: unknown key"),
    (lambda d: d['bases'][1].pop('x'), "Base 2: missing 'x'"),
    (lambda d: d['bases'][0].pop('size'), "Base 1: missing 'size'"),
    (lambda d: d['bases'][0].update(edge='left'), "Base 1: unknown edge"),
    (lambda d: d['bases'][0].update(shape='bogus'), "Unknown cutout shape"),
    (lambda d: d['bases'][0].update(size=[1, 2, 3]), "Base 1: size"),
    (lambda d: d['bases'][0].update(x="left"), "Base 1: x must be a number"),
    (lambda d: d['tray'].update(width=-5), "tray.width must be positive"),
    (lambda d: d.update(version=99), "Unsupported layout version"),
    (lambda d: d.update(bases=[]), "non-empty 'bases'"),
])
def test_parse_errors(mutate, match):
  data = minimal(tray={})
  mutate(data)
  with pytest.raises(ValueError, match=match):
    parse_layout(data)


def test_parse_rejects_pair_size_for_scalar_shape():
  data = minimal()
  data['bases'][0].update(shape='circle', size=[60, 35])
  with pytest.raises(ValueError, match="Base 1: 'circle'"):
    parse_layout(data)


def test_load_layout_reports_bad_json(tmp_path):
  path = tmp_path / "broken.json"
  path.write_text("{not json")
  with pytest.raises(ValueError, match="not valid JSON"):
    load_layout(str(path))


def test_save_and_load_round_trip(tmp_path):
  config = TrayConfig()
  layout_dict = build_layout(
      [24.7, (60.0, 35.0)], ['circle', 'oval'],
      [{'x': -40.0, 'y': 0, 'size': 24.7, 'index': 0, 'flipped': False},
       {'x': 30.0, 'y': 0, 'size': (60.0, 35.0), 'index': 1,
        'flipped': True}],
      config, edge_offsets=[0.5, 0], edge_adjusts=[0, 0.2])
  path = tmp_path / "layout.json"
  save_layout(str(path), layout_dict)

  layout = load_layout(str(path))
  assert layout['sizes'] == [24.7, (60.0, 35.0)]
  # circle is the tray default so it stays implicit; oval is spelled out.
  assert layout['shapes'] == [None, 'oval']
  assert layout['placements'] == [{'x': -40.0, 'edge': 'front'},
                                  {'x': 30.0, 'edge': 'back'}]
  assert layout['edge_offsets'] == [0.5, 0]
  assert layout['edge_adjusts'] == [0, 0.2]
  assert layout['tray'] == {'width': config.total_width,
                            'depth': config.total_depth,
                            'double_sided': True}


def test_auto_layout_export_import_reproduces_positions(tmp_path):
  """The UI flow: auto-layout -> export -> import -> identical layout."""
  config = TrayConfig()
  sizes = [24.7, 49.6, 39.2, 49.6, 24.7]
  base_shapes, auto_positions = compute_layout(sizes, config)

  layout_dict = build_layout(
      sizes, [shape.name for shape in base_shapes], auto_positions, config)
  path = tmp_path / "roundtrip.json"
  save_layout(str(path), layout_dict)

  layout = load_layout(str(path))
  _, manual_positions = compute_layout(
      layout['sizes'], config,
      edge_offsets=layout['edge_offsets'],
      shapes=layout['shapes'],
      placements=layout['placements'])

  by_index = {pos['index']: pos for pos in auto_positions}
  assert len(manual_positions) == len(auto_positions)
  for pos in manual_positions:
    auto = by_index[pos['index']]
    # Exact: x survives the file at full precision, y is re-derived
    # from the same formula, so the regenerated tray is byte-identical.
    assert pos['x'] == auto['x']
    assert pos['y'] == auto['y']
    assert pos['flipped'] == auto['flipped']
    assert pos['size'] == auto['size']


def test_linear_layout_export_import_reproduces_positions(tmp_path):
  """Dense two-row linear layouts (opposing rows ~0.1mm apart) must
  survive the export -> import round-trip too."""
  config = TrayConfig(force_linear_positions=True)
  sizes = [31.6, 31.6, 31.6, 31.6]
  base_shapes, auto_positions = compute_layout(sizes, config)

  path = tmp_path / "linear.json"
  save_layout(str(path), build_layout(
      sizes, [shape.name for shape in base_shapes], auto_positions, config))

  layout = load_layout(str(path))
  _, manual_positions = compute_layout(
      layout['sizes'], config,
      edge_offsets=layout['edge_offsets'],
      shapes=layout['shapes'],
      placements=layout['placements'])

  by_index = {pos['index']: pos for pos in auto_positions}
  for pos in manual_positions:
    auto = by_index[pos['index']]
    assert pos['x'] == auto['x']
    assert pos['y'] == auto['y']
    assert pos['flipped'] == auto['flipped']


def test_export_is_valid_json_with_expected_shape(tmp_path):
  config = TrayConfig()
  sizes = [24.7, 24.7]
  base_shapes, positions = compute_layout(sizes, config)
  path = tmp_path / "export.json"
  save_layout(str(path), build_layout(
      sizes, [shape.name for shape in base_shapes], positions, config))

  data = json.loads(path.read_text())
  assert data['version'] == LAYOUT_VERSION
  assert set(data) == {'version', 'tray', 'defaults', 'bases'}
  assert all(set(base) <= {'shape', 'size', 'x', 'edge', 'edge_offset',
                           'edge_adjust'} for base in data['bases'])
