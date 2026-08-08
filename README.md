# LayerSafe - Parametric 3D Tray Generator

A Python-based parametric tray generator for the **LayerSafe** project—a modular storage system created by Newman (electrumbeaulo) on Discord.

This tool generates customizable 3D storage trays with hinged flaps using the [build123d](https://build123d.readthedocs.io/) CAD library.

## Features

LayerSafe generates parametric 3D tray designs featuring:
- Adjustable dimensions (width and depth)
- Hinged flap mechanisms for opening/closing
- Customizable rails and base structure
- Cutouts for **circular, square, hexagonal, and oval** bases, mixed sizes per tray
- Adjustable cutout wall angle (taper) to match sloped base edges
- Flap clearance so closed flaps rotate past seated bases
- Support for single or double tray configurations
- Manual base placement via editable layout files (see [Manual base placement](#manual-base-placement-layout-files))
- Export capabilities in STEP and STL formats

## Requirements

- Python 3.8+
- [build123d](https://github.com/gumyr/build123d) - CAD library for 3D modeling
- [OCP VSCode](https://github.com/gumyr/ocp-vscode) - VS Code integration for viewing 3D models

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/seedback/LayerSafe
   cd LayerSafe
   ```

2. **Install dependencies:**
   ```bash
   pip install build123d ocp-vscode
   ```

3. **Verify installation:**
   ```bash
   python -c "import build123d; print('build123d installed successfully')"
   ```

## Usage

### Command-Line Interface

The tray generator is designed to be run from the command line, making it easy for anyone to use without setting up an IDE.

#### Basic Syntax

```bash
python Trays/tray_generator.py <size1> <size2> ... [options]
```

Each size is one base. What "size" means depends on the cutout shape:

| Shape | `--cutout-shape` | Size measurement |
|-------|------------------|------------------|
| Circle (default) | `circle` | Base diameter |
| Square | `square` | Side length |
| Hexagon | `hex` | Across the flats |
| Oval | `oval` | `WIDTHxDEPTH` pair, e.g. `60x35` |

Hex cutouts are oriented with their flats facing the tray edges (corners pointing sideways), so measure your hex bases across the flats—the natural caliper measurement.

Oval sizes are given in tray orientation: width runs along the tray, depth front-to-back. If an oval is too deep for a row, swap the numbers (e.g. `35x60`) to stand it upright. Ovals too deep to sit in two straight rows are automatically nested against alternating edges when they fit (e.g. two 75x42 ovals on the standard tray).

Shapes can be mixed in one tray by prefixing individual sizes with a shape name, e.g. `oval:60x35` or `hex:25.4`. Sizes without a prefix use `--cutout-shape` (circle by default).

> **⚠️ Important:** Base sizes should be measured as accurately as possible. Precision down to **0.1mm** is recommended for proper fit. Use quality calipers with good accuracy (±0.1mm or better) to measure your bases before generating the tray.

#### Simple Examples

Generate a tray with 6 circles of 31.6mm diameter:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6
```

Generate a tray with mixed diameters (2× 25.4mm and 1× 31.6mm):
```bash
python Trays/tray_generator.py 25.4 25.4 31.6
```

Generate a tray for five 29.8mm (across flats) hex bases:
```bash
python Trays/tray_generator.py 29.8 29.8 29.8 29.8 29.8 --cutout-shape hex
```

Generate a tray for oval bases (60mm wide, 30mm deep):
```bash
python Trays/tray_generator.py 60x30 60x30 45x25 --cutout-shape oval
```

Mix shapes in one tray — one oval among circles (deep ovals among small circles usually need `--force-linear-positions`):
```bash
python Trays/tray_generator.py oval:60x35 24.7 24.7 24.7 24.7 --force-linear-positions
```

#### Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--width` | float | 189.5 | Total tray width in mm |
| `--depth` | float | 66.0 | Total tray depth in mm |
| `--cutout-shape` | choice | circle | Default cutout shape for unprefixed sizes: `circle`, `square`, `hex`, or `oval` |
| `--taper-angle` | float | shape default | Wall angle of the cutouts in degrees from vertical (default: 12.5 for circle, 5 for square/hex/oval). See [Matching sloped bases](#matching-sloped-bases) |
| `--flap-clearance` | float | 1.0 | Extra sideways clearance (mm per side) in the flap's part of square/hex/oval cutouts so the flap rotates closed past seated bases. Circle cutouts have their own rotation relief and ignore this |
| `--tolerance` | float | 0.55 | Fit tolerance added around each base (mm) |
| `--safety-margin-x` | float | 6.5 | Horizontal margin from edges (mm) |
| `--safety-margin-y` | float | 0.8 | Vertical margin from edges (mm) |
| `--min-cutout-spacing` | float | 2.0 | Minimum gap (mm) between adjacent cutout edges |
| `--edge-offsets` | space-separated floats | None | Edge offsets for each base (e.g., `0.5 0.5 0.5`) will reduce the depth of the base with the given amount without affecting the width. Useful for fine-tuning fit, especially on larger bases (mm) |
| `--edge-adjusts` | space-separated floats | None | Edge adjustments for each base (e.g., `0.2 0.2 0.2`), independent of edge-offsets for additional fine-tuning, a larger value will give a larger flat-spot below the curved section (mm) |
| `--single-sided` | flag | False | Generate a single-sided tray (default: double-sided) |
| `--force-linear-positions` | flag | False | Forces straight-row positioning (default: bases too deep to stack are automatically nested against alternating edges — exact tangency for circles, conservative bounding-box spacing for square/hex/oval) |
| `--layout` | string | None | Layout file (JSON) with manually placed bases; replaces the positional sizes and the automatic layout. See [Manual base placement](#manual-base-placement-layout-files) |
| `--export-layout` | string | None | Write the computed placement to this JSON file (editable, feed it back with `--layout`) |
| `--validate-only` | flag | False | Check the layout (bounds, overlaps) and exit without generating geometry; needs no CAD libraries |
| `--output` | string | auto | Output filename (without extension) |

#### Matching sloped bases

Many bases are narrower at the top than the bottom. Give the generator the **bottom** size and set the wall angle to match the slope:

```
taper_angle = atan((bottom_size - top_size) / (2 * base_height))
```

A positive angle narrows the cutout toward the top (the usual case); a negative angle widens it.

Example: hex bases measuring 29.8mm across flats at the bottom, 27.2mm at the top, 4mm tall → `atan(2.6 / 8)` ≈ 18°:

```bash
python Trays/tray_generator.py 29.8 29.8 29.8 29.8 29.8 --cutout-shape hex --taper-angle 18.0
```

The walls then keep the same clearance along the full height of the base.

#### Advanced Examples

Adjust safety margins for a tight fit:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4
```

Custom dimensions with tolerance adjustment:
```bash
python Trays/tray_generator.py 25.4 25.4 25.4 --width 200 --depth 80 --tolerance 0.6
```

Generate a single-sided tray (not double-sided):
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 --single-sided
```

Square bases with a reduced flap clearance:
```bash
python Trays/tray_generator.py 25.0 25.0 25.0 --cutout-shape square --flap-clearance 0.6
```

Apply edge offsets to customize base positioning:
```bash
python Trays/tray_generator.py 25.4 25.4 25.4 --edge-offsets 0.5 0.5 0.5
```

Specify a custom output filename:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 --output my_custom_tray
```

#### Manual base placement (layout files)

By default the generator decides where each base goes. With a **layout
file** you place them yourself: each base gets an explicit position
along the tray and a choice of which edge it rests on. The easiest way
to start is to let the generator lay the tray out once and export the
result:

```bash
# 1. Compute the automatic layout and save it (no geometry generated)
python Trays/tray_generator.py 24.7 24.7 31.6 --validate-only --export-layout my_tray.json

# 2. Edit my_tray.json - move bases, swap edges, add or remove bases

# 3. Check the edited layout (instant, no CAD needed)
python Trays/tray_generator.py --layout my_tray.json --validate-only

# 4. Generate the tray from it
python Trays/tray_generator.py --layout my_tray.json
```

A layout file looks like this:

```json
{
  "version": 1,
  "tray": { "width": 189.5, "depth": 66.0, "double_sided": true },
  "defaults": { "shape": "circle" },
  "bases": [
    { "size": 24.7, "x": -32.1, "edge": "front" },
    { "shape": "oval", "size": [60, 35], "x": 30.0, "edge": "back", "edge_offset": 0.5 }
  ]
}
```

- **Coordinates** are tray-centered millimeters: `x: 0` is the middle of
  the tray, positive to the right. `x` is the center of the cutout.
- **`edge`** is `front` or `back` (default `front`): which tray edge the
  base rests against. Every base sits against an edge — that is what the
  flap-retention geometry requires — so there is no `y` coordinate;
  free placement toward the middle of the tray is a planned follow-up
  (see [docs/feature-manual-placement.md](docs/feature-manual-placement.md)).
- **`size`** follows the CLI conventions: a number for circle/square/hex,
  a `[width, depth]` pair (or `"60x35"` string) for ovals. `shape`
  defaults to `defaults.shape` (circle if omitted).
- **`edge_offset`** / **`edge_adjust`** are the same per-base fine-tuning
  values as `--edge-offsets`/`--edge-adjusts`, attached to the base they
  belong to.
- Explicit CLI flags (`--width`, `--tolerance`, ...) override the file's
  `tray` settings.

Your positions are authoritative — the generator never repacks them. It
only validates: every base inside the usable area, no two cutouts
overlapping (opposing front/back bases may sit as close as the automatic
layout puts them). Validation errors name the offending base:

```
Error: Base 1 (24.7mm at x=-32.1) overlaps Base 2 (24.7mm at x=-25): their holes
need at least 0.4mm between edges but have -18.13mm.
Move the bases further apart.
```

#### Getting Help

View all available options:
```bash
python Trays/tray_generator.py --help
```

#### Output

Generated files are saved to `Trays/output/` (regardless of the directory you run the command from):
- **STL format** (`.stl`) — Suitable for 3D printing
- **STEP format** (`.step`) — Suitable for CAD software and CNC machines

Filenames are auto-generated from your size input (e.g., `tray_6x31.6mm.stl`), or you can specify a custom name with `--output`.

### Python IDE Usage (Optional)

To use in VS Code or another IDE:
1. Open `Trays/tray_generator.py`
2. Adjust the parameters in the "User-Adjustable Parameters" section (see below)
3. Run the script (VS Code: F5 or Run button)

### Customizing Tray Parameters

All tray geometry and generation defaults live in a single `TrayConfig` dataclass in `Trays/functions/tray_config.py` — dimensions, rail/flap/hinge geometry, cutout shape, taper, tolerances, and more. For deeper customization than the CLI exposes, either edit the defaults there or override individual fields in `tray_generator.py`:

```python
config = TrayConfig(
    total_width=200,        # Overall tray width (mm)
    rail_height=10.0,       # Height of side rails (mm)
    cutout_shape='hex',     # 'circle', 'square', or 'hex'
    is_double_tray=False,   # Single-sided tray
)
```

### Adding a new cutout shape

Shapes are pluggable: subclass `CutoutShape` in `Trays/functions/shapes.py`, implement `build()` (the 3D negative) and `circumradius()`, override `footprint()`/`layout_sizes()` if the shape's bounding box is not size × size, and register an instance in `SHAPES`. The CLI choices, layout, and orchestrator pick it up automatically.

## Building a UI on top (implementation notes)

Manual placement was designed as the backend for a drag-and-drop tray
editor. Notes for anyone building that UI:

**Interchange format.** The layout JSON (above) is the contract in both
directions: `--export-layout` gives the UI a valid starting arrangement
from any size list, and `--layout` turns an edited arrangement into a
tray. Round-tripping an unedited export reproduces the tray
byte-identically — `x` is written at full float precision on purpose, so
don't round it when re-serializing. Parsing/writing lives in
[Trays/functions/layout_io.py](Trays/functions/layout_io.py)
(`load_layout`, `parse_layout`, `build_layout`, `save_layout`).

**Interaction model.** In Phase 1 every base rests against the front or
back edge, so the canvas is two horizontal rails: horizontal drags
change `x`, a vertical drag flips `edge`. Every arrangement expressible
this way stays inside the geometry the cutout builders support (the
edge-resting assumption is what makes the flap retention and slide-path
geometry valid — see
[docs/feature-manual-placement.md](docs/feature-manual-placement.md)
for why, and for the Phase 2 plan that will add free `y`).

**Validating without the CAD stack.** Everything needed to check a
placement is pure math and importable without build123d (the CAD import
costs seconds; the math is instant — fine to run on every drag):

```python
import sys; sys.path.insert(0, "<repo>/Trays")
from functions.layout_io import parse_layout
from functions.layout_engine import compute_layout
from functions.tray_config import TrayConfig

layout = parse_layout(layout_dict)          # schema errors name the base
config = TrayConfig(**tray_overrides)
base_shapes, positions = compute_layout(    # ValueError names the base
    layout['sizes'], config,
    edge_offsets=layout['edge_offsets'],
    shapes=layout['shapes'],
    placements=layout['placements'])
```

`compute_layout` returns the final positions (`x`, `y`, `flipped`,
`index`) — the same values generation will use, so the UI can render the
true resting `y` without duplicating any formula. Omit `placements` to
get the automatic layout (that is all `--export-layout` does). If you'd
rather shell out than import, `--validate-only` is the same check as a
subprocess: exit 0 with a position listing, exit 1 with the naming error
on stdout. It runs on a bare Python without the CAD libraries installed.

**Rendering the canvas.** From the CAD-free modules:
- Placeable area: `layout_engine.calculate_usable_area(...)` — the
  rectangle base *footprints* must stay inside.
- Base outline: `shape.footprint(size, config.tolerance)` from
  `functions/shapes.py` gives each base's (x, y) bounding extent — the
  physical hole, the thing to draw and hit-test. A hex is ~1.155× wider
  than its across-flats size; draw footprints, not sizes.
- Spacing rules for live snapping: same-edge neighbors need 0.4 mm
  between hole edges (`MIN_EDGE_GAP` in
  `calculate_cutout_positions/validate_positions.py`); circle pairs
  measure edge distance by tangency, any pair involving a
  square/hex/oval by bounding boxes (`CutoutShape.nesting` says which).
  Opposing front/back bases are allowed to meet in the middle whenever
  the tray is nominally deep enough for both — don't hard-code a
  cross-row gap.

**Generation.** Shell out to
`python Trays/tray_generator.py --layout file.json [--output name]` (the
CAD stack makes in-process generation heavyweight); STL/STEP land in
`Trays/output/`. Layout and schema failures are `ValueError`s printed as
`Error: ...` with exit 1, and always name the base, so surfacing stderr
verbatim gives usable UI messages.

## Development

Run the test suite (pure-math layout tests, no CAD required for most):

```bash
pip install pytest
python -m pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Alexander Bøhler (Seedback)

## Support & Contributions

For issues or suggestions, please refer to the project repository.
