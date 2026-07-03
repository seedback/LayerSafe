# %% Libraries
import copy
import math
from build123d import *
from ocp_vscode import *

if __name__ == "__main__":
  from tray_config import TrayConfig
  from shapes import get_shape
  from base_tray_generator import generate_base_tray
  from calculate_cutout_positions.calculate_linear_cutout_positions import calculate_linear_cutout_positions
  from calculate_cutout_positions.calculate_alternating_cutout_positions import calculate_alternating_cutout_positions
else:
  from .tray_config import TrayConfig
  from .shapes import get_shape
  from .base_tray_generator import generate_base_tray
  from .calculate_cutout_positions.calculate_linear_cutout_positions import calculate_linear_cutout_positions
  from .calculate_cutout_positions.calculate_alternating_cutout_positions import calculate_alternating_cutout_positions

base_tray_storage = {}


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
        usable_area, sizes, edge_offsets, tolerance)

  return positions

# %%


def generate_full_tray(
    sizes,
    config=None,
    edge_offsets=None,
    edge_adjusts=None,
):
  """Generate a tray with cutouts for the given base sizes.

  Each entry in `sizes` is one base: the diameter for circular cutouts,
  the side length for square ones (see functions/shapes.py). Geometry and
  layout settings come from `config` (a TrayConfig); per-base fine-tuning
  comes from edge_offsets / edge_adjusts, which are padded with zeros to
  match the length of `sizes`.
  """
  if config is None:
    config = TrayConfig()

  shape = get_shape(config.cutout_shape)
  for size in sizes:
    shape.validate_size(size)

  storage_key = ((config.total_width, config.total_depth),
                 config.is_double_tray)

  # Pad edge_offsets with zeros to match sizes length
  edge_offsets = list(edge_offsets) if edge_offsets else []
  while len(edge_offsets) < len(sizes):
    edge_offsets.append(0)

  # Pad edge_adjusts with zeros to match sizes length
  edge_adjusts = list(edge_adjusts) if edge_adjusts else []
  while len(edge_adjusts) < len(sizes):
    edge_adjusts.append(0)

  # Create a base tray if one of the given dimmension doesn't exist
  # Grab a deep copy of the tray from storage
  if not storage_key in base_tray_storage:
    base_tray_storage[storage_key] = generate_base_tray(config)
  tray_compound = copy.deepcopy(base_tray_storage[storage_key])

  usable_area = calculate_usable_area(
      config.total_width,
      config.total_depth,
      config.rail_width,
      config.safety_margin,
      config.tolerance,
      config.is_double_tray,
  )

  # Shapes that cannot guarantee clearance under the alternating layout's
  # nesting math (see functions/shapes.py) are kept on the linear layout.
  use_linear_positions = (config.force_linear_positions
                          or not shape.supports_alternating)
  positions = calculate_cutout_positions(
      usable_area, sizes, edge_offsets, config.tolerance,
      config.is_double_tray,
      force_linear_positions=use_linear_positions,
      min_cutout_spacing=config.min_cutout_spacing,
      layout_sizes=[shape.layout_sizes(size, config.tolerance)
                    for size in sizes])

  cutouts_list = []

  for i, position in enumerate(positions):
    cutout = shape.build(
        position['size'],
        tolerance=config.tolerance,
        flap_depth=config.flap_depth,
        hinge_diameter=config.hinge_diameter,
        flap_center_gap=config.flap_center_gap,
        edge_margin=config.safety_margin[1],
        edge_adjust=edge_adjusts[i],
        edge_offset=edge_offsets[i],
        taper_angle=config.taper_angle,
        flap_clearance=config.flap_clearance,
        epsilon=config.epsilon,
    )

    # Rotate 180 degrees if flipped (for top edge circles)
    if position['flipped']:
      cutout = cutout.rotate(Axis.Z, 180)

    cutout = cutout.translate(
        (position['x'], position['y'], config.floor_thickness))

    cutouts_list.append(cutout)

  if cutouts_list:
    cutouts = Compound(cutouts_list)
    tray_compound = tray_compound.cut(cutouts)

  return tray_compound, cutouts_list

# %%


if __name__ == "__main__":
  tray_compound, cutout_list = generate_full_tray(
      [25, 40, 40, 25, 25, 25, 25],
      TrayConfig(is_double_tray=True, force_linear_positions=True),
  )

  show(tray_compound, cutout_list)

  # export_stl(tray_compound, "../output/test_RGG_tray.stl")
  # export_step(tray_compound, "../output/test_RGG_tray.step")

# %%
