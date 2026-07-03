# %%

# Minimum clearance (mm) between the physical edges of front- and
# back-row cutouts (matches the alternating layout's MIN_EDGE_GAP).
MIN_ROW_GAP = 0.4


def _line_fits(line_total, n_in_line, new_x_size, max_width, tolerance, min_spacing):
  """Check if adding new_x_size to a line still fits with minimum spacing."""
  n = n_in_line + 1
  return line_total + new_x_size + (n - 1) * tolerance + (n + 1) * min_spacing <= max_width


def calculate_linear_cutout_positions(
    usable_area,
    sizes,
    edge_offsets,
    tolerance,
    is_double_tray=False,
    min_spacing=2.0,
    layout_sizes=None,
):
  """Place bases on one or two straight rows.

  `layout_sizes` is an optional per-base (x_size, y_size) list for shapes
  whose bounding box is not size x size (e.g. a hex is wider across its
  corners than its measured across-flats size). Defaults to (size, size).
  The physical hole measures layout_size + tolerance across each axis;
  positions keep the original scalar under the 'size' key.
  """
  if layout_sizes is None:
    layout_sizes = [(size, size) for size in sizes]

  line_one_indices = []
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
      x_size = layout_sizes[left_idx][0]
      if _line_fits(line_one_total, len(line_one_indices), x_size, max_width, tolerance, min_spacing):
        line_one_indices.append(left_idx)
        line_one_total += x_size
      elif is_double_tray and _line_fits(line_two_total, len(line_two_indices), x_size, max_width, tolerance, min_spacing):
        line_two_indices.append(left_idx)
        line_two_total += x_size
      else:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray with the required spacing.\n"
            + "Remove a base from the list, reduce min_cutout_spacing, or use a wider tray."
        )
      left_idx += 1
    else:
      x_size = layout_sizes[right_idx][0]
      if _line_fits(line_two_total, len(line_two_indices), x_size, max_width, tolerance, min_spacing):
        line_two_indices.insert(0, right_idx)
        line_two_total += x_size
      elif _line_fits(line_one_total, len(line_one_indices), x_size, max_width, tolerance, min_spacing):
        line_one_indices.append(right_idx)
        line_one_total += x_size
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
      [sizes[i] for i in line_one_indices],
      tolerance,
      min_spacing,
      x_sizes=[layout_sizes[i][0] for i in line_one_indices],
  )

  for i, pos in enumerate(x_positions):
    idx = line_one_indices[i]
    pos['y'] = usable_area['min']['y'] + layout_sizes[idx][1] / 2
    if idx < len(edge_offsets):
      pos['y'] += edge_offsets[idx]
    pos['flipped'] = False

  if is_double_tray:
    y_positions = calculate_line_positions(
        usable_area,
        [sizes[i] for i in line_two_indices],
        tolerance,
        min_spacing,
        x_sizes=[layout_sizes[i][0] for i in line_two_indices],
    )

    for i, pos in enumerate(y_positions):
      idx = line_two_indices[i]
      pos['y'] = usable_area['max']['y'] - layout_sizes[idx][1] / 2
      if idx < len(edge_offsets):
        pos['y'] -= edge_offsets[idx]
      pos['flipped'] = True

    positions = x_positions + y_positions

    _validate_row_overlap(usable_area, x_positions, y_positions,
                          layout_sizes, line_one_indices, line_two_indices,
                          tolerance)
  else:
    positions = x_positions

  # A base deeper than the usable area cannot fit at all.
  usable_depth = usable_area['max']['y'] - usable_area['min']['y']
  for x_size, y_size in layout_sizes:
    if y_size > usable_depth + 0.001:
      raise ValueError(
          f"A base of depth {y_size}mm is too deep for the tray "
          f"(usable depth: {usable_depth:.1f}mm).\n"
          "Use a deeper tray, or for oval bases swap the size to "
          "DEPTHxWIDTH so the long axis runs along the tray."
      )

  return positions


def _validate_row_overlap(usable_area, front_positions, back_positions,
                          layout_sizes, front_indices, back_indices,
                          tolerance):
  """The front and back rows share the tray's middle: two cutouts resting
  on opposite edges collide when their combined depth exceeds the usable
  depth AND they overlap along x. Deep bases are fine as long as the two
  rows interleave in x."""
  usable_depth = usable_area['max']['y'] - usable_area['min']['y']

  for front, fi in zip(front_positions, front_indices):
    for back, bi in zip(back_positions, back_indices):
      # Vertical clearance between the physical holes (tolerance eats
      # tolerance/2 into the gap from each side). The standard tray runs
      # opposing rows as close as ~0.1mm by design, so only an actual
      # overlap counts.
      y_gap = (usable_depth - layout_sizes[fi][1] - layout_sizes[bi][1]
               - tolerance)
      if y_gap >= -0.001:
        continue
      # Rows are too deep to stack: only allowed if they don't share x.
      front_half = (layout_sizes[fi][0] + tolerance) / 2
      back_half = (layout_sizes[bi][0] + tolerance) / 2
      x_gap = abs(back['x'] - front['x']) - front_half - back_half
      if x_gap < MIN_ROW_GAP:
        raise ValueError(
            "Bases on the front and back rows overlap in the middle of "
            "the tray.\n"
            "The tray is too shallow to stack these bases: use a deeper "
            "tray, remove a base, or use --single-sided."
        )


def calculate_line_positions(
    usable_area,
    sizes,
    tolerance,
    min_spacing=2.0,
    x_sizes=None,
):
  """Spread one row of bases evenly along x.

  `x_sizes` optionally overrides the horizontal extent used for spacing
  (defaults to `sizes`); the returned 'size' key always carries the
  original scalar.
  """
  if x_sizes is None:
    x_sizes = list(sizes)

  positions = []
  x_size_total = sum(x_sizes)
  n = len(sizes)

  if n == 0:
    return positions

  max_width = usable_area['max']['x'] * 2

  # Reserve min_spacing for all n+1 gaps, distribute any extra space equally.
  available = max_width - x_size_total - (n - 1) * tolerance - (n + 1) * min_spacing
  gap = min_spacing + max(available, 0) / (n + 1)

  x = -usable_area['max']['x']
  for size, x_size in zip(sizes, x_sizes):
    x += gap + x_size / 2
    positions.append({'x': x, 'size': size})
    x += x_size / 2 + tolerance

  return positions
