# %% Libraries
import copy
import math
from build123d import *
from ocp_vscode import *

if __name__ == "__main__":
  from base_tray_generator import generate_base_tray
  from cutout_generator import generate_cutout
  from calculate_cutout_positions.calculate_linear_cutout_positions import *
  from calculate_cutout_positions.calculate_alternating_cutout_positions import *
else:
  from .base_tray_generator import generate_base_tray
  from .cutout_generator import generate_cutout
  from .calculate_cutout_positions.calculate_linear_cutout_positions import *
  from .calculate_cutout_positions.calculate_alternating_cutout_positions import *

base_tray_storage = {}


def calculate_usable_area(
    total_width,
    total_depth,
    rail_width,
    safety_margin,
    is_double_tray,
    tolerance
):
  usable_area = {}
  usable_area_min = {}
  usable_area_min['x'] = -total_width/2 + \
      rail_width + tolerance + safety_margin[0]
  usable_area_min['y'] = -total_depth/2 + tolerance + safety_margin[1]
  usable_area['min'] = usable_area_min

  usable_area_max = {}
  usable_area_max['x'] = total_width/2 - \
      rail_width - tolerance - safety_margin[0]
  if is_double_tray:
    usable_area_max['y'] = total_depth/2 - tolerance - safety_margin[1]
  else:
    usable_area_max['y'] = 0
  usable_area['max'] = usable_area_max

  return usable_area


def calculate_cutout_positions(
    usable_area,
    diameters,
    is_double_tray=False,
):
  if len(diameters) == 0:
    return []
  positions = []
  max_diameter = max(diameters)
  if max_diameter < -usable_area['min']['y'] or not is_double_tray:
    positions = calculate_linear_cutout_positions(
        usable_area, diameters, is_double_tray)
  else:
    positions = calculate_alternating_cutout_positions(usable_area, diameters)

  return positions

# %%


def generate_full_tray(
    diameters=[],
    safety_margin=(6.5, 0.4),
    total_width=189.5,
    total_depth=66.0,
    floor_thickness=0.8,
    base_heigth=4.2,
    rail_height=8.4,
    rail_width=4.8,
    flap_center_gap=0.2,
    flap_depth=11.8,
    hinge_width=2.8,
    hinge_height=3.6,
    hinge_depth=17.5,
    hinge_pin_radius=1.4,
    hinge_pin_length=3,
    bottom_chamfer=0.4,
    hinge_lock_radius=2,
    hinge_lock_offset=0.5,
    hinge_lock_depth=8.3,
    is_double_tray=False,
    epsilon=0.001,
    tolerance=0.55,
    hinge_diameter=27.7,
    cutout_edge_spacing=.4,
):
  storage_key = ((total_width, total_depth), is_double_tray)

  # Create a base tray if one of the given dimmension doesn't exist
  # Grab a deep copy of the tray from storage
  if not storage_key in base_tray_storage:
    temp_tray = generate_base_tray(
        total_width,
        total_depth,
        floor_thickness,
        base_heigth,
        rail_height,
        rail_width,
        flap_center_gap,
        flap_depth,
        hinge_width,
        hinge_height,
        hinge_depth,
        hinge_pin_radius,
        hinge_pin_length,
        bottom_chamfer,
        hinge_lock_radius,
        hinge_lock_offset,
        hinge_lock_depth,
        is_double_tray,
        epsilon
    )
    base_tray_storage[storage_key] = temp_tray
  tray_compound = copy.deepcopy(base_tray_storage[storage_key])

  usable_area = calculate_usable_area(
      total_width,
      total_depth,
      rail_width,
      safety_margin,
      is_double_tray,
      tolerance
  )

  positions = calculate_cutout_positions(
      usable_area, diameters, is_double_tray)

  cutouts_list = []

  for position in positions:
    cutout = (generate_cutout(
        position['diameter'],
        tolerance,
        flap_depth,
        hinge_diameter,
        flap_center_gap,
        safety_margin[1],
        epsilon
    ))

    # Rotate 180 degrees if flipped (for top edge circles)
    if position['flipped']:
      cutout = cutout.rotate(Axis.Z, 180)

    cutout = cutout.translate((position['x'], position['y'], floor_thickness))

    cutouts_list.append(cutout)

  if cutouts_list:
    cutouts = Compound(cutouts_list)
    tray_compound -= cutouts

  return tray_compound, cutouts_list

# %%


if __name__ == "__main__":
  tray_compound, cuttout_list = generate_full_tray(
      [39.3, 39.3, 39.3, 39.3, 39.3, ],
      is_double_tray=True,
  )

  show(tray_compound, cuttout_list)

  export_stl(tray_compound, "../output/test_RGG_tray.stl")
  export_step(tray_compound, "../output/test_RGG_tray.step")

# %%
