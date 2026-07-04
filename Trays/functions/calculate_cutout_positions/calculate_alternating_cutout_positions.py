# %%
import math

# Validation constants
EDGE_TOLERANCE = 0.1  # Allowed boundary overshoot for floating-point precision
MIN_EDGE_GAP = 0.4    # Minimum gap (mm) between the edges of adjacent cutouts


def calculate_alternating_cutout_positions(
    usable_area,
    sizes,
    edge_offsets,
    tolerance,
    layout_sizes=None,
    nesting='circle',
):
  """Nest bases alternately against the front and back edges.

  `layout_sizes` is an optional per-base (x_size, y_size) list (see the
  linear layout); defaults to (size, size). `nesting` selects the spacing
  math: 'circle' is exact tangency for circular footprints; 'box' is
  conservative bounding-box separation, safe for any shape (squares,
  hexes, ovals) -- a pair resting on opposite edges is spaced apart in x
  unless the tray is deep enough for them to clear vertically.
  """
  if len(sizes) == 0:
    return []

  if layout_sizes is None:
    layout_sizes = [(size, size) for size in sizes]

  if len(sizes) == 1:
    positions = [{
        'x': 0,
        'y': usable_area['min']['y'] + layout_sizes[0][1] / 2
        + _offset(edge_offsets, 0),
        'size': sizes[0],
        'flipped': False,
    }]
  else:
    positions = _calculate_initial_positions(
        usable_area, sizes, edge_offsets, tolerance, layout_sizes, nesting)

  _validate_positions(usable_area, positions, tolerance, layout_sizes,
                      nesting)

  return positions


def _offset(edge_offsets, i):
  return edge_offsets[i] if i < len(edge_offsets) else 0


def _format_size(size):
  if isinstance(size, (tuple, list)):
    return f"{size[0]}x{size[1]}"
  return str(size)


def _box_min_dx(fx_a, fy_a, fx_b, fy_b, dy, tolerance, gap):
  """Minimum x distance between two bounding-box bases whose centers are
  `dy` apart in y, keeping `gap` between the physical (toleranced) holes.
  Zero when the tray is deep enough for the pair to clear vertically."""
  y_clearance = dy - (fy_a + tolerance) / 2 - (fy_b + tolerance) / 2
  if y_clearance >= gap:
    return 0.0
  return (fx_a + tolerance) / 2 + (fx_b + tolerance) / 2 + gap


def _calculate_initial_positions(
    usable_area,
    sizes,
    edge_offsets,
    tolerance,
    layout_sizes,
    nesting,
):
  positions = []
  usable_area_total = {
      'x': -usable_area['min']['x'] + usable_area['max']['x'],
      'y': -usable_area['min']['y'] + usable_area['max']['y']}
  for i, size in enumerate(sizes):
    fx, fy = layout_sizes[i]
    if i == 0:
      positions.append({
          'x': usable_area['min']['x'] + fx/2,
          'y': usable_area['min']['y'] + fy/2 + _offset(edge_offsets, i),
          'size': size,
          'flipped': False,
      })
    else:
      last_pos = positions[-1]
      last_fx, last_fy = layout_sizes[i - 1]
      # Distance in y between the two resting centers.
      dy = usable_area_total['y'] - last_fy / 2 - fy / 2
      if nesting == 'circle':
        # Nest against the previous cutout using the full (toleranced)
        # hole sizes so the physical holes keep their clearance.
        hyp = (last_fx + tolerance) / 2 + (fx + tolerance) / 2
        offset = _side_from_hyp(hyp, dy)
      else:
        offset = _box_min_dx(last_fx, last_fy, fx, fy, dy, tolerance, 0.0)
      is_flipped = not last_pos['flipped']
      # Edge offsets move the cutout inward, away from its resting edge
      # (same convention as the linear layout).
      if is_flipped:
        y = usable_area['max']['y'] - fy/2 - _offset(edge_offsets, i)
      else:
        y = usable_area['min']['y'] + fy/2 + _offset(edge_offsets, i)
      positions.append({
          'x': last_pos['x'] + offset,
          'y': y,
          'size': size,
          'flipped': is_flipped,
      })

  for i in range(100):
    positions, error = _redistribution_pass(
        usable_area, positions, tolerance, layout_sizes, nesting)
    if error < 0.01:
      break

  return positions


def _validate_positions(usable_area, positions, tolerance, layout_sizes,
                        nesting):
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
      raise ValueError(
          f"A base of size {_format_size(pos['size'])}mm does not fit "
          "within the tray's usable area.\n"
          "Use a larger tray, remove a base from the list, or reduce "
          "the safety margins."
      )

  # Overlap check between every pair of cutouts (not just consecutive ones),
  # using the full (toleranced) hole sizes.
  for i in range(len(positions)):
    for j in range(i + 1, len(positions)):
      dx = positions[j]['x'] - positions[i]['x']
      dy = positions[j]['y'] - positions[i]['y']
      if nesting == 'circle':
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
      if edge_distance < MIN_EDGE_GAP:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray.\n"
            + "Remove a base from the list and try again."
        )


def _redistribution_pass(
        usable_area,
        positions,
        tolerance,
        layout_sizes,
        nesting):
  if len(positions) <= 1:
    return positions, 0

  # Fixed boundaries
  target_first_x = usable_area['min']['x'] + layout_sizes[0][0] / 2
  target_last_x = usable_area['max']['x'] - layout_sizes[-1][0] / 2
  target_x_span = target_last_x - target_first_x

  # Vertical distances (fixed by alternating pattern)
  dy_list = []
  for i in range(len(positions) - 1):
    dy = abs(positions[i+1]['y'] - positions[i]['y'])
    dy_list.append(dy)

  if len(dy_list) == 0:
    return positions, 0

  # Find uniform edge-to-edge gap such that all gaps are equal.
  # Circle nesting: for each segment i,
  #   h_i = edge_gap + full_radius_i + full_radius_{i+1}; dx = sqrt(h^2-dy^2)
  # Box nesting: dx is zero when the pair clears vertically by the gap,
  # otherwise the full half-widths plus the gap.
  # Full sizes include the fit tolerance, since that is the size of the
  # physical hole cut into the tray.

  def calculate_dx(i, dy, gap):
    fx_a, fy_a = layout_sizes[i]
    fx_b, fy_b = layout_sizes[i + 1]
    if nesting == 'circle':
      radius_a = (fx_a + tolerance) / 2
      radius_b = (fx_b + tolerance) / 2
      h = gap + radius_a + radius_b  # Hypotenuse needed for this gap
      if h * h < dy * dy:
        return None  # Invalid: hypotenuse must be >= vertical distance
      return math.sqrt(h * h - dy * dy)
    return _box_min_dx(fx_a, fy_a, fx_b, fy_b, dy, tolerance, gap)

  def calculate_x_span(gap):
    """Calculate total x span for a given edge-to-edge gap"""
    total_dx = 0
    for i, dy in enumerate(dy_list):
      dx = calculate_dx(i, dy, gap)
      if dx is None:
        return None
      total_dx += dx
    return total_dx

  # Binary search to find gap that gives us the right x span
  low_gap = 0.01
  high_gap = target_x_span + 100

  for _ in range(50):
    mid_gap = (low_gap + high_gap) / 2
    span = calculate_x_span(mid_gap)

    if span is None or span < target_x_span:
      low_gap = mid_gap
    else:
      high_gap = mid_gap

  best_gap = (low_gap + high_gap) / 2

  # Calculate dx values with best_gap
  dx_list = []
  for i, dy in enumerate(dy_list):
    dx = calculate_dx(i, dy, best_gap)
    if dx is None:
      # best_gap sits marginally inside the infeasible region; fall back
      # to the known-feasible upper bound of the search.
      dx = calculate_dx(i, dy, high_gap)
    dx_list.append(dx)

  # Position elements based on calculated dx values
  new_positions = []
  current_x = target_first_x
  for i, pos in enumerate(positions):
    new_pos = pos.copy()
    new_pos['x'] = current_x
    new_positions.append(new_pos)
    if i < len(dx_list):
      current_x += dx_list[i]

  # Calculate error: how close are we to target span
  actual_span = sum(dx_list)
  error = abs(actual_span - target_x_span)

  return new_positions, error


def _side_from_hyp(
    hyp,
    side
):
  ratio = side / hyp
  if abs(ratio) > 1:
    raise ValueError("Alternating positioning was used and vertical gap between bases is too large.\n"
    "(eg. any set of two subsequent bases must be big enough to touch if they're placed on oposite sides of the tray)\n" \
    "Try enabling --force-linear-positions.")
  angle = math.asin(ratio)
  result = hyp * math.cos(angle)
  return result

# %%


if __name__ == "__main__":
  print(calculate_alternating_cutout_positions(
      {'min': {'x': -82.9, 'y': -31.65}, 'max': {'x': 82.9, 'y': 31.65}},
      [40, 40], [0, 0], 0.55))

# %%
