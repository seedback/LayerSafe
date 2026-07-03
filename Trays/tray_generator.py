# %% Libraries
from build123d import *
from ocp_vscode import *
import argparse
import os
from collections import Counter
from functions.full_tray_generator import generate_full_tray
from functions.shapes import SHAPES
from functions.tray_config import TrayConfig


# %% User-Adjustable Parameters (Defaults)

# All tray geometry and layout defaults live in functions/tray_config.py
# (TrayConfig). Override individual fields here for IDE/Jupyter runs, e.g.:
#   config = TrayConfig(total_width=200, cutout_shape='circle')
config = TrayConfig()

sizes = [24.7, 49.6, 39.2, 49.6, 24.7, ]
edge_offsets = []
edge_adjusts = []


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

    # Check if running from command line (has sizes argument) and NOT in Jupyter
    if len(sys.argv) > 1 and not is_jupyter:
      parser = argparse.ArgumentParser(
          description="Generate a tray with custom base cutouts\n"
          + "Usage:   \"python tray_generator.py [sizes] [options]\"\n"
          + "Example: \"python tray_generator.py 24.7 24.7 24.7 24.7 24.7 24.7\"\n"
          + "Example: \"python tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4\"\n"
          + "Example: \"python tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4 --tolerance 0.6\"\n",
          formatter_class=argparse.RawDescriptionHelpFormatter
      )
      parser.add_argument(
          "sizes",
          type=float,
          nargs="+",
          help="Space-separated list of base sizes: circle diameter or square side length, in mm (e.g., 31.6 31.6 25.4)"
      )
      parser.add_argument(
          "--width",
          type=float,
          default=config.total_width,
          help=f"Total tray width (default: {config.total_width})"
      )
      parser.add_argument(
          "--depth",
          type=float,
          default=config.total_depth,
          help=f"Total tray depth (default: {config.total_depth})"
      )
      parser.add_argument(
          "--output",
          type=str,
          default=None,
          help="Output file path without extension (default: auto-generated from size summary)"
      )
      parser.add_argument(
          "--safety-margin-x",
          type=float,
          default=None,
          help=f"Horizontal safety margin from edges (default: {config.safety_margin[0]})"
      )
      parser.add_argument(
          "--safety-margin-y",
          type=float,
          default=None,
          help=f"Vertical safety margin from edges (default: {config.safety_margin[1]}). If generating a tray of bases around 32mm, you may have to lower this to 0.4."
      )
      parser.add_argument(
          "--tolerance",
          type=float,
          default=None,
          help=f"Tolerance for base fit (default: {config.tolerance})"
      )
      parser.add_argument(
          "--edge-offsets",
          type=float,
          nargs="*",
          default=None,
          help="Space-separated edge offsets for each base (e.g., 0.5 0.5 0.5)"
      )
      parser.add_argument(
          "--edge-adjusts",
          type=float,
          nargs="*",
          default=None,
          help="Space-separated edge adjustments for each base (independent of edge-offsets)"
      )
      parser.add_argument(
          "--single-sided",
          action="store_true",
          help="Generate a single-sided tray (default: double-sided)"
      )
      parser.add_argument(
          "--cutout-shape",
          type=str,
          default=None,
          choices=sorted(SHAPES),
          help=f"Cutout shape (default: {config.cutout_shape})"
      )
      parser.add_argument(
          "--taper-angle",
          type=float,
          default=None,
          help="Wall angle of the cutouts in degrees from vertical "
          "(default: 12.5 for circle, 5 for square/hex). Positive narrows "
          "the cutout toward the top. To match a measured base: "
          "atan((bottom_size - top_size) / (2 * base_height)), e.g. a base "
          "29.8mm at the bottom, 27.2mm at the top and 4mm tall needs "
          "atan(2.6/8) = 18 degrees."
      )
      parser.add_argument(
          "--flap-clearance",
          type=float,
          default=None,
          help="Extra sideways clearance (mm per side) in the flap's part "
          "of square/hex cutouts so the flap can rotate closed past a "
          f"seated base (default: {config.flap_clearance}). Circle "
          "cutouts have their own rotation relief and ignore this."
      )
      parser.add_argument(
          "--min-cutout-spacing",
          type=float,
          default=None,
          help=f"Minimum gap (mm) between adjacent cutout edges (default: {config.min_cutout_spacing})"
      )
      parser.add_argument(
          "--force-linear-positions",
          action="store_true",
          help="Forces the use of linear positioning as opposed to alternating"
      )

      args = parser.parse_args()

      # Override config defaults with command line arguments
      sizes = args.sizes
      config.total_width = args.width
      config.total_depth = args.depth
      custom_output = args.output
      config.is_double_tray = not args.single_sided
      if args.cutout_shape is not None:
        config.cutout_shape = args.cutout_shape
      if args.min_cutout_spacing is not None:
        config.min_cutout_spacing = args.min_cutout_spacing
      if args.taper_angle is not None:
        config.taper_angle = args.taper_angle
      if args.flap_clearance is not None:
        config.flap_clearance = args.flap_clearance
      config.force_linear_positions = args.force_linear_positions

      # Handle safety margins - use provided values or keep defaults
      margin_x = args.safety_margin_x if args.safety_margin_x is not None else config.safety_margin[0]
      margin_y = args.safety_margin_y if args.safety_margin_y is not None else config.safety_margin[1]
      config.safety_margin = (margin_x, margin_y)

      # Handle tolerance - use provided value or keep default
      if args.tolerance is not None:
        config.tolerance = args.tolerance

      # Handle edge offsets - use provided values or keep default
      if args.edge_offsets is not None:
        edge_offsets = args.edge_offsets

      # Handle edge adjusts - use provided values or keep default
      if args.edge_adjusts is not None:
        edge_adjusts = args.edge_adjusts
    else:
      # No arguments - use defaults
      custom_output = None

    # Create a summary of sizes (count how many of each size)
    size_count = Counter(sizes)
    size_summary = sorted(size_count.items())

    # Generate filename from size summary if not provided
    if custom_output:
      output_filename = custom_output
    else:
      # Create filename like "tray_31.6x10_25.4x5" from the size summary
      filename_parts = [
          f"{count}x{size}mm" for size, count in size_summary]
      output_filename = f"tray_{'_'.join(filename_parts)}"

    print("Generating", output_filename, flush=True)
    sys.stdout.flush()

    tray_compound, _ = generate_full_tray(
        sizes,
        config,
        edge_offsets=edge_offsets,
        edge_adjusts=edge_adjusts,
    )
    print("Tray generated successfully", flush=True)
    sys.stdout.flush()

    try:
      show(tray_compound)
    except Exception:
      pass

    # Export next to this script, regardless of the current working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")
    stl_path = os.path.join(output_dir, f"{output_filename}.stl")
    step_path = os.path.join(output_dir, f"{output_filename}.step")
    os.makedirs(os.path.dirname(stl_path), exist_ok=True)

    export_stl(tray_compound, stl_path)
    print(f"Exported: {stl_path}", flush=True)

    export_step(tray_compound, step_path)
    print(f"Exported: {step_path}", flush=True)

    print(f"{output_filename} complete", flush=True)

    # show(tray_compound)

  except Exception as e:
    error_message = str(e)

    # ANSI color codes for red text
    RED = "\033[91m"
    RESET = "\033[0m"

    # Check for math domain error - usually caused by mixing large and small size bases
    if "math domain error" in error_message.lower():
      message = ("Cannot fit base configuration.\n"
          "Mixing large base sizes (32mm+) with small base sizes (<32mm) requires\n"
          "alternating them in the layout. Multiple small bases in a row causes geometric conflicts.\n"
          "Try: Distribute smaller sizes throughout with larger ones in between.\n"
          "Example: Instead of [25, 25, 40, 40], try [25, 40, 25, 40]\n"
          "Try: Setting the flag \"--force-linear-positions\".")
    elif isinstance(e, KeyError) and "flipped" in error_message.lower():
      message = ("System mirrors the geometry of the base cutout for double sided trays.\n"
          "This usually occurs when only one size is provided.\n"
          "Try: Setting the flag \"--single-sided\".\n"
          "(Note: You may then need to set --depth manually. Try --depth 132 for standard size.)")
    elif isinstance(e, ValueError):
      # Layout errors already carry a user-friendly message
      message = error_message
    else:
      message = f"{type(e).__name__}: {error_message}"

    print(f"{RED}Error: {message}{RESET}", flush=True)
    sys.exit(1)

# %%
