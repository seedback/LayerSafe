# %% Libraries
from build123d import *
from ocp_vscode import *
import math
import copy
import base_tray_generator
from cutout_generator import generate_cutout

# %% User-Adjustable Parameters

total_width = 189.5 # Default: 189.5
total_depth = 66.0

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

cutout_edge_spacing = 0.8




# %% Main execution

if __name__ == "__main__":
  base_radius = 31.6
  width = base_radius + rail_width*2 + 8
  base_center_part, base_flap_part = base_tray_generator.generate_base_tray(width, is_double_tray=True)
  cutout = generate_cutout(base_radius).translate((-width/2 + rail_width + 4, -total_depth/2 + cutout_edge_spacing, floor_thickness))

  base_center_part.part -= cutout
  base_flap_part.part -= cutout
  
  cutout = mirror(cutout, Plane.XZ)
  
  base_center_part.part -= cutout
  base_flap_part.part -= cutout

  show(base_center_part, base_flap_part, cutout)

#%%
if __name__ == "__main__":
  export_compound = Compound([base_center_part.part, base_flap_part.part])

  show(export_compound, base_center_part, base_flap_part)

  export_stl(export_compound, "tray.stl")
  export_step(export_compound, "tray.step")

# %%