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
   git clone <repository-url>
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

### Basic Usage

1. **Open the main script:**
   Open `Trays/tray_generator.py` in your Python IDE or VS Code

2. **Run the script:**
   - In VS Code with Python extension: Run the script with `F5` or use the Run button
   - From command line: `python Trays/tray_generator.py`

3. **View the 3D model:**
   - The script will display a 3D preview in VS Code if using the OCP VSCode extension
   - Generated files are saved to `Trays/output/`

### Customizing Your Tray

Edit the **User-Adjustable Parameters** section at the top of `tray_generator.py`:

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
is_double_tray = False     # Set to True for stacked tray configuration
cutout_edge_spacing = 0.8  # Distance of cutouts from edges (mm)
```

## Exporting Models

The script automatically exports generated models in two formats:

### STEP Format (STEP)
- Better for CAD software and CNC machines
- Preserves full geometry information
- File: `Trays/output/tray.step`

### STL Format (STL)
- Better for 3D printing
- Suitable for most slicing software
- File: `Trays/output/tray.stl`

To export only to a specific format, modify the `if __name__ == "__main__":` section at the bottom of `tray_generator.py`:

```python
# Export to STEP only
export_step(export_compound, "output/tray.step")

# Or export to STL only
export_stl(export_compound, "output/tray.stl")
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Alexander Bøhler (Seedback)

## Support & Contributions

For issues or suggestions, please refer to the project repository.
