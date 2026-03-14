# %% Libraries
from build123d import *
from ocp_vscode import *
import math
import copy
import argparse
import os
from collections import Counter
from functions.full_tray_generator import generate_full_tray


# %% User-Adjustable Parameters (Defaults)

diameters = [24.7, 49.6, 39.2, 49.6, 24.7, ]

total_width = 189.5  # Default: 189.5
total_depth = 66  # Default: 66.0
safety_margin = (6.5, 0.8)

floor_thickness = 0.4
base_heigth = 4.2
rail_height = 8.4
rail_width = 4.8

flap_center_gap = 0.2
flap_depth = 11.8

hinge_width = 2.8
hinge_height = 3.6
# Calculated from the edge of the center, not the flap
hinge_depth = 17.5
hinge_pin_radius = 1.4
hinge_pin_length = 3
bottom_chamfer = 0.4

hinge_lock_radius = 3.5
hinge_lock_offset = 0.4
hinge_lock_depth = 8.3

is_double_tray = True

base_tolerance = .55
epsilon = 0.001
custom_filename = "output/test_tray"


# %% Main execution

if __name__ == "__main__":
  import sys
  import io

  # Force unbuffered output (only works on command line, skip in Jupyter)
  try:
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', line_buffering=True)
  except AttributeError:
    # In Jupyter, sys.stdout doesn't have a 'buffer' attribute - that's fine, skip it
    pass

  try:
    # Detect if running in Jupyter/IPython
    is_jupyter = 'ipykernel' in sys.argv[0] or 'jupyter' in sys.argv[0].lower()

    # Check if running from command line (has diameters argument) and NOT in Jupyter
    if len(sys.argv) > 1 and not is_jupyter:
      parser = argparse.ArgumentParser(
          description="Generate a tray with custom base cutouts\n"
          + "Usage:   \"python tray_generator.py [diameters] [options]\"\n"
          + "Example: \"python tray_generator.py 24.7 24.7 24.7 24.7 24.7 24.7\"\n"
          + "Example: \"python tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4\"\n"
          + "Example: \"python tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4 --tolerance 0.6\"\n",
          formatter_class=argparse.RawDescriptionHelpFormatter
      )
      parser.add_argument(
          "diameters",
          type=float,
          nargs="+",
          help="Space-separated list of base diameters (e.g., 31.6 31.6 25.4)"
      )
      parser.add_argument(
          "--width",
          type=float,
          default=total_width,
          help=f"Total tray width (default: {total_width})"
      )
      parser.add_argument(
          "--depth",
          type=float,
          default=total_depth,
          help=f"Total tray depth (default: {total_depth})"
      )
      parser.add_argument(
          "--output",
          type=str,
          default=None,
          help="Output file path without extension (default: auto-generated from diameter summary)"
      )
      parser.add_argument(
          "--safety-margin-x",
          type=float,
          default=None,
          help=f"Horizontal safety margin from edges (default: {safety_margin[0]})"
      )
      parser.add_argument(
          "--safety-margin-y",
          type=float,
          default=None,
          help=f"Vertical safety margin from edges (default: {safety_margin[1]}). If generating a tray of bases around 32mm, you may have to lower this to 0.4."
      )
      parser.add_argument(
          "--tolerance",
          type=float,
          default=None,
          help=f"Tolerance for base fit (default: {base_tolerance})"
      )
      parser.add_argument(
          "--single-sided",
          action="store_true",
          help="Generate a single-sided tray (default: double-sided)"
      )

      args = parser.parse_args()

      # Override defaults with command line arguments
      diameters = args.diameters
      total_width = args.width
      total_depth = args.depth
      custom_output = args.output
      is_double_tray = not args.single_sided

      # Handle safety margins - use provided values or keep defaults
      margin_x = args.safety_margin_x if args.safety_margin_x is not None else safety_margin[0]
      margin_y = args.safety_margin_y if args.safety_margin_y is not None else safety_margin[1]
      safety_margin = (margin_x, margin_y)

      # Handle tolerance - use provided value or keep default
      if args.tolerance is not None:
        base_tolerance = args.tolerance
    else:
      # No arguments - use defaults
      custom_output = None

    # Create a summary of diameters (count how many of each size)
    diameter_count = Counter(diameters)
    diameter_summary = sorted(diameter_count.items())

    # Generate filename from diameter summary if not provided
    if custom_output:
      output_filename = custom_output
    else:
      # Create filename like "tray_31.6x10_25.4x5" from the diameter summary
      filename_parts = [
          f"{count}x{diameter}mm" for diameter, count in diameter_summary]
      output_filename = f"tray_{'_'.join(filename_parts)}"

    print("Generating", output_filename, flush=True)
    sys.stdout.flush()

    tray_compound, _ = generate_full_tray(
        diameters,
        safety_margin,
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
        epsilon,
        base_tolerance
    )
    print("Tray generated successfully", flush=True)
    sys.stdout.flush()

    try:
      show(tray_compound)
    except:
      pass

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    export_stl(tray_compound, f"output/{output_filename}.stl")
    print(f"Exported: output/{output_filename}.stl", flush=True)

    export_step(tray_compound, f"output/{output_filename}.step")
    print(f"Exported: output/{output_filename}.step", flush=True)

    print(f"{output_filename} complete", flush=True)

    # show(tray_compound)

  except Exception as e:
    error_message = str(e)

    # ANSI color codes for red text
    RED = "\033[91m"
    RESET = "\033[0m"

    # Check for math domain error - usually caused by mixing large and small diameter bases
    if "math domain error" in error_message.lower():
      print(f"{RED}Error: Cannot fit base configuration.{RESET}", flush=True)
      print(
          f"{RED}Mixing large base diameters (32mm+) with small base diameters (<32mm) requires{RESET}",
          flush=True)
      print(
          f"{RED}alternating them in the layout. Multiple small bases in a row causes geometric conflicts.{RESET}",
          flush=True)
      print(
          f"{RED}Try: Distribute smaller diameters throughout with larger ones in between.{RESET}",
          flush=True)
      print(
          f"{RED}Example: Instead of [25, 25, 40, 40], try [25, 40, 25, 40]{RESET}",
          flush=True)
    if "keyerror: 'flipped'" in error_message.lower():
      print(
          f"{RED}Error: System mirror the geometry of the base cutout for double sided trays.{RESET}",
          flush=True)
      print(
          f"{RED}This usually occurs when only one diameter is provided.{RESET}",
          flush=True)
      print(f"{RED}Try setting the flag \"--single-sided\".{RESET}", flush=True)
      print(
          f"{RED}(Note: You may then need to set --depth manually. Try --depth 132 for standard size.){RESET}",
          flush=True)
    else:
      print(f"{RED}Error: {type(e).__name__}: {e}{RESET}", flush=True)

    sys.stdout.flush()
    exit(1)

# %%
