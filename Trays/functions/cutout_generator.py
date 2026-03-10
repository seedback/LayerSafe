# %%
from build123d import *
from ocp_vscode import *
import math

# %%


def generate_cutout(
    base_diameter,
    tolerance=0.6,
    flap_depth=11.8,
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    cutout_edge_spacing=.8,
    epsilon=0.001
):
  with BuildPart() as normal_base:
    with BuildSketch():
      c = Circle(base_diameter/2 + tolerance/2,
                 align=(Align.CENTER, Align.CENTER))
    extrude(amount=5, taper=12.5)
    # Add the slide path for the base
    cross_section_result = section(normal_base.part, Plane.XZ)
    e = extrude(cross_section_result, (base_diameter/2 + tolerance/2) -
                flap_depth - flap_center_gap + cutout_edge_spacing)
  normal_base.part = normal_base.part.translate((0, 0, -epsilon))

  with BuildPart() as lip_adjustor:
    with Locations((0, -base_diameter/2)):
      Cylinder(base_diameter, 6, align=(Align.CENTER, Align.CENTER))
    # Get the radius cut out of the adjustor
    hinge_radius = hinge_diameter/2
    delta_x = hinge_radius - math.sqrt(hinge_radius*hinge_radius - 1.8*1.8)
    with BuildSketch(Plane.YZ) as test:
      with Locations((-base_diameter/2 - tolerance/2 + delta_x - hinge_radius, 1.8)):
        Circle(hinge_radius, align=(Align.CENTER, Align.CENTER))
    revolve_axis = Axis(origin=(0, -tolerance/2, 0), direction=(0, 0, 1))
    r = revolve(axis=revolve_axis, mode=Mode.SUBTRACT)
    # Keep only the part of the lip adjustor that intersects with the flap
    with Locations((0, -base_diameter/2 - tolerance/2)):
      b = Box(
          (base_diameter/2 + tolerance/2) * 2,
          flap_depth*2 - cutout_edge_spacing*2 + epsilon,
          7,
          align=(Align.CENTER, Align.CENTER, Align.MIN),
          mode=Mode.INTERSECT
      )

  lip_adjustor.part = lip_adjustor.part.translate((0, 0, -epsilon*2))

  normal_base.part += lip_adjustor.part

  with BuildPart() as flattener:
    flat = Box(base_diameter+tolerance*2, base_diameter+tolerance *
               2, 1, align=(Align.CENTER, Align.CENTER, Align.MAX))
  normal_base.part -= flattener.part

  return_compound = Compound(
      [normal_base.part])  # .translate((-tolerance/2, 0, 0))

  return return_compound

# %%


if __name__ == "__main__":
  cutout = generate_cutout(32)

  show(cutout)
# %%
