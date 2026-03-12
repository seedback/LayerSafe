# %%
from build123d import *
from ocp_vscode import *
import math
import sys

# %%


def generate_cutout(
    base_diameter,
    tolerance=0.55,
    flap_depth=11.8,
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    cutout_edge_spacing=.8,
    epsilon=0.001
):
  with BuildPart() as normal_base:
    with Locations((0, 0, -epsilon)):
      with BuildSketch():
        c = Circle(base_diameter/2 + tolerance/2,
                  align=(Align.CENTER, Align.CENTER))
      extrude(amount=5, taper=12.5)
      # Add the slide path for the base
      cross_section_result = section(normal_base.part, Plane.XZ)
      e = extrude(cross_section_result, (base_diameter/2 + tolerance/2) -
                  flap_depth - flap_center_gap + epsilon + 1.8)

  with BuildPart() as lip_adjustor_base:
    with Locations((0, -base_diameter*0.75, -epsilon*2)):
      Cylinder(base_diameter, 6, align=(Align.CENTER, Align.CENTER))

  # Get the radius cut out of the adjustor
  hinge_radius = hinge_diameter/2
  delta_x = hinge_radius - math.sqrt(hinge_radius*hinge_radius - 1.8*1.8) -1
  with BuildPart() as lip_adjustor_edge:
    with BuildSketch(Plane.YZ):
      with Locations((-base_diameter/2 - tolerance/2 + delta_x - hinge_radius, 1.8)):
        Circle(hinge_radius, align=(Align.CENTER, Align.CENTER))
    revolve_axis = Axis(origin=(0, -tolerance/2 - epsilon, 0), direction=(0, 0, 1))
    revolve(axis=revolve_axis)
    
  lip_adjustor_base.part -= lip_adjustor_edge.part
  
    # Keep only the part of the lip adjustor that intersects with the flap
  with BuildPart() as lip_box:
    with Locations((0, -base_diameter/2 - tolerance/2 - 1.4, -1)):
      b = Box(
          (base_diameter + 5),
          flap_depth*2 - cutout_edge_spacing + epsilon,
          8,
          align=(Align.CENTER, Align.CENTER, Align.MIN),
      )
  
  lip_adjustor_base.part = lip_adjustor_base.part.intersect(lip_box.part)

  normal_base.part += lip_adjustor_base.part

  # Create flattener
  with BuildPart() as flattener:
    Box(base_diameter + 5, base_diameter + 5, 1, 
        align=(Align.CENTER, Align.CENTER, Align.MAX))
  
  # Subtract flattener using boolean operation
  normal_base.part = normal_base.part - flattener.part

  return_compound = Compound([normal_base.part])

  # try:
  #     show(return_compound, flattener, normal_base, lip_adjustor_base, lip_adjustor_edge, lip_box, alphas=[1, 0.5, 1, 0.5, 0.5])
  # except:
  #   pass

  return return_compound



# %%


if __name__ == "__main__":
  cutout = generate_cutout(50, tolerance=0.55)

# try:
#   show(cutout)
# except:
#   pass
# %%
