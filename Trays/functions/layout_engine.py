# %%
"""The pure-math layout pipeline: usable area, shape resolution, and
cutout positioning (automatic linear/alternating or manual placement).

This module must stay importable without the CAD libraries (build123d):
it is what lets a UI backend or `tray_generator.py --validate-only`
check a layout without loading the CAD stack. Geometry building lives in
full_tray_generator, which consumes the positions computed here.
"""

if __name__ == "__main__":
  from tray_config import TrayConfig
  from shapes import get_shape
  from calculate_cutout_positions.calculate_linear_cutout_positions import calculate_linear_cutout_positions
  from calculate_cutout_positions.calculate_alternating_cutout_positions import calculate_alternating_cutout_positions
  from calculate_cutout_positions.calculate_manual_cutout_positions import calculate_manual_cutout_positions
else:
  from .tray_config import TrayConfig
  from .shapes import get_shape
  from .calculate_cutout_positions.calculate_linear_cutout_positions import calculate_linear_cutout_positions
  from .calculate_cutout_positions.calculate_alternating_cutout_positions import calculate_alternating_cutout_positions
  from .calculate_cutout_positions.calculate_manual_cutout_positions import calculate_manual_cutout_positions


def calculate_usable_area(
    total_width,
    total_depth,
    rail_width,
    safety_margin,
    tolerance,
    is_double_tray,
):
  usable_area = {}
  usable_area_min = {}
  usable_area_min['x'] = -total_width/2 + \
      rail_width + safety_margin[0]
  usable_area_min['y'] = -total_depth/2 + safety_margin[1] + tolerance/2
  usable_area['min'] = usable_area_min

  usable_area_max = {}
  usable_area_max['x'] = total_width/2 - \
      rail_width - safety_margin[0]
  if is_double_tray:
    usable_area_max['y'] = total_depth/2 - safety_margin[1] - tolerance/2
  else:
    usable_area_max['y'] = 0
  usable_area['max'] = usable_area_max

  return usable_area


def calculate_cutout_positions(
    usable_area,
    sizes,
    edge_offsets,
    tolerance,
    is_double_tray=False,
    force_linear_positions=False,
    min_cutout_spacing=2.0,
    layout_sizes=None,
    nesting='circle',
):
  if len(sizes) == 0:
    return []
  positions = []
  max_y_size = (max(y for _, y in layout_sizes) if layout_sizes
                else max(sizes))
  if max_y_size <= -usable_area['min']['y'] or not is_double_tray or force_linear_positions:
    positions = calculate_linear_cutout_positions(
        usable_area, sizes, edge_offsets, tolerance, is_double_tray,
        min_spacing=min_cutout_spacing, layout_sizes=layout_sizes)
  else:
    positions = calculate_alternating_cutout_positions(
        usable_area, sizes, edge_offsets, tolerance,
        layout_sizes=layout_sizes, nesting=nesting)

  return positions


def resolve_base_shapes(sizes, shapes, default_shape):
  """Resolve per-base shape names to CutoutShape objects and validate
  each size against its shape. `shapes` entries of None (and bases beyond
  the end of the list) use `default_shape`."""
  shape_names = list(shapes) if shapes else []
  while len(shape_names) < len(sizes):
    shape_names.append(None)
  base_shapes = [get_shape(name if name is not None else default_shape)
                 for name in shape_names]
  for i, (shape, size) in enumerate(zip(base_shapes, sizes)):
    try:
      shape.validate_size(size)
    except ValueError as e:
      raise ValueError(f"Base {i + 1}: {e}") from None
  return base_shapes


def compute_layout(
    sizes,
    config=None,
    edge_offsets=None,
    shapes=None,
    placements=None,
):
  """Resolve shapes and compute the cutout positions for a tray.

  With `placements` (a per-base list of {'x', 'edge'} dicts) the bases go
  exactly where the user put them (manual placement); otherwise the
  automatic linear/alternating layout runs. `edge_offsets` is padded with
  zeros to match `sizes`. Returns (base_shapes, positions); raises
  ValueError with a user-facing message when the layout is invalid.
  """
  if config is None:
    config = TrayConfig()

  base_shapes = resolve_base_shapes(sizes, shapes, config.cutout_shape)

  edge_offsets = list(edge_offsets) if edge_offsets else []
  while len(edge_offsets) < len(sizes):
    edge_offsets.append(0)

  usable_area = calculate_usable_area(
      config.total_width,
      config.total_depth,
      config.rail_width,
      config.safety_margin,
      config.tolerance,
      config.is_double_tray,
  )

  layout_sizes = [shape.layout_sizes(size, config.tolerance)
                  for shape, size in zip(base_shapes, sizes)]
  nesting = [shape.nesting for shape in base_shapes]

  if placements is not None:
    positions = calculate_manual_cutout_positions(
        usable_area, sizes, placements, edge_offsets, config.tolerance,
        config.is_double_tray,
        layout_sizes=layout_sizes,
        nesting=nesting)
  else:
    positions = calculate_cutout_positions(
        usable_area, sizes, edge_offsets, config.tolerance,
        config.is_double_tray,
        force_linear_positions=config.force_linear_positions,
        min_cutout_spacing=config.min_cutout_spacing,
        layout_sizes=layout_sizes,
        nesting=nesting)

  return base_shapes, positions
