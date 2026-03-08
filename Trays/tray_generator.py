# %% Libraries
from build123d import *
from ocp_vscode import *
import math
import copy
from functions.base_tray_generator import generate_base_tray
from functions.cutout_generator import generate_cutout

# %% User-Adjustable Parameters

total_width = 189.5 # Default: 189.5
total_depth = 67.0  # Default: 66.0

floor_thickness = 0.4
base_heigth = 4.2
rail_height = 8.4
rail_width = 4.8

flap_center_gap = 0.2
flap_depth = 11.8

hinge_width = 2.8
hinge_height = 3.6
# Calculated from the edge of the center, not the flap
hinge_depth = 17.5
hinge_pin_radius = 1.4
hinge_pin_length = 3
bottom_chamfer = 0.4

hinge_lock_radius = 3.5
hinge_lock_offset = 0.4
hinge_lock_depth = 8.3

is_double_tray = False

cutout_edge_spacing = 0.4

base_tolerance = 0.5
epsilon = 0.0001




# %% Main execution

if __name__ == "__main__":
  base_radius = 31.6
  width = base_radius + rail_width*2 + 8
  tray_compound = generate_base_tray(
    width,
    is_double_tray=False,
    epsilon=epsilon
  )
  cutout = (
    generate_cutout(
      base_radius,
      tolerance=base_tolerance,
      cutout_edge_spacing=cutout_edge_spacing,
      epsilon=epsilon
    ).translate((
      -width/2 + rail_width + 4,
      -total_depth/2 + cutout_edge_spacing,
      0,
      floor_thickness,
    ))
  )

  tray_compound -= cutout
  # base_flap_part.part -= cutout
  
  # cutout = mirror(cutout, Plane.XZ)
  
  # tray_compound -= cutout
  # base_flap_part.part -= cutout

  show(tray_compound, cutout)

#%%
if __name__ == "__main__":
  # show(export_compound, base_center_part, base_flap_part)

  export_stl(tray_compound, "output/tray.stl")
  export_step(tray_compound, "output/tray.step")

# %%