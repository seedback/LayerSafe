#%%
from build123d import *
from ocp_vscode import *
import math

#%%

def generate_cutout(
  base_diameter,
  tolerance = 1,
  flap_depth = 11.8,
  hinge_diameter = 27.7,
  flap_center_gap=0.2,
  cutout_edge_spacing = .8,
  epsilon = 0.0001
):
  with BuildPart() as normal_base:
    with BuildSketch():
      Circle(base_diameter/2 + tolerance/2, align=(Align.MIN, Align.MIN))
    extrude(amount=5, taper=12.5)
    # Add the slide path for the base
    cross_section_plane = Plane.XZ.offset(-(base_diameter/2 + tolerance/2))
    cross_section_result = section(normal_base.part, cross_section_plane)
    extrude(cross_section_result, (base_diameter/2 + tolerance/2)-flap_depth -flap_center_gap + cutout_edge_spacing)
  
  with BuildPart() as lip_adjustor:
    with Locations((tolerance/2 - base_diameter/2, -base_diameter/2)):
      Cylinder(base_diameter, 6, align=(Align.MIN, Align.MIN))
    # Get the radius cut out of the adjustor
    hinge_radius = hinge_diameter/2
    delta_x = hinge_radius - math.sqrt(hinge_radius*hinge_radius - 1.8*1.8)
    with BuildSketch(Plane.YZ.offset(base_diameter/2 + tolerance/2)) as test:
      with Locations((delta_x, 1.8)):
        Circle(hinge_radius, align=(Align.MAX, Align.CENTER))
    revolve_axis = Axis(origin=(base_diameter/2 + tolerance/2, base_diameter/2, -1.8), direction=(0, 0, 1))
    revolve(axis=revolve_axis, mode=Mode.SUBTRACT)
    # Keep only the part of the lip adjustor that intersects with the flap
    Box((base_diameter/2 + tolerance/2) * 2, flap_depth*2 - cutout_edge_spacing*2 + epsilon, 7, align=(Align.MIN, Align.CENTER, Align.MIN), mode=Mode.INTERSECT)
  
  return_compound = Compound([normal_base.part, lip_adjustor.part]).translate((-tolerance/2,0,0))
  
  return return_compound

# %%

if __name__ == "__main__":
  cutout = generate_cutout(32)

  show( cutout)
#%%