# %%
from build123d import *
from ocp_vscode import *
import math

# Wall draft for the cutout sides. NOTE: circle and prismatic cutouts
# currently use different draft angles and heights (12.5deg/6mm vs
# 5deg/5mm); unify these once it is confirmed the difference is not a
# deliberate fit choice.
CIRCLE_EXTRUDE_HEIGHT = 6
CIRCLE_TAPER = 12.5
PRISM_EXTRUDE_HEIGHT = 5
PRISM_TAPER = 5

# %%


def generate_cutout(
    size,
    tolerance=0.55,
    flap_depth=11.8,
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    edge_margin=0.8,
    edge_adjust=0,
    edge_offset=0,
    taper_angle=None,
    epsilon=0.001
):
  """Build the negative shape for one circular base cutout.

  `size` is the base diameter. edge_margin is the y safety margin between
  the cutout and the tray edge; edge_adjust (--edge-adjusts) grows the
  flat spot below the curved lip; edge_offset (--edge-offsets) shifts the
  lip to reduce the base depth. taper_angle is the wall angle in degrees
  from vertical (None uses CIRCLE_TAPER).
  """
  taper = CIRCLE_TAPER if taper_angle is None else taper_angle

  with BuildPart() as normal_base:
    with BuildSketch():
      c = Circle(size/2 + tolerance/2,
                  align=(Align.CENTER, Align.CENTER))
    extrude(amount=CIRCLE_EXTRUDE_HEIGHT, taper=taper)
    extrude(c, amount=-CIRCLE_EXTRUDE_HEIGHT, taper=-taper)
    # Add the slide path for the base
    if(size/2 > flap_depth-edge_margin):
      cross_section_result = section(normal_base.part, Plane.XZ)
      extrude(cross_section_result, (size/2 + tolerance/2) -
              (flap_depth - edge_margin) - flap_center_gap + epsilon)

  normal_base.part = normal_base.part.translate((0,0,-epsilon))

  if not edge_offset == 0:
    edge_offseter = normal_base.part.translate((0,edge_offset,0))
    normal_base.part = normal_base.part.intersect(edge_offseter)

  if isinstance(normal_base.part, ShapeList):
    normal_base.part = normal_base.part[0]

  with BuildPart() as lip_adjustor_base:
    with Locations((0, -size*0.75, -epsilon*2)):
      Cylinder(size, 6, align=(Align.CENTER, Align.CENTER, Align.CENTER))

  # Get the radius cut out of the adjustor
  hinge_radius = hinge_diameter/2 - edge_margin
  delta_x = hinge_radius - \
      math.sqrt(math.pow(hinge_radius, 2) - math.pow(2 - edge_adjust + epsilon, 2))

  with BuildPart() as lip_adjustor_edge:
    with BuildSketch(Plane.YZ):
      with Locations(( -size/2 - tolerance/2 + delta_x - hinge_radius, 2 - edge_adjust)):
        Circle(hinge_radius, align=(Align.CENTER, Align.CENTER))
    revolve_axis = Axis(
        origin=(0, -tolerance/2  - epsilon, 0), direction=(0, 0, 1))
    revolve(axis=revolve_axis)

  lip_adjustor_edge.part = lip_adjustor_edge.part.translate((0,edge_offset,0))

  lip_adjustor_base.part -= lip_adjustor_edge.part

  # Keep only the part of the lip adjustor that intersects with the flap
  with BuildPart() as lip_box:
    with Locations((0, edge_offset - size/2 - tolerance/2, -1)):
      b = Box(
          (size + 5),
          (flap_depth - edge_margin + epsilon)*2,
          8,
          align=(Align.CENTER, Align.CENTER, Align.MIN),
      )

  lip_adjustor_base.part = lip_adjustor_base.part.intersect(lip_box.part)

  # Unwrap ShapeList or dim-less Compound to get the underlying Solid
  if isinstance(lip_adjustor_base.part, ShapeList):
    lip_adjustor_base.part = lip_adjustor_base.part[0]
  elif isinstance(lip_adjustor_base.part, Compound) and lip_adjustor_base.part._dim is None:
    children = list(lip_adjustor_base.part)
    if children:
      lip_adjustor_base.part = children[0]

  normal_base.part += lip_adjustor_base.part

  # Create flattener
  with BuildPart() as flattener:
    Box(size + 5, size + 5, 5,
        align=(Align.CENTER, Align.CENTER, Align.MIN))

  # Subtract flattener using boolean operation
  normal_base.part = normal_base.part.intersect(flattener.part)

  # Convert normal_base from ShapeList to Shape if necessary
  if isinstance(normal_base.part, ShapeList):
    normal_base.part = normal_base.part[0]

  return Compound([normal_base.part])


# %%


def _prismatic_cutout(
    profile_fn,
    slide_path_length,
    flatten_width,
    flatten_depth,
    taper_angle=None,
    epsilon=0.001,
):
  """Shared pipeline for straight-walled (prismatic) cutouts such as
  squares and future hexes: extrude the 2D profile with a wall draft, add
  the slide path toward the flap, then remove everything below the floor
  plane. The caller supplies the profile sketch via `profile_fn`;
  taper_angle is the wall angle in degrees from vertical (None uses
  PRISM_TAPER).
  """
  taper = PRISM_TAPER if taper_angle is None else taper_angle

  with BuildPart() as normal_base:
    with BuildSketch():
      profile_fn()
    extrude(amount=PRISM_EXTRUDE_HEIGHT, taper=taper)
    # Add the slide path for the base (same approach as circular cutout)
    cross_section_result = section(normal_base.part, Plane.XZ)
    extrude(cross_section_result, slide_path_length)
  normal_base.part = normal_base.part.translate((0, 0, -epsilon))

  with BuildPart() as flattener:
    Box(flatten_width, flatten_depth, 1,
        align=(Align.CENTER, Align.CENTER, Align.MAX))
  normal_base.part -= flattener.part

  return Compound([normal_base.part])


def generate_square_cutout(
    size,
    tolerance=0.55,
    flap_depth=11.8,
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    edge_margin=0.8,
    edge_adjust=0,
    edge_offset=0,
    taper_angle=None,
    epsilon=0.001
):
  """Build the negative shape for one square base cutout.

  `size` is the side length. taper_angle is the wall angle in degrees from
  vertical (None uses PRISM_TAPER). edge_adjust (--edge-adjusts) and
  edge_offset (--edge-offsets) are accepted for signature parity with
  generate_cutout; the square cutout geometry does not use them.
  """
  half_side = size / 2 + tolerance / 2

  return _prismatic_cutout(
      profile_fn=lambda: Rectangle(size + tolerance, size + tolerance,
                                   align=(Align.CENTER, Align.CENTER)),
      slide_path_length=(half_side - flap_depth - flap_center_gap
                         + edge_margin),
      flatten_width=size + tolerance * 2,
      flatten_depth=size + tolerance * 2,
      taper_angle=taper_angle,
      epsilon=epsilon,
  )


# %%


if __name__ == "__main__":
  cutout = generate_cutout(49.6, tolerance=0.55, edge_offset=0.1, edge_adjust=-1)
  show(cutout)
# %%
