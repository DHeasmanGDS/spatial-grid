"""spatial-grid — generate local geophysical grids."""
from .core import GridSpec, Grid, generate_grid
from .config import load_config

__version__ = "0.1.0"
__all__ = ["GridSpec", "Grid", "generate_grid", "load_config"]
