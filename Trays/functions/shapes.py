"""Registry of cutout shapes the tray generator can cut for a base.

To add a new shape:
  1. Subclass CutoutShape and implement build() (the 3D negative) and
     circumradius(); override footprint() if the bounding box is not
     size x size.
  2. Set supports_alternating only if the shape's clearance math is safe
     under the alternating layout's nesting.
  3. Add an instance to SHAPES below. The CLI --cutout-shape choices and
     the orchestrator pick it up from there.

This module must stay importable without the CAD libraries (build123d),
so shape classes import their geometry builders lazily inside build().
All lengths are in millimeters.
"""
import math


class CutoutShape:
  """One cutout shape, described by a single scalar `size`.

  For a circle, `size` is the base diameter; for a square, the side
  length. `tolerance` is the fit tolerance added around the base, so the
  physical hole measures size + tolerance across.
  """

  #: Registry key, also the CLI value for --cutout-shape.
  name = None
  #: Whether the alternating (nested) layout may be used for this shape.
  supports_alternating = False

  def footprint(self, size, tolerance):
    """(x, y) bounding extent of the physical hole cut into the tray."""
    return (size + tolerance, size + tolerance)

  def layout_sizes(self, size, tolerance):
    """Per-axis sizes the layout algorithms should use for this base,
    defined so that layout_size + tolerance equals the physical hole
    footprint per axis.

    Default: (size, size), exact for shapes whose bounding box is
    size x size (do NOT compute it as footprint - tolerance here: the
    float round-trip would shift layout positions by ~1e-14 and make
    otherwise identical exports differ). Shapes with a wider bounding
    box (e.g. a hex across its corners) must override this.
    """
    return (size, size)

  def circumradius(self, size, tolerance):
    """Radius of the smallest circle containing the physical hole."""
    raise NotImplementedError

  def min_center_distance(self, size, other, other_size, tolerance, gap=0.0):
    """Minimum center-to-center distance to another cutout that keeps at
    least `gap` clearance between their edges.

    Conservative default: the shapes' circumscribed circles touch. Shape
    pairs with tighter exact math can override this.
    """
    return (self.circumradius(size, tolerance)
            + other.circumradius(other_size, tolerance)
            + gap)

  def build(self, size, **params):
    """Build the 3D negative (a build123d Compound) for one cutout."""
    raise NotImplementedError


class CircleShape(CutoutShape):
  name = 'circle'
  supports_alternating = True

  def circumradius(self, size, tolerance):
    return (size + tolerance) / 2

  def build(self, size, **params):
    try:
      from .cutout_generator import generate_cutout
    except ImportError:
      from cutout_generator import generate_cutout
    return generate_cutout(size, **params)


class SquareShape(CutoutShape):
  name = 'square'
  # The alternating layout nests bases using circle-tangency math, which
  # underestimates a square's diagonal footprint and can overlap adjacent
  # squares at their corners — keep squares on the linear layout.
  supports_alternating = False

  def circumradius(self, size, tolerance):
    return (size + tolerance) * math.sqrt(2) / 2

  def build(self, size, **params):
    try:
      from .cutout_generator import generate_square_cutout
    except ImportError:
      from cutout_generator import generate_square_cutout
    return generate_square_cutout(size, **params)


class HexShape(CutoutShape):
  """Regular hexagon, measured across the flats (the natural caliper
  measurement). Oriented with flats facing the tray edges, so the corners
  point along x: the footprint is 2/sqrt(3) (~1.155x) wider across x than
  the measured size.
  """
  name = 'hex'
  # Same reason as squares: circle-tangency nesting cannot guarantee
  # corner clearance, so hexes stay on the linear layout.
  supports_alternating = False

  def footprint(self, size, tolerance):
    across_corners = (size + tolerance) * 2 / math.sqrt(3)
    return (across_corners, size + tolerance)

  def circumradius(self, size, tolerance):
    return (size + tolerance) / math.sqrt(3)

  def layout_sizes(self, size, tolerance):
    across_corners = (size + tolerance) * 2 / math.sqrt(3)
    return (across_corners - tolerance, size)

  def build(self, size, **params):
    try:
      from .cutout_generator import generate_hex_cutout
    except ImportError:
      from cutout_generator import generate_hex_cutout
    return generate_hex_cutout(size, **params)


SHAPES = {shape.name: shape
          for shape in (CircleShape(), SquareShape(), HexShape())}


def get_shape(name):
  try:
    return SHAPES[name]
  except KeyError:
    raise ValueError(
        f"Unknown cutout shape '{name}'. "
        f"Available shapes: {', '.join(sorted(SHAPES))}"
    ) from None
