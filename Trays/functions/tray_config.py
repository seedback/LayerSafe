from dataclasses import dataclass


@dataclass
class TrayConfig:
  """All tray geometry and generation settings, defaulted in one place.

  Per-base inputs (sizes, edge offsets, edge adjusts) are passed to
  generate_full_tray separately. All lengths are in millimeters.
  """

  # Overall dimensions
  total_width: float = 189.5
  total_depth: float = 66.0
  # (x, y) margin between the tray walls and the usable cutout area
  safety_margin: tuple = (6.5, 0.8)

  # Base structure
  floor_thickness: float = 0.8
  base_height: float = 4.2
  rail_height: float = 8.4
  rail_width: float = 4.8

  # Flap
  flap_center_gap: float = 0.2
  flap_depth: float = 11.8

  # Hinge (hinge_depth is measured from the edge of the center, not the flap)
  hinge_width: float = 2.8
  hinge_height: float = 3.6
  hinge_depth: float = 17.5
  hinge_pin_radius: float = 1.4
  hinge_pin_length: float = 3.0
  bottom_chamfer: float = 0.4
  hinge_lock_radius: float = 3.5
  hinge_lock_offset: float = 0.4
  hinge_lock_depth: float = 8.3
  hinge_diameter: float = 27.7

  # Cutout and layout options
  cutout_shape: str = 'circle'  # any key of shapes.SHAPES ('circle', 'square')
  # Wall angle of the cutout in degrees from vertical. None uses the
  # shape's default (see cutout_generator: 12.5 for circles, 5 for
  # squares). For a measured base:
  #   taper_angle = atan((top_size - bottom_size) / (2 * base_height))
  taper_angle: float = None
  min_cutout_spacing: float = 2.0  # Minimum gap (mm) between cutout edges
  is_double_tray: bool = True
  force_linear_positions: bool = False
  tolerance: float = 0.55  # Base fit tolerance (mm)
  epsilon: float = 0.001
