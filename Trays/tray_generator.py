# %% Libraries
# Only CAD-free modules are imported at the top so that --validate-only
# and --help never pay for (or require) the CAD stack; build123d and the
# geometry pipeline are imported in the generation step below.
import argparse
import os
from functions.shapes import SHAPES, parse_base, format_base_summary
from functions.tray_config import TrayConfig
from functions.layout_engine import compute_layout
from functions.layout_io import load_layout, build_layout, save_layout


# %% User-Adjustable Parameters (Defaults)

# All tray geometry and layout defaults live in functions/tray_config.py
# (TrayConfig). Override individual fields here for IDE/Jupyter runs, e.g.:
#   config = TrayConfig(total_width=200, cutout_shape='circle')
config = TrayConfig()

sizes = [24.7, 49.6, 39.2, 49.6, 24.7, ]
# Optional per-base shape names, parallel to sizes; None (or a missing
# entry) uses config.cutout_shape. Example: ['oval', None, None].
shapes = []
edge_offsets = []
edge_adjusts = []
# Optional manual placement, parallel to sizes: each entry is
# {'x': <cutout center>, 'edge': 'front'|'back'}. None uses the
# automatic layout. Usually driven by --layout on the command line.
placements = None


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

    validate_only = False
    export_layout_path = None

    # Check if running from command line (has arguments) and NOT in Jupyter
    if len(sys.argv) > 1 and not is_jupyter:
      parser = argparse.ArgumentParser(
          description="Generate a tray with custom base cutouts\n"
          + "Usage:   \"python tray_generator.py [sizes] [options]\"\n"
          + "Example: \"python tray_generator.py 24.7 24.7 24.7 24.7 24.7 24.7\"\n"
          + "Example: \"python tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4\"\n"
          + "Example: \"python tray_generator.py --layout my_tray.json\"\n",
          formatter_class=argparse.RawDescriptionHelpFormatter
      )
      def base_argument(token):
        try:
          return parse_base(token)
        except ValueError as e:
          raise argparse.ArgumentTypeError(f"'{token}': {e}")

      parser.add_argument(
          "sizes",
          type=base_argument,
          nargs="*",
          help="Space-separated list of base sizes in mm: circle diameter, "
          "square side length, or hex across-flats (e.g., 31.6 31.6 25.4). "
          "Oval bases take WIDTHxDEPTH pairs (e.g., 60x35). Prefix a size "
          "with a shape name to mix shapes in one tray (e.g., oval:60x35 "
          "24.7 24.7); unprefixed sizes use --cutout-shape. Omit sizes "
          "when using --layout."
      )
      parser.add_argument(
          "--layout",
          type=str,
          default=None,
          help="Layout file (JSON) with manually placed bases; replaces "
          "the positional sizes and the automatic layout. Create a "
          "starting point with --export-layout."
      )
      parser.add_argument(
          "--export-layout",
          type=str,
          default=None,
          help="Write the computed placement to this JSON file (editable, "
          "feed it back with --layout)."
      )
      parser.add_argument(
          "--validate-only",
          action="store_true",
          help="Check the layout (bounds, overlaps) and exit without "
          "generating geometry; needs no CAD libraries."
      )
      parser.add_argument(
          "--width",
          type=float,
          default=None,
          help=f"Total tray width (default: {config.total_width})"
      )
      parser.add_argument(
          "--depth",
          type=float,
          default=None,
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

      validate_only = args.validate_only
      export_layout_path = args.export_layout
      custom_output = args.output

      if args.layout:
        # Manual placement from a layout file: bases, their fine-tuning,
        # and their placements all come from the file.
        if args.sizes:
          parser.error("--layout replaces the positional sizes; give one "
                       "or the other.")
        if args.edge_offsets is not None or args.edge_adjusts is not None:
          parser.error("--edge-offsets/--edge-adjusts belong inside the "
                       "layout file (per-base 'edge_offset'/'edge_adjust' "
                       "keys) when using --layout.")
        layout = load_layout(args.layout)
        sizes = layout['sizes']
        shapes = layout['shapes']
        edge_offsets = layout['edge_offsets']
        edge_adjusts = layout['edge_adjusts']
        placements = layout['placements']
        # Tray settings: explicit CLI flags win over the layout file,
        # which wins over TrayConfig defaults.
        tray = layout['tray']
        if 'width' in tray:
          config.total_width = tray['width']
        if 'depth' in tray:
          config.total_depth = tray['depth']
        if 'double_sided' in tray:
          config.is_double_tray = tray['double_sided']
        if layout['default_shape'] is not None:
          config.cutout_shape = layout['default_shape']
      else:
        if not args.sizes:
          parser.error("Give base sizes (e.g. 24.7 24.7 31.6) or a "
                       "--layout file.")
        shapes = [name for name, _ in args.sizes]
        sizes = [size for _, size in args.sizes]

        # Handle edge offsets - use provided values or keep default
        if args.edge_offsets is not None:
          edge_offsets = args.edge_offsets

        # Handle edge adjusts - use provided values or keep default
        if args.edge_adjusts is not None:
          edge_adjusts = args.edge_adjusts

      # Override config defaults (and layout-file settings) with
      # explicit command line arguments
      if args.width is not None:
        config.total_width = args.width
      if args.depth is not None:
        config.total_depth = args.depth
      if args.single_sided:
        config.is_double_tray = False
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
    else:
      # No arguments - use defaults
      custom_output = None

    # Generate filename from a summary of the bases if not provided,
    # like "tray_1xoval60x35mm_4x24.7mm".
    if custom_output:
      output_filename = custom_output
    else:
      output_filename = (
          f"tray_{format_base_summary(shapes, sizes, config.cutout_shape)}")

    if validate_only or export_layout_path:
      # Pure-math pass: resolve shapes and compute/check positions
      # without loading the CAD stack.
      base_shapes, positions = compute_layout(
          sizes, config, edge_offsets=edge_offsets, shapes=shapes,
          placements=placements)
      if export_layout_path:
        shape_names = [shape.name for shape in base_shapes]
        save_layout(export_layout_path,
                    build_layout(sizes, shape_names, positions, config,
                                 edge_offsets=edge_offsets,
                                 edge_adjusts=edge_adjusts))
        print(f"Layout written: {export_layout_path}", flush=True)
      if validate_only:
        print(f"Layout OK: {len(positions)} base(s) fit the tray.",
              flush=True)
        for pos in sorted(positions, key=lambda p: p['index']):
          edge = 'back' if pos['flipped'] else 'front'
          print(f"  Base {pos['index'] + 1}: x={pos['x']:.2f} "
                f"y={pos['y']:.2f} ({edge})", flush=True)
        sys.exit(0)

    # Generation needs the CAD stack; imported here so the steps above
    # stay CAD-free.
    from build123d import export_stl, export_step
    from functions.full_tray_generator import generate_full_tray

    print("Generating", output_filename, flush=True)
    sys.stdout.flush()

    tray_compound, _ = generate_full_tray(
        sizes,
        config,
        edge_offsets=edge_offsets,
        edge_adjusts=edge_adjusts,
        shapes=shapes,
        placements=placements,
    )
    print("Tray generated successfully", flush=True)
    sys.stdout.flush()

    try:
      from ocp_vscode import show
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
