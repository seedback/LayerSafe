# %%
"""Shared validation for cutout position lists.

Both the automatic layouts and manual placement produce the same
position dicts ({'x', 'y', 'size', 'index', 'flipped'}); this module
checks a finished list against the usable area (bounds) and against
itself (pairwise overlap, honoring per-pair nesting math).

Pure math: no CAD libraries required.
"""
import math

# Allowed boundary overshoot for floating-point precision.
EDGE_TOLERANCE = 0.1
# Minimum gap (mm) between the edges of adjacent cutouts.
MIN_EDGE_GAP = 0.4


def format_size(size):
  if isinstance(size, (tuple, list)):
    return f"{size[0]}x{size[1]}"
  return str(size)


def pair_nests_as_circles(nesting, i, j):
  """Exact circle tangency only applies between two circular footprints;
  any pair involving a box-nested shape falls back to bounding boxes."""
  return nesting[i] == 'circle' and nesting[j] == 'circle'


def _base_label(pos):
  """Name one base for a manual-placement error message, by its position
  in the user's input list."""
  return (f"Base {pos['index'] + 1} ({format_size(pos['size'])}mm "
          f"at x={pos['x']:g})")


def validate_positions(usable_area, positions, tolerance, layout_sizes,
                       nesting, name_bases=False,
                       row_rule_for_opposite_edges=False):
  """Check bounds and pairwise overlap for a finished position list.

  `layout_sizes` is the per-base (x_size, y_size) list, parallel to
  `positions`. `nesting` is a per-base list ('circle'/'box') or a single
  string broadcast to every base. With `name_bases=False` (the automatic
  layouts) failures raise the historical generic messages; with
  `name_bases=True` (manual placement) they name the offending base(s)
  so the user knows which placement to fix.

  `row_rule_for_opposite_edges` makes pairs resting on opposite edges
  use the linear layout's row-overlap rule instead of the strict
  MIN_EDGE_GAP check: the standard double tray runs opposing rows as
  close as ~0.1mm by design, so an opposite-edge pair is fine when the
  tray is nominally deep enough for both (sizes + tolerance, edge
  offsets deliberately ignored, matching _validate_row_overlap in the
  linear layout), and otherwise must clear sideways. Manual placement
  needs this so any exported automatic layout re-imports cleanly.
  """
  if isinstance(nesting, str):
    nesting = [nesting] * len(positions)

  # Boundary check. Raw sizes are used on purpose: the usable area
  # already reserves tolerance/2 along y, and the x safety margin absorbs
  # the tolerance overhang, matching the linear layout's convention.
  for pos, (fx, fy) in zip(positions, layout_sizes):
    left_edge = pos['x'] - fx / 2
    right_edge = pos['x'] + fx / 2
    top_edge = pos['y'] + fy / 2
    bottom_edge = pos['y'] - fy / 2

    if (left_edge < usable_area['min']['x'] - EDGE_TOLERANCE or
        right_edge > usable_area['max']['x'] + EDGE_TOLERANCE or
        top_edge > usable_area['max']['y'] + EDGE_TOLERANCE or
            bottom_edge < usable_area['min']['y'] - EDGE_TOLERANCE):
      if name_bases:
        raise ValueError(
            f"{_base_label(pos)} extends outside the tray's usable area "
            f"(x {usable_area['min']['x']:.2f} to "
            f"{usable_area['max']['x']:.2f}, "
            f"y {usable_area['min']['y']:.2f} to "
            f"{usable_area['max']['y']:.2f}).\n"
            "Move it inward, use a larger tray, or reduce the safety "
            "margins."
        )
      raise ValueError(
          f"A base of size {format_size(pos['size'])}mm does not fit "
          "within the tray's usable area.\n"
          "Use a larger tray, remove a base from the list, or reduce "
          "the safety margins."
      )

  usable_depth = usable_area['max']['y'] - usable_area['min']['y']

  # Overlap check between every pair of cutouts (not just consecutive ones),
  # using the full (toleranced) hole sizes.
  for i in range(len(positions)):
    for j in range(i + 1, len(positions)):
      dx = positions[j]['x'] - positions[i]['x']
      dy = positions[j]['y'] - positions[i]['y']
      if pair_nests_as_circles(nesting, i, j):
        center_distance = math.sqrt(dx*dx + dy*dy)
        edge_distance = (
            center_distance -
            (layout_sizes[i][0] + tolerance) / 2 -
            (layout_sizes[j][0] + tolerance) / 2
        )
      else:
        # Bounding boxes are separated if they clear on EITHER axis.
        x_gap = (abs(dx) - (layout_sizes[i][0] + tolerance) / 2
                 - (layout_sizes[j][0] + tolerance) / 2)
        y_gap = (abs(dy) - (layout_sizes[i][1] + tolerance) / 2
                 - (layout_sizes[j][1] + tolerance) / 2)
        edge_distance = max(x_gap, y_gap)
      if edge_distance >= MIN_EDGE_GAP:
        continue
      if (row_rule_for_opposite_edges
              and positions[i]['flipped'] != positions[j]['flipped']):
        # Linear-layout row rule (see _validate_row_overlap): opposing
        # bases share the tray's middle and may nominally kiss there
        # (the standard tray runs opposing rows ~0.1mm apart by design);
        # they only collide when together too deep for the tray AND
        # overlapping along x.
        row_y_gap = (usable_depth - layout_sizes[i][1]
                     - layout_sizes[j][1] - tolerance)
        row_x_gap = (abs(dx) - (layout_sizes[i][0] + tolerance) / 2
                     - (layout_sizes[j][0] + tolerance) / 2)
        if row_y_gap >= -0.001 or row_x_gap >= MIN_EDGE_GAP:
          continue
        raise ValueError(
            f"{_base_label(positions[i])} and "
            f"{_base_label(positions[j])} overlap in the middle of "
            "the tray: together they are too deep to sit opposite "
            "each other at the same x.\n"
            "Offset them sideways, use a deeper tray, or move one to "
            "the other edge."
        )
      if name_bases:
        raise ValueError(
            f"{_base_label(positions[i])} overlaps "
            f"{_base_label(positions[j])}: their holes need at least "
            f"{MIN_EDGE_GAP}mm between edges but have "
            f"{edge_distance:.2f}mm.\n"
            "Move the bases further apart."
        )
      raise ValueError(
          "Total width of bases is too wide to fit on the tray.\n"
          + "Remove a base from the list and try again."
      )
