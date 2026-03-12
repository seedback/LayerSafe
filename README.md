# LayerSafe - Parametric 3D Tray Generator

A Python-based parametric tray generator for the **LayerSafe** project—a modular storage system created by Newman (electrumbeaulo) on Discord.

This tool generates customizable 3D storage trays with hinged flaps using the [build123d](https://build123d.readthedocs.io/) CAD library.

## Features

LayerSafe generates parametric 3D tray designs featuring:
- Adjustable dimensions (width and depth)
- Hinged flap mechanisms for opening/closing
- Customizable rails and base structure
- Built-in cutouts for organization
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
python Trays/tray_generator.py <diameter1> <diameter2> ... [options]
```

> **⚠️ Important:** Base diameters should be measured as accurately as possible. Precision down to **0.1mm** is recommended for proper fit. Use quality calipers with good accuracy (±0.1mm or better) to measure your bases before generating the tray.

#### Simple Examples

Generate a tray with 6 circles of 31.6mm diameter:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6
```

Generate a tray with mixed diameters (2× 25.4mm and 1× 31.6mm):
```bash
python Trays/tray_generator.py 25.4 25.4 31.6
```

#### Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--width` | float | 189.5 | Total tray width in mm |
| `--depth` | float | 66.0 | Total tray depth in mm |
| `--safety-margin-x` | float | 6.5 | Horizontal margin from edges (mm) |
| `--safety-margin-y` | float | 0.8 | Vertical margin from edges (mm) |
| `--tolerance` | float | 0.55 | Tolerance for circle fit (mm) |
| `--output` | string | auto | Output filename (without extension) |

#### Advanced Examples

Adjust safety margins for a tight fit:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4
```

Custom dimensions with tolerance adjustment:
```bash
python Trays/tray_generator.py 25.4 25.4 25.4 --width 200 --depth 80 --tolerance 0.6
```

Specify a custom output filename:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 --output my_custom_tray
```

Combine all options:
```bash
python Trays/tray_generator.py 31.6 31.6 31.6 31.6 31.6 31.6 --safety-margin-y 0.4 --tolerance 0.6 --width 190 --output special_tray
```

#### Getting Help

View all available options:
```bash
python Trays/tray_generator.py --help
```

#### Output

Generated files are automatically saved to `Trays/output/`:
- **STL format** (`.stl`) — Suitable for 3D printing
- **STEP format** (`.step`) — Suitable for CAD software and CNC machines

Filenames are auto-generated based on your diameter input (e.g., `tray_6x31.6mm.stl`), or you can specify a custom name with `--output`.

### Jupyter Notebook (Optional)

If you prefer an interactive notebook environment:
1. Open `Trays/tray_generator.ipynb` in Jupyter
2. Modify the default parameters in the notebook and run cells
3. View the 3D model preview in the notebook output

### Python IDE Usage (Optional)

To use in VS Code or another IDE:
1. Open `Trays/tray_generator.py` 
2. Modify the default parameters in the "User-Adjustable Parameters" section
3. Run the script (VS Code: F5 or Run button)

### Customizing Tray Parameters

For more detailed customization, you can edit the **User-Adjustable Parameters** section in `tray_generator.py`:

```python
total_width = 189.5        # Overall tray width (mm)
total_depth = 66.0         # Overall tray depth (mm)
floor_thickness = 0.4      # Bottom thickness (mm)
base_height = 4.2          # Height of base section (mm)
rail_height = 8.4          # Height of side rails (mm)
rail_width = 4.8           # Width of side rails (mm)
flap_depth = 11.8          # Depth of hinged flap (mm)
flap_center_gap = 0.2      # Gap between flap and base (mm)
hinge_width = 2.8          # Width of hinge mechanism (mm)
hinge_height = 3.6         # Height of hinge mechanism (mm)
is_double_tray = True      # Set to True for stacked tray configuration
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Alexander Bøhler (Seedback)

## Support & Contributions

For issues or suggestions, please refer to the project repository.
