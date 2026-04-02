# %%
from build123d import *
from ocp_vscode import *
import math
import copy

# %%


def generate_cutout(
    base_diameter,
    tolerance=0.55,
    flap_depth=11.8,
    hinge_diameter=27.5,
    flap_middle_gap=0.2,
    cutout_edge_spacing=.8,
    lip_offset=0,
    hinge_pin_height=1.2,
    taper_angle=12.5,
    epsilon=0.001
):
  total_diameter = (base_diameter + tolerance)
  total_radius = total_diameter/2
  
  with BuildPart() as base_builder:
    with BuildSketch(Plane.XY):
      Circle(total_radius)
    extrude(amount=6, taper=taper_angle)
    RigidJoint("Track", joint_location=Location((-total_radius, 0, 0)))
    RigidJoint("LipShaper", joint_location=Location((0, -total_radius+epsilon, 0)))
  cutout = base_builder.part
  
  with BuildPart() as track_builder:
    cross_section = section(base_builder.part, Plane.XZ)
    extrude(cross_section, total_radius - flap_depth + cutout_edge_spacing - flap_middle_gap + epsilon)
    RigidJoint("Base", joint_location=Location((-total_radius, 0, 0)))
  cutout.joints["Track"].connect_to(track_builder.joints["Base"])
  cutout += track_builder.part
  
  with BuildPart() as lip_shaper_builder:
    revolve_axis = Axis(origin=(0, total_radius + hinge_diameter/2 - lip_offset - tolerance, 0), direction=(0, 0, 1))
    with BuildSketch(Plane.YZ) as revolve_sketch:
      Circle(hinge_diameter/2)
    revolve(axis=revolve_axis)
    y_adjust = math.sqrt((hinge_diameter/2)**2 - hinge_pin_height**2)
    RigidJoint("Base", joint_location=Location((0, y_adjust, -hinge_pin_height)))
  cutout.joints["LipShaper"].connect_to(lip_shaper_builder.joints["Base"])
  
  with BuildPart() as lip_box_builder:
    box_depth = flap_depth - cutout_edge_spacing + epsilon
    with Locations((0,0,3)):
      Box(total_diameter*2, box_depth * 2, 6)
    RigidJoint("Base")
  cutout.joints["LipShaper"].connect_to(lip_box_builder.joints["Base"])
  lip = lip_box_builder.part - lip_shaper_builder.part
  lip = (lip.solids()<Axis.Y)[:1]
  cutout += lip
  
  RigidJoint("Center", cutout)
  return Compound(children=[cutout], label=f"cutout {base_diameter}mm")
  
#%%
if __name__ == "__main__":
  cutout = generate_cutout(40, lip_offset=0.1)
  show(cutout, render_joints=True)
# %%

    