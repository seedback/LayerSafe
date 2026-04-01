import copy

from build123d import *
from ocp_vscode import *

# %%


def generate_base_tray(
    total_width=189.5,
    total_depth=66.0,
    floor_thickness=0.8,
    base_heigth=4.2,
    rail_height=8.4,
    rail_width=4.8,
    flap_middle_gap=0.2,
    flap_depth=11.8,
    hinge_width=2.8,
    hinge_height=4,
    hinge_depth=17.5,
    hinge_pin_radius=1.4,
    hinge_pin_length=3,
    bottom_chamfer=0.4,
    hinge_lock_radius=2,
    hinge_lock_offset=0.8,
    hinge_lock_depth=8.3,
    is_double_tray=False,
    epsilon=0.001,
):
  middle_width = total_width - rail_width*2
  middle_depth = total_depth/2 - (flap_depth + flap_middle_gap)
  middle_height = base_heigth + floor_thickness
  with BuildPart() as middle_builder:
    with Locations((0, epsilon, 0)):
      Box(middle_width + epsilon*2, middle_depth + epsilon,
          middle_height, align=(Align.CENTER, Align.MAX, Align.MIN))
    RigidJoint("LeftRail", joint_location=(Location((-middle_width/2, 0, 0))))
    RigidJoint("Flap", joint_location=(
        Location((0, -middle_depth - flap_middle_gap, 0))))
  tray = middle_builder.part

  with BuildPart() as rail_builder:
    with Locations((0, epsilon, 0)):
      Box(rail_width, total_depth/2, rail_height +
          epsilon, align=(Align.MAX, Align.MAX, Align.MIN))
    chamfer((rail_builder.part.edges() | Axis.Y < Axis.Z)[:2], 1)
    RigidJoint("Middle")

  tray.joints["LeftRail"].connect_to(rail_builder.part.joints["Middle"])
  tray += rail_builder.part
  tray += mirror(rail_builder.part, Plane.YZ)

  with BuildPart() as flap_builder:
    flap_width = middle_width - flap_middle_gap*2
    with Locations((0, 0, 0)):
      Box(flap_width, flap_depth, middle_height,
          align=(Align.CENTER, Align.MIN, Align.MIN))
    RigidJoint("Middle", joint_location=Location((0, flap_depth, 0)))
    RigidJoint("HingeLeft", joint_location=Location(
        (-flap_width/2, flap_depth, 0)))
    RigidJoint("HingeLockLeft", joint_location=Location(
        (-flap_width/2, 0, base_heigth/2 + floor_thickness/2)))
  flap = flap_builder.part

  with BuildPart() as hinge_builder:
    with Locations((0, -epsilon, 0)):
      Box(hinge_width, hinge_depth + epsilon, hinge_height,
          align=(Align.MIN, Align.MIN, Align.MIN))
    fillet_edges = (hinge_builder.part.edges() | Axis.X < Axis.Y)[:2]
    fillet_radius = hinge_builder.part.max_fillet(fillet_edges, epsilon, 32)
    fillet(fillet_edges, fillet_radius)
    RigidJoint("Flap")
    RigidJoint("HingePin", joint_location=Location(
        (hinge_width/2, hinge_depth-fillet_radius, hinge_height/2)))
  hinge = hinge_builder.part

  with BuildPart() as hinge_pin_builder:
    Cylinder(hinge_pin_radius, hinge_pin_length *
             2+hinge_width, rotation=(0, 90, 0))
    RigidJoint("Hinge")

  flap.joints["HingeLeft"].connect_to(hinge.joints["Flap"])
  flap += hinge
  flap += mirror(hinge, Plane.YZ)

  with BuildPart() as hinge_negative_builder:
    hinge_negative_width = hinge_width + flap_middle_gap*2
    hinge_negative_depth = hinge_depth + flap_middle_gap + epsilon
    hinge_negative_height = hinge_height + flap_middle_gap
    with Locations((-flap_middle_gap, -epsilon, 0)):
      Box(hinge_negative_width, hinge_negative_depth,
          hinge_negative_height, align=(Align.MIN, Align.MIN, Align.MIN))
    sketch_face = (hinge_negative_builder.part.faces() | Plane.YZ < Axis.X)[1]
    fillet_edges = (hinge_negative_builder.part.edges() | Axis.X < Axis.Y)[1:2]
    fillet(fillet_edges, fillet_radius)
    with BuildSketch(sketch_face):
      with Locations((-hinge_negative_height/2, hinge_negative_depth/2 - hinge_pin_radius - epsilon)):
        Polygon([(0, 0), (0, hinge_negative_height - fillet_radius + hinge_pin_radius),
                (hinge_negative_height - fillet_radius + hinge_pin_radius, 0)])
    extrude(amount=-hinge_negative_width)
    RigidJoint("Flap")
    RigidJoint("HingePin", joint_location=Location(
        (hinge_width/2, hinge_depth-fillet_radius, hinge_height/2)))
  hinge_negative = hinge_negative_builder.part

  with BuildPart() as hinge_pin_negative_builder:
    Cylinder(hinge_pin_radius + flap_middle_gap, hinge_pin_length *
             2+hinge_width+flap_middle_gap*2, rotation=(0, 90, 0))
    RigidJoint("Hinge")

  with BuildPart() as hinge_lock_builder:
    Cylinder(
        hinge_lock_radius,
        hinge_lock_depth,
        rotation=(90, 0, 0),
        align=(Align.MIN, Align.CENTER, Align.MAX)
    )
    RigidJoint("Flap", joint_location=Location((hinge_lock_offset, 0, 0)))
  flap.joints["HingeLockLeft"].connect_to(
      hinge_lock_builder.part.joints["Flap"])
  flap += hinge_lock_builder.part
  flap += mirror(hinge_lock_builder.part, Plane.YZ)

  with BuildPart() as hinge_lock_negative_builder:
    Cylinder(
        hinge_lock_radius + flap_middle_gap,
        hinge_lock_depth + flap_middle_gap,
        rotation=(90, 0, 0),
        align=(Align.MIN, Align.CENTER, Align.MAX)
    )
    RigidJoint("Flap", joint_location=Location(
        (hinge_lock_offset + flap_middle_gap, 0, 0)))

  tray.joints["Flap"].connect_to(flap_builder.part.joints["Middle"])
  flap.joints["HingeLockLeft"].connect_to(
      hinge_lock_negative_builder.part.joints["Flap"])
  tray -= hinge_lock_negative_builder.part
  tray -= mirror(hinge_lock_negative_builder.part, Plane.YZ)

  flap.joints["HingeLeft"].connect_to(hinge_negative.joints["Flap"])
  tray -= hinge_negative
  tray -= mirror(hinge_negative, Plane.YZ)

  if is_double_tray:
    chamfer_edges = tray.edges().filter_by_position(
        Axis.Z, -0.01, 0.01).sort_by(Axis.Y)[:-2]
  else:
    chamfer_edges = tray.edges().filter_by_position(Axis.Z, -0.01, 0.01)
  tray = chamfer(chamfer_edges, bottom_chamfer)

  flap.joints["HingeLeft"].connect_to(hinge_negative.joints["Flap"])
  hinge_negative.joints["HingePin"].connect_to(
      hinge_pin_negative_builder.part.joints["Hinge"])
  tray -= hinge_pin_negative_builder.part
  tray -= mirror(hinge_pin_negative_builder.part, Plane.YZ)

  # Chamfering this way resets joints, so saving and reapplying them
  chamfer_edges = flap.edges().filter_by_position(Axis.Z, -0.01, 0.01)
  stored_joints = {name: flap.joints[name] for name in flap.joints}
  flap = chamfer(chamfer_edges, bottom_chamfer)
  for name, joint in stored_joints.items():
    flap.joints[name] = joint

  flap.joints["HingeLeft"].connect_to(hinge.joints["Flap"])
  hinge.joints["HingePin"].connect_to(hinge_pin_builder.part.joints["Hinge"])
  flap += hinge_pin_builder.part
  flap += mirror(hinge_pin_builder.part, Plane.YZ)

  part_list = [flap]

  if is_double_tray:
    tray += mirror(tray, Plane.XZ)
    part_list.append(mirror(flap, Plane.XZ))

  part_list.append(tray)

  return Compound([part.translate((0, 0, -floor_thickness)) for part in part_list])


# %%

if __name__ == "__main__":
  base_tray = generate_base_tray(is_double_tray=False, total_width=30)
  export_step(base_tray, "test.step")
  show(base_tray, render_joints=False)

# %%
