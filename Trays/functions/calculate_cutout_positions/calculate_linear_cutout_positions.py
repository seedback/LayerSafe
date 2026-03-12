# %%
import math

# %%


def calculate_linear_cutout_positions(
    usable_area,
    diameters,
    tolerance,
    is_double_tray=False,
):
  full_diameters = []
  for diameter in diameters:
    full_diameters.append(diameter + tolerance)
  
  line_one = []
  line_two = []

  max_width = usable_area['max']['x'] * 2
  line_one_total = 0
  line_two_total = 0

  left_idx = 0
  right_idx = len(diameters) - 1
  take_from_left = True

  # Alternate taking from start and end
  while left_idx <= right_idx:
    if take_from_left:
      diameter = diameters[left_idx]
      if line_one_total + diameter <= max_width:
        line_one.append(diameter)
        line_one_total += diameter
      elif is_double_tray and line_two_total + diameter <= max_width:
        line_two.append(diameter)
        line_two_total += diameter
      else:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray.\n"
            + "Remove a diameter from the list and try again."
        )
      left_idx += 1
    else:
      diameter = diameters[right_idx]
      if line_two_total + diameter <= max_width:
        line_two.insert(0, diameter)
        line_two_total += diameter
      elif line_one_total + diameter <= max_width:
        line_one.append(diameter)
        line_one_total += diameter
      else:
        raise ValueError(
            "Total width of bases is too wide to fit on the tray.\n"
            + "Remove a diameter from the list and try again."
        )
      right_idx -= 1

    if is_double_tray:
      take_from_left = not take_from_left

  x_positions = calculate_line_positions(
      usable_area,
      line_one
  )

  for pos in x_positions:
    pos['y'] = usable_area['min']['y'] + (pos['diameter']) / 2
    pos['flipped'] = False

  if is_double_tray:
    y_positions = calculate_line_positions(
        usable_area,
        line_two,
    )

    for pos in y_positions:
      pos['y'] = usable_area['max']['y'] - (pos['diameter']) / 2
      pos['flipped'] = True

    positions = x_positions + y_positions
  else:
    positions = x_positions

  return positions


def calculate_line_positions(
    usable_area,
    diameters,
):
  positions = []
  diameter_total = sum(diameters)

  if diameter_total > usable_area['max']['x']*2:
    raise ValueError(
        "Total width of bases is too wide to fit on the tray.\n"
        + "Remove a diameter from the list and try again."
    )

  if (len(diameters) == 0):
    pass
  elif (len(diameters) == 1):
    positions.append({
        'x': 0,
        'diameter': diameters[0],
    })
  else:
    remaining_space = usable_area['max']['x'] * 2 - diameter_total
    padding = remaining_space / len(diameters)
    current_x = 0

    for i, diameter in enumerate(diameters):
      pos = {'diameter': diameter}

      if i == 0:
        pos['x'] = -usable_area['max']['x'] + \
            (diameters[0]) / 2 + padding/2
      else:
        pos['x'] = current_x + diameters[i-1] / \
            2 + diameter/2 + padding
      current_x = pos['x']
      positions.append(pos)

  return positions
