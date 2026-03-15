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
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    cutout_edge_spacing=.8,
    lip_offset = 0,
    epsilon=0.001
):
  with BuildPart() as normal_base:
    with BuildSketch():
      c = Circle(base_diameter/2 + tolerance/2,
                  align=(Align.CENTER, Align.CENTER))
    extrude(amount=6, taper=12.5)
    extrude(c, amount=-6, taper=-12.5)
    # # Add the slide path for the base
    if(base_diameter/2 > flap_depth-cutout_edge_spacing):
      cross_section_result = section(normal_base.part, Plane.XZ)
      e = extrude(cross_section_result, (base_diameter/2 + tolerance/2) -
                  (flap_depth - cutout_edge_spacing) - flap_center_gap + epsilon)
  
  normal = copy.deepcopy(normal_base.part)
  
  normal_base.part = normal_base.part.translate((0,0,-epsilon))
  
  if not lip_offset == 0:
    lip_offseter = normal_base.part.translate((0,lip_offset,0))
    normal_base.part = normal_base.part.intersect(lip_offseter)
    
  if isinstance(normal_base.part, ShapeList):
    normal_base.part = normal_base.part[0]

  with BuildPart() as lip_adjustor_base:
    with Locations((0, -base_diameter*0.75, -epsilon*2)):
      Cylinder(base_diameter, 6, align=(Align.CENTER, Align.CENTER))

  # Get the radius cut out of the adjustor
  hinge_radius = hinge_diameter/2
  delta_x = hinge_radius - \
      math.sqrt(hinge_radius*hinge_radius - math.pow(2 + epsilon, 2))
  
  with BuildPart() as lip_adjustor_edge:
    with BuildSketch(Plane.YZ):
      with Locations(( -base_diameter/2 - tolerance/2 + delta_x - hinge_radius, 2)):
        Circle(hinge_radius, align=(Align.CENTER, Align.CENTER))
    revolve_axis = Axis(
        origin=(0, -tolerance/2  - epsilon, 0), direction=(0, 0, 1))
    revolve(axis=revolve_axis)
  
  lip_adjustor_edge.part = lip_adjustor_edge.part.translate((0,lip_offset,0))

  lip_adjustor_base.part -= lip_adjustor_edge.part

  # Keep only the part of the lip adjustor that intersects with the flap
  with BuildPart() as lip_box:
    with Locations((0, lip_offset - base_diameter/2 - tolerance/2, -1)):
      b = Box(
          (base_diameter + 5),
          (flap_depth - cutout_edge_spacing + epsilon)*2,
          8,
          align=(Align.CENTER, Align.CENTER, Align.MIN),
      )

  lip_adjustor_base.part = lip_adjustor_base.part.intersect(lip_box.part)

  # Convert ShapeList to Compound if needed
  if isinstance(lip_adjustor_base.part, ShapeList):
    lip_adjustor_base.part = lip_adjustor_base.part[0]

  normal_base.part += lip_adjustor_base.part

  # Create flattener
  with BuildPart() as flattener:
    Box(base_diameter + 5, base_diameter + 5, 5,
        align=(Align.CENTER, Align.CENTER, Align.MIN))

  # Subtract flattener using boolean operation
  normal_base.part = normal_base.part.intersect(flattener.part)
  
  # Convert normal_base from ShapeList to Shape if necessary
  if isinstance(normal_base.part, ShapeList):
    normal_base.part = normal_base.part[0]

  # # Handle case where subtraction returns a ShapeList
  return_compound = Compound([normal_base.part])

  # show(
  #     return_compound, flattener, normal, lip_adjustor_base,
  #     lip_adjustor_edge, lip_box, c, lip_box.faces().sort_by(Axis.Z)[0].
  #     center(),
  #     alphas=[1, 0.5, 1, 0.5, 0.5],
  #     names=['return', 'flat', 'normal', 'lip_base', 'lip_edge', 'lip_box',
  #            'circle', 'lip_box_center'])

  return return_compound


# %%

if __name__ == "__main__":
  cutout = generate_cutout(32, tolerance=0.55, lip_offset=0)
  show(cutout)
# %%
