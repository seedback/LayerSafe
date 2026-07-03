# %%
import math

# %%


def _line_fits(line_total, n_in_line, new_size, max_width, tolerance, min_spacing):
  """Check if adding new_size to a line still fits with minimum spacing."""
  n = n_in_line + 1
  return line_total + new_size + (n - 1) * tolerance + (n + 1) * min_spacing <= max_width


def calculate_linear_cutout_positions(
    usable_area,
    sizes,
    edge_offsets,
    tolerance,
    is_double_tray=False,
    min_spacing=2.0,
):
  line_one = []
  line_one_indices = []
  line_two = []
  line_two_indices = []

  max_width = usable_area['max']['x'] * 2
  line_one_total = 0
  line_two_total = 0

  left_idx = 0
  right_idx = len(sizes) - 1
  take_from_left = True

  # Alternate taking from start and end
  while left_idx <= right_idx:
    if take_from_left:
      size = sizes[left_idx]
      if _line_fits(line_one_total, len(line_one), size, max_width, tolerance, min_spacing):
        line_one.append(size)
        line_one_indices.append(left_idx)
        line_one_total += size
      elif is_double_tray and _line_fits(line_two_total, len(line_two), size, max_width, tolerance, min_spacing):
        line_two.append(size)
        line_two_indices.append(left_idx)
        line_two_total += size
      else:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray with the required spacing.\n"
            + "Remove a base from the list, reduce min_cutout_spacing, or use a wider tray."
        )
      left_idx += 1
    else:
      size = sizes[right_idx]
      if _line_fits(line_two_total, len(line_two), size, max_width, tolerance, min_spacing):
        line_two.insert(0, size)
        line_two_indices.insert(0, right_idx)
        line_two_total += size
      elif _line_fits(line_one_total, len(line_one), size, max_width, tolerance, min_spacing):
        line_one.append(size)
        line_one_indices.append(right_idx)
        line_one_total += size
      else:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray with the required spacing.\n"
            + "Remove a base from the list, reduce min_cutout_spacing, or use a wider tray."
        )
      right_idx -= 1

    if is_double_tray:
      take_from_left = not take_from_left

  x_positions = calculate_line_positions(
      usable_area,
      line_one,
      tolerance,
      min_spacing,
  )

  for i, pos in enumerate(x_positions):
    pos['y'] = usable_area['min']['y'] + (pos['size']) / 2
    if line_one_indices[i] < len(edge_offsets):
      pos['y'] += edge_offsets[line_one_indices[i]]
    pos['flipped'] = False

  if is_double_tray:
    y_positions = calculate_line_positions(
        usable_area,
        line_two,
        tolerance,
        min_spacing,
    )

    for i, pos in enumerate(y_positions):
      pos['y'] = usable_area['max']['y'] - (pos['size']) / 2
      if line_two_indices[i] < len(edge_offsets):
        pos['y'] -= edge_offsets[line_two_indices[i]]
      pos['flipped'] = True

    positions = x_positions + y_positions
  else:
    positions = x_positions

  return positions


def calculate_line_positions(
    usable_area,
    sizes,
    tolerance,
    min_spacing=2.0,
):
  positions = []
  size_total = sum(sizes)
  n = len(sizes)

  if n == 0:
    return positions

  max_width = usable_area['max']['x'] * 2

  # Reserve min_spacing for all n+1 gaps, distribute any extra space equally.
  available = max_width - size_total - (n - 1) * tolerance - (n + 1) * min_spacing
  gap = min_spacing + max(available, 0) / (n + 1)

  x = -usable_area['max']['x']
  for size in sizes:
    x += gap + size / 2
    positions.append({'x': x, 'size': size})
    x += size / 2 + tolerance

  return positions
