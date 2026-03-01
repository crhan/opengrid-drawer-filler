"""Grid dimension calculations"""
from dataclasses import dataclass

from .constants import TILE_SIZE, TILE_THICKNESS


@dataclass
class GridConfig:
    """网格分割配置"""
    max_cells_x: int      # bed_x // TILE_SIZE
    max_cells_y: int      # bed_y // TILE_SIZE
    tile_size: int = 28
    min_tile: int = 2


def get_max_stacks():
    """Calculate maximum number of stacks based on Z height"""
    from opengrid.config import get_printer_config_or_default
    from .constants import TILE_THICKNESS
    printer = get_printer_config_or_default()
    max_z = printer.get("max_z", 256)
    tile_type = "Full"  # TODO: make configurable
    base_thickness = TILE_THICKNESS.get(tile_type, 6.8)
    full_thickness = base_thickness + 0.4  # default with interface
    return int(max_z // full_thickness)


def get_grid_dimensions(width_mm, depth_mm):
    """Calculate available grid cells for drawer dimensions"""
    x = width_mm // TILE_SIZE
    y = depth_mm // TILE_SIZE
    return x, y


def validate_tile(w, h, grid_config: GridConfig = None):
    """Validate if a tile size is within printer limits

    Args:
        w: tile width in cells
        h: tile height in cells
        grid_config: optional GridConfig. If None, reads from config.
    """
    from .constants import MIN_TILE

    if grid_config is not None:
        max_x = grid_config.max_cells_x
        max_y = grid_config.max_cells_y
    else:
        from opengrid.config import get_printer_config_or_default
        printer = get_printer_config_or_default()
        bed_x = printer.get("bed_x", 256)
        bed_y = printer.get("bed_y", 256)
        max_x = bed_x // TILE_SIZE
        max_y = bed_y // TILE_SIZE

    return MIN_TILE <= w <= max_x and MIN_TILE <= h <= max_y
