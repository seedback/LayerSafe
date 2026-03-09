# %% Libraries
from build123d import *
from ocp_vscode import *
import math
import copy
from functions.base_tray_generator import generate_base_tray
from functions.cutout_generator import generate_cutout

# %% User-Adjustable Parameters

total_width = 189.5 # Default: 189.5
total_depth = 104  # Default: 66.0
safety_margin = (14, 0.8)

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

base_tolerance = 0.6
epsilon = 0.001




# %% Main execution

if __name__ == "__main__":
  base_radius = 49.5
  width = base_radius + rail_width*2 + safety_margin[0]
  depth = base_radius * 2 + 4 if base_radius * 2 + 4 > 66 else 66
  tray_compound = generate_base_tray(
    width,
    depth,
    is_double_tray=False,
    epsilon=epsilon
  )
  cutout = (
    generate_cutout(
      base_radius,
      tolerance=base_tolerance,
      cutout_edge_spacing=safety_margin[1],
      epsilon=epsilon
    ).translate((
      -width/2 + rail_width + safety_margin[0]/2,
      -depth/2 + safety_margin[1],
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

  export_stl(tray_compound, "output/tray_" + str(base_radius) + "mm.stl")
  export_step(tray_compound, "output/tray_" + str(base_radius) + "mm.step")

# %%