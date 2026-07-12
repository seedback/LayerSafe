# %% Libraries
import copy
from build123d import *
from ocp_vscode import *

# calculate_usable_area and calculate_cutout_positions moved to
# layout_engine (the CAD-free layout pipeline) and are re-imported here
# so existing callers keep working.
if __name__ == "__main__":
  from tray_config import TrayConfig
  from base_tray_generator import generate_base_tray
  from layout_engine import (
      calculate_usable_area, calculate_cutout_positions, compute_layout)
else:
  from .tray_config import TrayConfig
  from .base_tray_generator import generate_base_tray
  from .layout_engine import (
      calculate_usable_area, calculate_cutout_positions, compute_layout)

base_tray_storage = {}

# %%


def generate_full_tray(
    sizes,
    config=None,
    edge_offsets=None,
    edge_adjusts=None,
    shapes=None,
    placements=None,
):
  """Generate a tray with cutouts for the given base sizes.

  Each entry in `sizes` is one base: the diameter for circular cutouts,
  the side length for square ones (see functions/shapes.py). `shapes`
  optionally gives each base its own shape name; entries of None (and
  bases beyond the end of the list) use config.cutout_shape, so shapes
  can be mixed in one tray (e.g. one oval among circles). Geometry and
  layout settings come from `config` (a TrayConfig); per-base fine-tuning
  comes from edge_offsets / edge_adjusts, which are padded with zeros to
  match the length of `sizes`. `placements` (a per-base list of
  {'x', 'edge'} dicts) switches from the automatic layout to manual
  placement — see layout_engine.compute_layout.
  """
  if config is None:
    config = TrayConfig()

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

  base_shapes, positions = compute_layout(
      sizes, config, edge_offsets=edge_offsets, shapes=shapes,
      placements=placements)

  # Create a base tray if one of the given dimmension doesn't exist
  # Grab a deep copy of the tray from storage
  if not storage_key in base_tray_storage:
    base_tray_storage[storage_key] = generate_base_tray(config)
  tray_compound = copy.deepcopy(base_tray_storage[storage_key])

  cutouts_list = []

  for position in positions:
    # Layouts may reorder the bases (the linear layout splits them into
    # two rows), so per-base inputs are looked up by the original index.
    idx = position['index']
    cutout = base_shapes[idx].build(
        position['size'],
        tolerance=config.tolerance,
        flap_depth=config.flap_depth,
        hinge_diameter=config.hinge_diameter,
        flap_center_gap=config.flap_center_gap,
        edge_margin=config.safety_margin[1],
        edge_adjust=edge_adjusts[idx],
        edge_offset=edge_offsets[idx],
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
