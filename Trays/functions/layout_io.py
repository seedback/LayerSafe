"""Load and save manual-placement layout files (JSON).

The layout file is the interchange format between the generator and any
UI: `tray_generator.py --export-layout` writes one from a computed
layout, a user (or UI) edits it, and `--layout` feeds it back in. See
docs/feature-manual-placement.md for the schema.

Coordinates are tray-centered millimeters: origin at the tray center,
x positive to the right, y positive toward the back. Each base gives its
cutout-center `x` and the `edge` it rests on ('front' or 'back'); y is
derived from the edge, so a `y` key is rejected until free y placement
(Phase 2) exists.

This module must stay importable without the CAD libraries (build123d).
"""
import json

try:
  from .shapes import get_shape, parse_size
except ImportError:
  from shapes import get_shape, parse_size

LAYOUT_VERSION = 1

_TOP_KEYS = {'version', 'tray', 'defaults', 'bases'}
_TRAY_KEYS = {'width', 'depth', 'double_sided'}
_BASE_KEYS = {'shape', 'size', 'x', 'edge', 'edge_offset', 'edge_adjust'}


def _is_number(value):
  return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_number(value, what):
  if not _is_number(value):
    raise ValueError(f"{what} must be a number, got {value!r}")
  return float(value)


def _parse_base_size(value, what):
  """A size is a number (scalar shapes), a [width, depth] pair (oval), or
  a string in the CLI's size syntax ('31.6', '60x35')."""
  if _is_number(value):
    return float(value)
  if isinstance(value, list):
    if len(value) != 2 or not all(_is_number(v) for v in value):
      raise ValueError(
          f"{what} must be a number, a [width, depth] pair, or a string "
          f"like \"60x35\"; got {value!r}")
    return (float(value[0]), float(value[1]))
  if isinstance(value, str):
    try:
      return parse_size(value)
    except ValueError as e:
      raise ValueError(f"{what}: {e}") from None
  raise ValueError(
      f"{what} must be a number, a [width, depth] pair, or a string "
      f"like \"60x35\"; got {value!r}")


def parse_layout(data):
  """Validate a layout dict (already JSON-decoded) and unpack it.

  Returns a dict with keys: 'tray' (dict with any of width / depth /
  double_sided the file set), 'default_shape' (name or None), and the
  parallel per-base lists 'sizes', 'shapes', 'edge_offsets',
  'edge_adjusts', 'placements'. Raises ValueError naming the offending
  key or base. Shape/size compatibility (e.g. oval:31.6) is checked
  later by the layout engine, which also knows the tray's default shape.
  """
  if not isinstance(data, dict):
    raise ValueError("Layout file must contain a JSON object at the top "
                     "level.")
  unknown = set(data) - _TOP_KEYS
  if unknown:
    raise ValueError(
        f"Unknown layout key(s): {', '.join(sorted(unknown))}. "
        f"Valid keys: {', '.join(sorted(_TOP_KEYS))}.")
  version = data.get('version', LAYOUT_VERSION)
  if version != LAYOUT_VERSION:
    raise ValueError(
        f"Unsupported layout version {version!r} (this generator "
        f"supports version {LAYOUT_VERSION}).")

  tray = {}
  if 'tray' in data:
    if not isinstance(data['tray'], dict):
      raise ValueError("'tray' must be an object.")
    unknown = set(data['tray']) - _TRAY_KEYS
    if unknown:
      raise ValueError(
          f"Unknown tray key(s): {', '.join(sorted(unknown))}. "
          f"Valid keys: {', '.join(sorted(_TRAY_KEYS))}.")
    for key in ('width', 'depth'):
      if key in data['tray']:
        value = _require_number(data['tray'][key], f"tray.{key}")
        if value <= 0:
          raise ValueError(f"tray.{key} must be positive, got {value}")
        tray[key] = value
    if 'double_sided' in data['tray']:
      if not isinstance(data['tray']['double_sided'], bool):
        raise ValueError("tray.double_sided must be true or false.")
      tray['double_sided'] = data['tray']['double_sided']

  default_shape = None
  if 'defaults' in data:
    if not isinstance(data['defaults'], dict):
      raise ValueError("'defaults' must be an object.")
    unknown = set(data['defaults']) - {'shape'}
    if unknown:
      raise ValueError(
          f"Unknown defaults key(s): {', '.join(sorted(unknown))}. "
          "The only valid key is 'shape'.")
    if 'shape' in data['defaults']:
      default_shape = get_shape(data['defaults']['shape']).name

  if 'bases' not in data or not isinstance(data['bases'], list) \
          or not data['bases']:
    raise ValueError("Layout file needs a non-empty 'bases' list.")

  sizes, shapes, edge_offsets, edge_adjusts, placements = [], [], [], [], []
  for i, base in enumerate(data['bases']):
    label = f"Base {i + 1}"
    if not isinstance(base, dict):
      raise ValueError(f"{label}: each base must be an object.")
    if 'y' in base:
      raise ValueError(
          f"{label}: free y placement is not supported yet; place bases "
          "with 'x' and 'edge' ('front' or 'back'). A base always rests "
          "against its edge.")
    unknown = set(base) - _BASE_KEYS
    if unknown:
      raise ValueError(
          f"{label}: unknown key(s): {', '.join(sorted(unknown))}. "
          f"Valid keys: {', '.join(sorted(_BASE_KEYS))}.")
    if 'size' not in base:
      raise ValueError(f"{label}: missing 'size'.")
    if 'x' not in base:
      raise ValueError(f"{label}: missing 'x' (cutout-center position, "
                       "0 is the tray center).")
    size = _parse_base_size(base['size'], f"{label}: size")
    shape_name = None
    if 'shape' in base:
      shape = get_shape(base['shape'])
      try:
        shape.validate_size(size)
      except ValueError as e:
        raise ValueError(f"{label}: {e}") from None
      shape_name = shape.name
    edge = base.get('edge', 'front')
    if edge not in ('front', 'back'):
      raise ValueError(
          f"{label}: unknown edge {edge!r}. Use 'front' or 'back'.")
    sizes.append(size)
    shapes.append(shape_name)
    edge_offsets.append(
        _require_number(base.get('edge_offset', 0),
                        f"{label}: edge_offset"))
    edge_adjusts.append(
        _require_number(base.get('edge_adjust', 0),
                        f"{label}: edge_adjust"))
    placements.append({'x': _require_number(base['x'], f"{label}: x"),
                       'edge': edge})

  return {
      'tray': tray,
      'default_shape': default_shape,
      'sizes': sizes,
      'shapes': shapes,
      'edge_offsets': edge_offsets,
      'edge_adjusts': edge_adjusts,
      'placements': placements,
  }


def load_layout(path):
  """Read and parse a layout file; see parse_layout."""
  try:
    with open(path, encoding='utf-8') as f:
      data = json.load(f)
  except json.JSONDecodeError as e:
    raise ValueError(f"'{path}' is not valid JSON: {e}") from None
  except OSError as e:
    raise ValueError(f"Cannot read layout file '{path}': {e}") from None
  try:
    return parse_layout(data)
  except ValueError as e:
    raise ValueError(f"Invalid layout file '{path}': {e}") from None


def build_layout(sizes, shapes, positions, config,
                 edge_offsets=None, edge_adjusts=None):
  """Build a layout dict (the export half of the round-trip) from a
  computed position list, ready for save_layout. `shapes` is the
  per-base shape-name list (None entries mean the tray default);
  positions are matched to bases via their 'index' key."""
  by_index = {pos['index']: pos for pos in positions}
  bases = []
  for i, size in enumerate(sizes):
    pos = by_index[i]
    base = {}
    shape_name = shapes[i] if shapes and i < len(shapes) else None
    if shape_name is not None and shape_name != config.cutout_shape:
      base['shape'] = shape_name
    base['size'] = list(size) if isinstance(size, (tuple, list)) else size
    # Full precision on purpose: re-importing the file must reproduce
    # the exact same tray, byte for byte.
    base['x'] = pos['x']
    base['edge'] = 'back' if pos['flipped'] else 'front'
    if edge_offsets and i < len(edge_offsets) and edge_offsets[i]:
      base['edge_offset'] = edge_offsets[i]
    if edge_adjusts and i < len(edge_adjusts) and edge_adjusts[i]:
      base['edge_adjust'] = edge_adjusts[i]
    bases.append(base)

  return {
      'version': LAYOUT_VERSION,
      'tray': {
          'width': config.total_width,
          'depth': config.total_depth,
          'double_sided': config.is_double_tray,
      },
      'defaults': {'shape': config.cutout_shape},
      'bases': bases,
  }


def save_layout(path, layout):
  """Write a layout dict (from build_layout) as pretty-printed JSON."""
  with open(path, 'w', encoding='utf-8') as f:
    json.dump(layout, f, indent=2)
    f.write('\n')
