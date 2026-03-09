# %% Libraries
import copy
import math
from build123d import *
from ocp_vscode import *
from base_tray_generator import generate_base_tray
from cutout_generator import generate_cutout

base_tray_storage = {}


def calculate_usable_area(
    total_width,
    total_depth,
    rail_width,
    safety_margin,
    is_double_tray,
    tolerance
):
  tol = tolerance/2
  usable_area_min = (
      -total_width/2 + rail_width + safety_margin[0],
      -total_depth/2 + safety_margin[1] + tol
  )
  usable_area_max = (
      total_width/2 - rail_width - safety_margin[0],
      total_depth/2 - safety_margin[1] - tol if is_double_tray else 0
  )
  return (usable_area_min, usable_area_max)


def calculate_cutout_positions(
    usable_area,
    diameters,
    tolerance,
    is_double_tray=False,
):
  positions = []

  for i, diameter in enumerate(diameters):
    radius = diameter / 2
    if i == 0:
      # First circle with bottom edge at the boundary
      x_pos = usable_area[0][0] + radius + tolerance/2
      y_pos = usable_area[0][1] + radius
    else:
      # Zigzag only for double trays, otherwise stay at bottom
      if is_double_tray:
        y_pos = usable_area[1][1] - radius if i % 2 == 1 else usable_area[0][1] + radius
      else:
        y_pos = usable_area[0][1] + radius

      # Get previous circle info
      prev_pos = positions[-1]
      prev_x = prev_pos['x']
      prev_y = prev_pos['y']
      prev_diameter = diameters[i - 1]
      prev_radius = prev_diameter / 2

      # Calculate horizontal spacing needed
      y_diff = abs(y_pos - prev_y)
      min_center_distance = prev_radius + radius + tolerance

      # For zigzag in double trays, try to align with previous circle (same x)
      if is_double_tray and i % 2 == 1:
        # Odd index: place directly above/below previous circle
        x_pos = prev_x
        # Check if this creates overlap
        distance = math.sqrt((x_pos - prev_x)**2 + (y_pos - prev_y)**2)
        if distance < min_center_distance:
          # If overlap, shift right
          x_distance = math.sqrt(max(0, min_center_distance**2 - y_diff**2))
          x_pos = prev_x + x_distance
      else:
        # Even index: calculate spacing based on Pythagorean theorem
        x_distance = math.sqrt(max(0, min_center_distance**2 - y_diff**2))
        x_pos = prev_x + x_distance

    # Check if circle fits within usable area
    if x_pos + radius + tolerance/2 > usable_area[1][0]:
      raise ValueError(
          f"Circle {i} (diameter={diameter}) doesn't fit in usable area. "
          f"Required x <= {usable_area[1][0]}, but got {x_pos + radius + tolerance/2}"
      )

    # Determine if this circle should be flipped (top edge in double tray)
    flipped = is_double_tray and i % 2 == 1

    positions.append({'x': x_pos, 'y': y_pos, 'diameter': diameter, 'flipped': flipped})

  # Spread positions equally across available width
  if len(positions) > 1:
    if is_double_tray:
      y_width = usable_area[1][1] - usable_area[0][1]
      half_y_width = y_width / 2
      max_diameter = max(diameters)
      min_diameter = min(diameters)
      
      # Use per-row spacing if: (1) all fit in half-width, OR (2) all circles are equal diameter
      if max_diameter < half_y_width or max_diameter == min_diameter:
        # Try per-row distribution first
        try:
          # Separate positions by row
          bottom_positions = [pos for pos in positions if not pos['flipped']]
          top_positions = [pos for pos in positions if pos['flipped']]
          
          # Redistribute bottom row with equal gaps
          if len(bottom_positions) > 1:
            total_diameter = sum(pos['diameter'] for pos in bottom_positions)
            available_width = usable_area[1][0] - usable_area[0][0] - tolerance
            gap = (available_width - total_diameter) / (len(bottom_positions) - 1)
            
            new_bottom = []
            current_x = usable_area[0][0] + tolerance / 2 + bottom_positions[0]['diameter'] / 2
            new_bottom.append({'x': current_x, 'y': bottom_positions[0]['y'], 'diameter': bottom_positions[0]['diameter'], 'flipped': False})
            
            for i in range(1, len(bottom_positions)):
              current_x += bottom_positions[i-1]['diameter'] / 2 + gap + bottom_positions[i]['diameter'] / 2
              new_bottom.append({'x': current_x, 'y': bottom_positions[i]['y'], 'diameter': bottom_positions[i]['diameter'], 'flipped': False})
          else:
            new_bottom = bottom_positions
          
          # Redistribute top row with equal gaps
          if len(top_positions) > 1:
            total_diameter = sum(pos['diameter'] for pos in top_positions)
            available_width = usable_area[1][0] - usable_area[0][0] - tolerance
            gap = (available_width - total_diameter) / (len(top_positions) - 1)
            
            new_top = []
            current_x = usable_area[0][0] + tolerance / 2 + top_positions[0]['diameter'] / 2
            new_top.append({'x': current_x, 'y': top_positions[0]['y'], 'diameter': top_positions[0]['diameter'], 'flipped': True})
            
            for i in range(1, len(top_positions)):
              current_x += top_positions[i-1]['diameter'] / 2 + gap + top_positions[i]['diameter'] / 2
              new_top.append({'x': current_x, 'y': top_positions[i]['y'], 'diameter': top_positions[i]['diameter'], 'flipped': True})
          else:
            new_top = top_positions
          
          # Check for cross-row overlaps
          if new_bottom and new_top:
            for b_pos in new_bottom:
              for t_pos in new_top:
                x1, y1 = b_pos['x'], b_pos['y']
                r1 = b_pos['diameter'] / 2
                x2, y2 = t_pos['x'], t_pos['y']
                r2 = t_pos['diameter'] / 2
                
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                min_distance = r1 + r2 + tolerance
                
                if distance < min_distance:
                  # Cross-row overlap detected, fall back to sequential placement
                  raise ValueError(f"Per-row spacing creates cross-row overlap")
          
          # Merge back in original order
          merged_positions = []
          bottom_idx = 0
          top_idx = 0
          for orig_pos in positions:
            if orig_pos['flipped']:
              merged_positions.append(new_top[top_idx])
              top_idx += 1
            else:
              merged_positions.append(new_bottom[bottom_idx])
              bottom_idx += 1
          
          positions = merged_positions
        except ValueError:
          # Per-row spacing failed (cross-row overlap), fall back to sequential placement
          total_diameter = sum(pos['diameter'] for pos in positions)
          available_width = usable_area[1][0] - usable_area[0][0] - tolerance
          
          # Use simple sequential placement with Pythagorean gap calculation
          result = []
          result.append(positions[0].copy())
          result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
          
          # Define a target gap (try to maximize it)
          for target_gap in range(int(available_width / (len(positions) - 1)), 0, -1):
            result = []
            result.append(positions[0].copy())
            result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
            
            valid = True
            for i in range(1, len(positions)):
              curr_r = positions[i]['diameter'] / 2
              prev_x = result[i-1]['x']
              prev_y = result[i-1]['y']
              prev_r = result[i-1]['diameter'] / 2
              
              curr_y = positions[i]['y']
              y_diff = abs(curr_y - prev_y)
              
              # Use the target gap with Pythagorean spacing
              center_dist = prev_r + target_gap + curr_r + tolerance
              x_dist_sq = center_dist**2 - y_diff**2
              
              if x_dist_sq < 0:
                valid = False
                break
              
              new_x = prev_x + math.sqrt(x_dist_sq)
              
              # Check bounds and overlaps
              if new_x + curr_r + tolerance/2 > usable_area[1][0]:
                valid = False
                break
              
              # Check against ALL previous circles for overlaps
              for j in range(i):
                x1 = result[j]['x']
                y1 = result[j]['y']
                r1 = result[j]['diameter'] / 2
                
                distance = math.sqrt((new_x - x1)**2 + (curr_y - y1)**2)
                min_distance = r1 + curr_r + tolerance
                
                if distance < min_distance:
                  valid = False
                  break
              
              if not valid:
                break
              
              result.append({
                  'x': new_x,
                  'y': curr_y,
                  'diameter': positions[i]['diameter'],
                  'flipped': positions[i]['flipped']
              })
            
            if valid:
              positions = result
              break
          else:
            # No valid gap found, use minimum pacing
            result = []
            result.append(positions[0].copy())
            result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
            
            for i in range(1, len(positions)):
              curr_r = positions[i]['diameter'] / 2
              curr_y = positions[i]['y']
              
              new_x = usable_area[0][0] + tolerance / 2 + curr_r
              
              # Check against ALL previous circles
              for j in range(i):
                prev_x = result[j]['x']
                prev_y = result[j]['y']
                prev_r = result[j]['diameter'] / 2
                y_diff = abs(curr_y - prev_y)
                
                min_center_dist = prev_r + curr_r + tolerance
                x_dist_sq = min_center_dist**2 - y_diff**2
                
                if x_dist_sq < 0:
                  raise ValueError(f"Circle {i} cannot fit without overlapping circle {j}")
                
                x_diff = math.sqrt(x_dist_sq)
                required_x = prev_x + x_diff
                new_x = max(new_x, required_x)
              
              if new_x + curr_r + tolerance/2 > usable_area[1][0]:
                raise ValueError(f"Circle {i} cannot fit in bounds")
              
              result.append({
                  'x': new_x,
                  'y': curr_y,
                  'diameter': positions[i]['diameter'],
                  'flipped': positions[i]['flipped']
              })
            
            positions = result
      else:
        # At least one diameter > half y-width: use sequential placement with Pythagorean spacing
        # This achieves equal edge-to-edge gaps while accounting for y-offset geometry
        total_diameter = sum(pos['diameter'] for pos in positions)
        available_width = usable_area[1][0] - usable_area[0][0] - tolerance
        
        # Use simple sequential placement with Pythagorean gap calculation
        result = []
        result.append(positions[0].copy())
        result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
        
        # Define a target gap (try to maximize it)
        for target_gap in range(int(available_width / (len(positions) - 1)), 0, -1):
          result = []
          result.append(positions[0].copy())
          result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
          
          valid = True
          for i in range(1, len(positions)):
            curr_r = positions[i]['diameter'] / 2
            prev_x = result[i-1]['x']
            prev_y = result[i-1]['y']
            prev_r = result[i-1]['diameter'] / 2
            
            curr_y = positions[i]['y']
            y_diff = abs(curr_y - prev_y)
            
            # Use the target gap with Pythagorean spacing
            center_dist = prev_r + target_gap + curr_r + tolerance
            x_dist_sq = center_dist**2 - y_diff**2
            
            if x_dist_sq < 0:
              valid = False
              break
            
            new_x = prev_x + math.sqrt(x_dist_sq)
            
            # Check bounds and overlaps
            if new_x + curr_r + tolerance/2 > usable_area[1][0]:
              valid = False
              break
            
            # Check against ALL previous circles for overlaps
            for j in range(i):
              x1 = result[j]['x']
              y1 = result[j]['y']
              r1 = result[j]['diameter'] / 2
              
              distance = math.sqrt((new_x - x1)**2 + (curr_y - y1)**2)
              min_distance = r1 + curr_r + tolerance
              
              if distance < min_distance:
                valid = False
                break
            
            if not valid:
              break
            
            result.append({
                'x': new_x,
                'y': curr_y,
                'diameter': positions[i]['diameter'],
                'flipped': positions[i]['flipped']
            })
          
          if valid:
            positions = result
            break
        else:
          # No valid gap found, use minimum pacing
          result = []
          result.append(positions[0].copy())
          result[0]['x'] = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
          
          for i in range(1, len(positions)):
            curr_r = positions[i]['diameter'] / 2
            curr_y = positions[i]['y']
            
            new_x = usable_area[0][0] + tolerance / 2 + curr_r
            
            # Check against ALL previous circles
            for j in range(i):
              prev_x = result[j]['x']
              prev_y = result[j]['y']
              prev_r = result[j]['diameter'] / 2
              y_diff = abs(curr_y - prev_y)
              
              min_center_dist = prev_r + curr_r + tolerance
              x_dist_sq = min_center_dist**2 - y_diff**2
              
              if x_dist_sq < 0:
                raise ValueError(f"Circle {i} cannot fit without overlapping circle {j}")
              
              x_diff = math.sqrt(x_dist_sq)
              required_x = prev_x + x_diff
              new_x = max(new_x, required_x)
            
            if new_x + curr_r + tolerance/2 > usable_area[1][0]:
              raise ValueError(f"Circle {i} cannot fit in bounds")
            
            result.append({
                'x': new_x,
                'y': curr_y,
                'diameter': positions[i]['diameter'],
                'flipped': positions[i]['flipped']
            })
          
          positions = result
    else:
      # Single tray: redistribute along bottom with equal gaps
      total_diameter = sum(pos['diameter'] for pos in positions)
      available_width = usable_area[1][0] - usable_area[0][0] - tolerance
      gap = (available_width - total_diameter) / (len(positions) - 1)
      
      new_positions = []
      current_x = usable_area[0][0] + tolerance / 2 + positions[0]['diameter'] / 2
      new_positions.append({'x': current_x, 'y': positions[0]['y'], 'diameter': positions[0]['diameter'], 'flipped': positions[0]['flipped']})
      
      for i in range(1, len(positions)):
        current_x += positions[i-1]['diameter'] / 2 + gap + positions[i]['diameter'] / 2
        new_positions.append({'x': current_x, 'y': positions[i]['y'], 'diameter': positions[i]['diameter'], 'flipped': positions[i]['flipped']})
      
      positions = new_positions

    # Validate no overlaps after redistribution (check ALL pairs)
    for i in range(len(positions)):
      for j in range(i + 1, len(positions)):
        x1 = positions[i]['x']
        y1 = positions[i]['y']
        r1 = positions[i]['diameter'] / 2

        x2 = positions[j]['x']
        y2 = positions[j]['y']
        r2 = positions[j]['diameter'] / 2

        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        min_distance = r1 + r2 + tolerance
        
        # Strict validation - no overlaps allowed
        if distance < min_distance:
          raise ValueError(
              f"Circles {i} and {j} overlap after redistribution. "
              f"Distance: {distance:.2f}, Required: {min_distance:.2f}"
          )

  return positions


# %%
def generate_full_tray(
    diameters=[],
    safety_margin=((0, 0.8)),
    total_width=189.5,
    total_depth=66.0,
    floor_thickness=0.4,
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
    hinge_lock_radius=3.5,
    hinge_lock_offset=0.4,
    hinge_lock_depth=8.3,
    is_double_tray=False,
    epsilon=0.001,
    tolerance=0.55,
    hinge_diameter=27.7,
    cutout_edge_spacing=.8,
):
  storage_key = ((total_width, total_depth), is_double_tray)

  # Create a base tray if one of the given dimmension doesn't exist
  # Grab a deep copy of the tray from storage
  if not storage_key in base_tray_storage:
    temp_tray = generate_base_tray(
        total_width,
        total_depth,
        floor_thickness,
        base_heigth,
        rail_height,
        rail_width,
        flap_center_gap,
        flap_depth,
        hinge_width,
        hinge_height,
        hinge_depth,
        hinge_pin_radius,
        hinge_pin_length,
        bottom_chamfer,
        hinge_lock_radius,
        hinge_lock_offset,
        hinge_lock_depth,
        is_double_tray,
        epsilon
    )
    base_tray_storage[storage_key] = temp_tray
  tray_compound = copy.deepcopy(base_tray_storage[storage_key])

  usable_area = calculate_usable_area(
      total_width,
      total_depth,
      rail_width,
      safety_margin,
      is_double_tray,
      tolerance
  )

  positions = calculate_cutout_positions(usable_area, diameters, tolerance, is_double_tray)
  
  for i, pos in enumerate(positions):
    if i > 0:
      prev = positions[i-1]
      # 2D euclidean distance between centers
      center_dist = math.sqrt((pos['x'] - prev['x'])**2 + (pos['y'] - prev['y'])**2)
      # Edge-to-edge gap (tolerance subtracted once total)
      edge_gap = center_dist - pos['diameter']/2 - prev['diameter']/2 - tolerance
  
  cutouts_list = []

  for position in positions:
    cutout = (generate_cutout(
        position['diameter'],
        tolerance,
        flap_depth,
        hinge_diameter,
        flap_center_gap,
        cutout_edge_spacing,
        epsilon
    ))
    
    # Rotate 180 degrees if flipped (for top edge circles)
    if position['flipped']:
      cutout = cutout.rotate(Axis.Z, 180)
    
    cutout = cutout.translate((position['x'], position['y'], floor_thickness))
    
    cutouts_list.append(cutout)
  
  if cutouts_list:
    cutouts = Compound(cutouts_list)
    tray_compound -= cutouts

  return tray_compound


# %%
# if __name__ == "__main__":
  # tray_compound = generate_full_tray(
  #     [31.6,31.6,31.6,31.6,31.6,31.6,31.6,31.6,31.6,31.6],
  #     is_double_tray=True
  # )
  # tray_compound = generate_full_tray(
  #     [24.7,24.7,24.7,24.7,24.7,24.7,24.7,24.7,24.7,24.7,24.7,24.7,],
  #     is_double_tray=True
  # )
  # tray_compound = generate_full_tray(
  #     [49.5,31.2,39.3,39.3,39.3],
  #     is_double_tray=True
  # )
  
  
  # show(tray_compound)

# %%
if __name__ == "__main__":
  tray_compound = generate_full_tray(
      [28.1, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7],
      is_double_tray=True
  )
  
  show(tray_compound)
  
  export_stl(tray_compound, "../output/tray_1x28.1mm_11x24.7mm.stl")
  export_step(tray_compound, "../output/tray_1x28.1mm_11x24.7mm.step")
  
# %%
if __name__ == "__main__":
  tray_compound = generate_full_tray(
      [24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7, 24.7],
      is_double_tray=True
  )
  
  show(tray_compound)
  
  export_stl(tray_compound, "../output/tray_12x24.7mm.stl")
  export_step(tray_compound, "../output/tray_12x24.7mm.step")
  
# %%
if __name__ == "__main__":
  tray_compound = generate_full_tray(
      [39.3, 39.3, 39.3, 39.3, 39.3],
      is_double_tray=True
  )
  
  show(tray_compound)
  
  export_stl(tray_compound, "../output/tray_5x39.3mm.stl")
  export_step(tray_compound, "../output/tray_5x39.3mm.step")
  
# %%
