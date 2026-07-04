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

#### Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--width` | float | 189.5 | Total tray width in mm |
| `--depth` | float | 66.0 | Total tray depth in mm |
| `--cutout-shape` | choice | circle | Cutout shape: `circle`, `square`, `hex`, or `oval` |
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
