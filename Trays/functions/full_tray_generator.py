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
    diameters,
    edge_offsets,
    tolerance,
    is_double_tray=False,
):
  if len(diameters) == 0:
    return []
  max_diameter = max(diameters)
  if max_diameter <= -usable_area['min']['y'] or not is_double_tray:
    print("linear")
    return calculate_linear_cutout_positions(
        usable_area, diameters, edge_offsets, tolerance, is_double_tray)
  else:
    print("alternating")
    return calculate_alternating_cutout_positions(
        usable_area, diameters, edge_offsets, tolerance)

# %%


def generate_full_tray(
    diameters=[],
    safety_margin=(6.5, 0.8),
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
    edge_offsets=[],
    edge_adjusts=[],
    is_double_tray=False,
    epsilon=0.001,
    tolerance=0.55,
    hinge_diameter=27.7,
):
  storage_key = ((total_width, total_depth), is_double_tray)

  # Pad edge_offsets with zeros to match diameters length
  edge_offsets = list(edge_offsets) if edge_offsets else []
  while len(edge_offsets) < len(diameters):
    edge_offsets.append(0)

  # Pad edge_adjusts with zeros to match diameters length
  edge_adjusts = list(edge_adjusts) if edge_adjusts else []
  while len(edge_adjusts) < len(diameters):
    edge_adjusts.append(0)

  # Create a base tray if one of the given dimmension doesn't exist
  # Grab a deep copy of the tray from storage
  if not storage_key in base_tray_storage:
    temp_tray, hinge_pin_height = generate_base_tray(
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
    base_tray_storage[storage_key] = (temp_tray, hinge_pin_height)
  tray_data = copy.deepcopy(base_tray_storage[storage_key])
  tray_compound = tray_data[0]
  hinge_pin_height = tray_data[1]

  usable_area = calculate_usable_area(
      total_width,
      total_depth,
      rail_width,
      safety_margin,
      tolerance,
      is_double_tray,
  )

  positions = calculate_cutout_positions(
      usable_area, diameters, edge_offsets, tolerance, is_double_tray)

  cutouts_list = []

  for i, position in enumerate(positions.joints):
    cutout = (generate_cutout(
        diameters[i],
        tolerance,
        flap_depth,
        hinge_diameter,
        flap_center_gap,
        safety_margin[1],
        edge_adjusts[i],
        hinge_pin_height,
        12.5,
        epsilon
    ))
    
    print("showing")
    show(cutout.children[0], render_joints=True)
    print("showed")

    print(cutout.joints)
    positions.joints[f"{i}"].connect_to(cutout.children[0].joints["Center"])
    tray_compound -= cutout.children[0]
    
    cutouts_list.append(cutout)
    print("Got here2")
    

  return tray_compound, cutouts_list, positions

# %%


if __name__ == "__main__":
  # tray_compound, cutout_list = generate_full_tray(
  #     [49.6],
  #     is_double_tray=False,
  #     total_depth=110,
  #     total_width=80,
  #     edge_offsets=[.1]
  # )

  tray_compound, cutouts_list, positions = generate_full_tray(
      [32,32,32,32,32,32,32,32,32,32],
      is_double_tray=True,
      safety_margin=(6.5, 0.4),
      # edge_offsets=[5, 5],
      edge_adjusts=[0.3],
      floor_thickness=.8
  )
  
  print("Got here")

  show(tray_compound, cutouts_list, positions, render_joints=True)

  # export_stl(tray_compound, "../output/test_RGG_tray.stl")
  # export_step(tray_compound, "../output/test_RGG_tray.step")

# %%
