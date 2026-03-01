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


def get_max_stacks(printer_config):
    """Calculate maximum number of stacks based on Z height

    Args:
        printer_config: PrinterConfig instance with max_z and tile_thickness

    Returns:
        Maximum number of stacks that fit in Z height
    """
    max_z = printer_config.max_z
    thickness = printer_config.tile_thickness

    return int(max_z // thickness)


def get_grid_dimensions(width_mm, depth_mm, tile_size: int = TILE_SIZE):
    """Calculate available grid cells for drawer dimensions

    Args:
        width_mm: drawer width in mm
        depth_mm: drawer depth in mm
        tile_size: grid pitch in mm (default: TILE_SIZE constant)

    Returns:
        (x, y) number of cells in each dimension
    """
    x = width_mm // tile_size
    y = depth_mm // tile_size
    return x, y


def validate_tile(w, h, grid_config: GridConfig):
    """Validate if a tile size is within printer limits

    Args:
        w: tile width in cells
        h: tile height in cells
        grid_config: GridConfig instance with max_cells_x, max_cells_y

    Returns:
        True if tile is within limits
    """
    max_x = grid_config.max_cells_x
    max_y = grid_config.max_cells_y

    return grid_config.min_tile <= w <= max_x and grid_config.min_tile <= h <= max_y
