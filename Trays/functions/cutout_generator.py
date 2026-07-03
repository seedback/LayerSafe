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
    flap_clearance=0,
    epsilon=0.001
):
  """Build the negative shape for one circular base cutout.

  `size` is the base diameter. edge_margin is the y safety margin between
  the cutout and the tray edge; edge_adjust (--edge-adjusts) grows the
  flat spot below the curved lip; edge_offset (--edge-offsets) shifts the
  lip to reduce the base depth. taper_angle is the wall angle in degrees
  from vertical (None uses CIRCLE_TAPER). flap_clearance is accepted for
  signature parity: the circular cutout's revolved lip relief already
  provides the flap rotation clearance, so it is not used here.
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


def _unwrap_boolean_result(shape):
  """Boolean ops occasionally return a ShapeList or a dimension-less
  Compound instead of a plain solid, which then breaks follow-up unions.
  Unwrap to the underlying solid(s), unioning if there are several;
  returns None for an empty result."""
  if isinstance(shape, ShapeList):
    children = list(shape)
  elif isinstance(shape, Compound) and shape._dim is None:
    children = list(shape)
  else:
    return shape
  if not children:
    return None
  result = children[0]
  for child in children[1:]:
    result = result + child
  return result


def _prismatic_cutout(
    profile_fn,
    slide_path_length,
    flatten_width,
    flatten_depth,
    taper_angle=None,
    flap_clearance=0,
    epsilon=0.001,
):
  """Shared pipeline for straight-walled (prismatic) cutouts such as
  squares and hexes: extrude the 2D profile with a wall draft, add the
  slide path toward the flap, then remove everything below the floor
  plane. The caller supplies the profile sketch via `profile_fn`;
  taper_angle is the wall angle in degrees from vertical (None uses
  PRISM_TAPER).

  flap_clearance widens the cutout sideways (per side) in the region in
  front of the slide path -- the part cut into the rotating flap -- so
  the flap's cutout edge sweeps past the seated base when closing
  instead of clipping it. The pocket that grips the base is unaffected.
  (Circle cutouts get this clearance from their revolved lip relief
  instead.)
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

  if flap_clearance > 0:
    # Union of the cutout shifted +-flap_clearance along x: for an
    # x-convex profile this is exactly the cutout widened by
    # flap_clearance per side, walls and taper preserved.
    widened = (normal_base.part
               + normal_base.part.translate((-flap_clearance, 0, 0))
               + normal_base.part.translate((flap_clearance, 0, 0)))
    # Keep the widening only from the end of the slide path forward
    # (the flap-center gap and the flap itself).
    with BuildPart() as flap_region:
      with Locations((0, -slide_path_length, 0)):
        Box(
            flatten_width + flap_clearance * 2 + 2,
            flatten_depth * 2,
            (PRISM_EXTRUDE_HEIGHT + 1) * 2,
            align=(Align.CENTER, Align.MAX, Align.CENTER),
        )
    relief = _unwrap_boolean_result(widened.intersect(flap_region.part))
    if relief is not None:
      normal_base.part += relief

  with BuildPart() as flattener:
    Box(flatten_width + flap_clearance * 2, flatten_depth, 1,
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
    flap_clearance=0,
    epsilon=0.001
):
  """Build the negative shape for one square base cutout.

  `size` is the side length. taper_angle is the wall angle in degrees from
  vertical (None uses PRISM_TAPER); flap_clearance widens the flap's part
  of the cutout so it can rotate closed past a seated base. edge_adjust
  (--edge-adjusts) and edge_offset (--edge-offsets) are accepted for
  signature parity with generate_cutout; the square cutout geometry does
  not use them.
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
      flap_clearance=flap_clearance,
      epsilon=epsilon,
  )


def generate_hex_cutout(
    size,
    tolerance=0.55,
    flap_depth=11.8,
    hinge_diameter=27.7,
    flap_center_gap=0.2,
    edge_margin=0.8,
    edge_adjust=0,
    edge_offset=0,
    taper_angle=None,
    flap_clearance=0,
    epsilon=0.001
):
  """Build the negative shape for one hexagonal base cutout.

  `size` is measured across the flats. The hex is oriented with flats
  facing the tray edges (corners pointing along x), so the front flat
  rests against the edge lip like a square's side does. taper_angle is
  the wall angle in degrees from vertical (None uses PRISM_TAPER);
  flap_clearance widens the flap's part of the cutout so it can rotate
  closed past a seated base. edge_adjust (--edge-adjusts) and edge_offset
  (--edge-offsets) are accepted for signature parity with
  generate_cutout; the hex cutout geometry does not use them.
  """
  half_flats = size / 2 + tolerance / 2
  across_corners = (size + tolerance) * 2 / math.sqrt(3)

  return _prismatic_cutout(
      # apothem-mode RegularPolygon: flats face +-y, corners along x
      profile_fn=lambda: RegularPolygon((size + tolerance) / 2, 6,
                                        major_radius=False,
                                        align=(Align.CENTER, Align.CENTER)),
      slide_path_length=(half_flats - flap_depth - flap_center_gap
                         + edge_margin),
      flatten_width=across_corners + tolerance * 2,
      flatten_depth=size + tolerance * 2,
      taper_angle=taper_angle,
      flap_clearance=flap_clearance,
      epsilon=epsilon,
  )


# %%


if __name__ == "__main__":
  cutout = generate_cutout(49.6, tolerance=0.55, edge_offset=0.1, edge_adjust=-1)
  show(cutout)
# %%
