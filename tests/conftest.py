import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The layout modules live under Trays/functions and are not an installed
# package yet, so make them importable both as top-level modules
# (calculate_cutout_positions.*) and as the package path used by the CLI
# (functions.*).
sys.path.insert(0, str(ROOT / "Trays"))
sys.path.insert(0, str(ROOT / "Trays" / "functions"))
