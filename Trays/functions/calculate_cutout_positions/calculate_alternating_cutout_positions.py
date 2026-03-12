# %%
import math


def calculate_alternating_cutout_positions(
    usable_area,
    diameters,
    tolerance
):
  full_diameters = []
  for diameter in diameters:
    full_diameters.append(diameter + tolerance)
  
  if len(diameters) == 1:
    return [{
        'x': 0,
        'diameter': diameters[0],
    }]

  positions = _calculate_initial_positions(usable_area, full_diameters, tolerance)

  return positions


def _calculate_initial_positions(
    usable_area,
    diameters,
    tolerance
):
  positions = []
  usable_area_total = {'x': -usable_area['min']['x'] + usable_area['max']
                       ['x'], 'y': -usable_area['min']['y'] + usable_area['max']['y']}
  for i, diameter in enumerate(diameters):
    if i == 0:
      positions.append({
          'x': usable_area['min']['x'] + diameter/2,
          'y': usable_area['min']['y'] + diameter/2,
          'diameter': diameters[0] - tolerance,
          'flipped': False,
      })
    else:
      last_pos = positions[-1]
      offset = _side_from_hyp(last_pos['diameter']/2 + diameter/2,
                              usable_area_total['y'] - last_pos['diameter']/2 - diameter/2)
      positions.append({
          'x': last_pos['x'] + offset,
          'y': usable_area['min']['y'] + diameter/2 if last_pos['flipped'] else usable_area['max']['y'] - diameter/2,
          'diameter': diameter - tolerance,
          'flipped': not last_pos['flipped'],
      })

  for i in range(100):
    positions, error = _redistribution_pass(usable_area, positions)
    if error < 0.01:
      break

# Validate: check for overlaps and boundary violations
  edge_tolerance = 0.1  # Allow 0.1mm tolerance for floating-point precision
  gap_tolerance = 0.4   # Minimum 0.4mm gap between circles
  has_error = False
  
  for i, pos in enumerate(positions):
    # Check boundaries (allow small tolerance for floating-point precision)
    left_edge = pos['x'] - pos['diameter'] / 2
    right_edge = pos['x'] + pos['diameter'] / 2
    top_edge = pos['y'] + pos['diameter'] / 2
    bottom_edge = pos['y'] - pos['diameter'] / 2

    if (left_edge < usable_area['min']['x'] - edge_tolerance or 
        right_edge > usable_area['max']['x'] + edge_tolerance or
        top_edge > usable_area['max']['y'] + edge_tolerance or 
        bottom_edge < usable_area['min']['y'] - edge_tolerance):
      break

  # Check for overlaps (minimum 0.4mm gap required)
  distances = []
  for i in range(len(positions) - 1):
    dx = positions[i+1]['x'] - positions[i]['x']
    dy = positions[i+1]['y'] - positions[i]['y']
    center_distance = math.sqrt(dx*dx + dy*dy)
    # Edge-to-edge distance = center distance - radius1 - radius2
    edge_distance = center_distance - \
        positions[i]['diameter']/2 - positions[i+1]['diameter']/2
    distances.append(edge_distance)

    if edge_distance < gap_tolerance:
      has_error = True

  if has_error:
    raise ValueError(
        "Total width of bases is too wide to fit on the tray.\n"
        + "Remove a diameter from the list and try again."
    )

  return positions


def _redistribution_pass(
        usable_area,
        positions):
  if len(positions) <= 1:
    return positions, 0

  # Fixed boundaries
  target_first_x = usable_area['min']['x'] + positions[0]['diameter'] / 2
  target_last_x = usable_area['max']['x'] - positions[-1]['diameter'] / 2
  target_x_span = target_last_x - target_first_x

  # Vertical distances (fixed by alternating pattern)
  dy_list = []
  for i in range(len(positions) - 1):
    dy = abs(positions[i+1]['y'] - positions[i]['y'])
    dy_list.append(dy)

  if len(dy_list) == 0:
    return positions, 0

  # Find uniform edge-to-edge gap such that all gaps are equal
  # For each segment i: edge_gap = h_i - radius_i - radius_{i+1}
  # Therefore: h_i = edge_gap + radius_i + radius_{i+1}

  def calculate_x_span(gap):
    """Calculate total x span for a given edge-to-edge gap"""
    total_dx = 0
    for i, dy in enumerate(dy_list):
      radius_i = positions[i]['diameter'] / 2
      radius_next = positions[i+1]['diameter'] / 2
      h = gap + radius_i + radius_next  # Hypotenuse needed for this gap

      if h * h < dy * dy:
        return None  # Invalid: hypotenuse must be >= vertical distance
      dx = math.sqrt(h * h - dy * dy)
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
    radius_i = positions[i]['diameter'] / 2
    radius_next = positions[i+1]['diameter'] / 2
    h = best_gap + radius_i + radius_next
    dx = math.sqrt(h * h - dy * dy)
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
  return math.sqrt(hyp*hyp - side*side)

# %%


if __name__ == "__main__":
  print(calculate_alternating_cutout_positions(
      {'min': {'x': -82.9, 'y': -31.65}, 'max': {'x': 82.9, 'y': 31.65}},
      [40, 40]))

# %%
