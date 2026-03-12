from build123d import *
from ocp_vscode import *


def generate_base_tray(
    total_width=189.5,
    total_depth=66.0,
    floor_thickness=0.8,
    base_heigth=4.2,
    rail_height=8.4,
    rail_width=4.8,
    flap_center_gap=0.2,
    flap_depth=11.8,
    hinge_width=2.8,
    hinge_height=3.6,
    hinge_depth=17.5,
    hinge_pin_radius=1.4,
    hinge_pin_length=3,
    bottom_chamfer=0.4,
    hinge_lock_radius=2,
    hinge_lock_offset=0.5,
    hinge_lock_depth=8.3,
    is_double_tray=False,
    epsilon=0.001,
):
  """Generate tray geometry with all components."""
  # Calculated Parameters
  center_width = total_width - 2 * rail_width
  center_depth = total_depth - 2 * (flap_depth + flap_center_gap)

  hinge_top_offset = floor_thickness - 0.4

  flap_width = center_width - flap_center_gap * 2

  hinge_negative_space = flap_center_gap
  hinge_negative_width = hinge_width + 2 * hinge_negative_space
  hinge_negative_depth = hinge_depth + hinge_negative_space
  hinge_negative_height = hinge_height + hinge_negative_space
  hinge_pin_offset = (
      hinge_height - 2 * hinge_pin_radius + hinge_top_offset) / 2
  hinge_negative_fillet_radius = (
      hinge_pin_radius + hinge_pin_offset + hinge_negative_space
  )

  hinge_depth += hinge_negative_space

  # Middle

  with BuildPart() as center:
    # Middle Box
    Box(
        center_width,
        center_depth / 2,
        base_heigth + hinge_top_offset,
        align=(Align.CENTER, Align.MAX, Align.MIN),
    )

    # Left Rail
    with Locations((-center_width / 2, 0, 0)):
      b = Box(
          rail_width,
          total_depth / 2,
          rail_height,
          align=(Align.MAX, Align.MAX, Align.MIN),
      )
      # Chamfer the two top edges along Y axis
      chamfer(b.edges().filter_by(Axis.Y).sort_by(Axis.Z)[-2:], 1)
    mirror(center.part, Plane.YZ)

  # Hinge Negative

  # Main box for hinge negative
  hinge_negative_offset = (-center_width / 2, -
                           center_depth / 2 - epsilon, -epsilon)
  with BuildPart() as hinge_negative:
    with Locations(hinge_negative_offset):
      b = Box(
          hinge_negative_width,
          hinge_negative_depth + epsilon,
          hinge_negative_height + hinge_top_offset + epsilon,
          align=(Align.MIN, Align.MIN, Align.MIN),
      )
      fillet(
          b.edges().filter_by(Axis.X)[-1],
          radius=hinge_negative_fillet_radius,
      )
    mirror(hinge_negative.part, Plane.YZ)

  # Cylinder-pin for hinge negative, to be applied later
  with BuildPart() as hinge_negative_pin:
    with Locations(hinge_negative_offset):
      with Locations((
          -hinge_pin_length,
          hinge_depth - 2 * hinge_pin_radius - hinge_pin_offset * 2 + hinge_top_offset/2 + epsilon,
          hinge_pin_offset - hinge_negative_space + epsilon,
      )):
        Cylinder(
            hinge_pin_radius + hinge_negative_space,
            (
                hinge_pin_length * 2 + hinge_width +
                2 * hinge_negative_space
            ),
            rotation=(0, 90, 0),
            align=(Align.MAX, Align.MIN, Align.MIN),
        )
    mirror(hinge_negative_pin.part, Plane.YZ)

  # Final adjustments on Center

  # Apply hinge negative to center
  center.part -= hinge_negative.part

  # Apply chamfer to bottom-inner edge of hinge negative
  # To allow hinge to rotate back
  bottom_edges = center.faces().sort_by(Axis.Z)[0].edges()
  edges_x = bottom_edges.filter_by(Axis.X)
  hinge_edges = sorted(
      edges_x, key=lambda e: abs(e.center().Y)
  )[1:3]
  center.part = chamfer(
      hinge_edges,
      (
          hinge_negative_height - hinge_negative_fillet_radius -
          epsilon
      ),
      angle=45,
  )

  # Apply chamfer to edge around bottom
  bottom_edges = center.faces().sort_by(Axis.Z)[0].edges()
  edges_x = bottom_edges.filter_by(Axis.X)
  hinge_edges = sorted(
      edges_x, key=lambda e: abs(e.center().Y)
  )[1:3]
  back_edge = sorted(edges_x, key=lambda e: abs(e.center().Y))[:1]
  center.part = chamfer(
      bottom_edges - hinge_edges - hinge_edges - back_edge,
      bottom_chamfer,
  )

  # Apply Hinge negative pin to center
  center.part -= hinge_negative_pin.part

  # Flaps

  with BuildPart() as flap:
    with Locations((0, -total_depth / 2, 0)):
      Box(
          flap_width,
          flap_depth,
          base_heigth + hinge_top_offset,
          align=(Align.CENTER, Align.MIN, Align.MIN),
      )

  with BuildPart() as hinge:
    with Locations((0, -total_depth / 2, 0)):
      # Hinge
      with Locations((-flap_width / 2, flap_depth, 0)):
        Box(
            hinge_width,
            hinge_depth,
            hinge_height + hinge_top_offset,
            align=(Align.MIN, Align.MIN, Align.MIN),
        )
        with Locations((
            -hinge_pin_length,
            hinge_depth - hinge_pin_radius * 2 - hinge_pin_offset,
            hinge_pin_offset,
        )):
          Cylinder(
              hinge_pin_radius,
              hinge_pin_length * 2 + hinge_width,
              rotation=(0, 90, 0),
              align=(Align.MAX, Align.MIN, Align.MIN),
          )
    fillet(
        hinge.edges().filter_by(Axis.X).sort_by(Axis.Y)[-2:],
        (hinge_height + hinge_top_offset) / 2 - epsilon,
    )
    mirror(hinge.part, Plane.YZ)

  flap.part += hinge.part

  with BuildPart() as hinge_lock:
    with Locations((
        -(flap_width / 2 - hinge_lock_radius + hinge_lock_offset),
        -total_depth / 2,
        (base_heigth + hinge_top_offset) / 2,
    )):
      Cylinder(
          hinge_lock_radius,
          hinge_lock_depth,
          rotation=(90, 0, 0),
          align=(Align.CENTER, Align.CENTER, Align.MAX),
      )
    hinge_lock.part = split(
        hinge_lock.part,
        flap.part.faces().filter_by(Plane.YZ).sort_by(Axis.X)[1],
    )
    hinge_lock.part = hinge_lock.part + mirror(hinge_lock.part, Plane.YZ)

  with BuildPart() as hinge_lock_negative:
    with Locations((
        -(flap_width / 2 - hinge_lock_radius + hinge_lock_offset),
        -total_depth / 2,
        (base_heigth + hinge_top_offset) / 2,
    )):
      Cylinder(
          hinge_lock_radius + hinge_negative_space,
          hinge_lock_depth,
          rotation=(90, 0, 0),
          align=(Align.CENTER, Align.CENTER, Align.MAX),
      )
    hinge_lock_negative.part = split(
        hinge_lock_negative.part,
        flap.part.faces().filter_by(Plane.YZ).sort_by(Axis.X)[1],
    )
    hinge_lock_negative.part = (
        hinge_lock_negative.part +
        mirror(hinge_lock_negative.part, Plane.YZ)
    )

  flap.part += hinge_lock.part
  center.part -= hinge_lock_negative.part

  # Final adjustments for flaps

  flap_bottom_chamfer_edges = (
      flap.faces()
      .sort_by(Axis.Z)[0]
      .edges()
      .filter_by(Axis.X)
      .sort_by(Axis.Y)[0:2]
  )

  arc_candidates = flap.edges().filter_by(Plane.YZ)
  flap_hinge_arc_edges = ShapeList([
      e for e in arc_candidates
      if e.length > 0.001
  ])
  flap_hinge_arc_edges = flap_hinge_arc_edges.sort_by(Axis.Y)[-12:]

  flap_chamfer_edges = flap_bottom_chamfer_edges + flap_hinge_arc_edges

  flap.part = chamfer(flap_chamfer_edges, 0.4 - epsilon)

  # Decide whether it's one or two
  flap_compound = flap.part

  if is_double_tray:
    center.part += mirror(center.part, Plane.XZ)
    flap_compound = Compound([flap.part, mirror(flap.part, Plane.XZ)])

  return Compound([center.part, flap_compound])

# %%


if __name__ == "__main__":
  center, flap = generate_base_tray(is_double_tray=True)

  show(center, flap)
# %%
