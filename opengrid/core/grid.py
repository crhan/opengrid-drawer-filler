"""Grid dimension calculations"""
from .constants import TILE_SIZE, TILE_THICKNESS


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


def validate_tile(w, h):
    """Validate if a tile size is within printer limits"""
    from opengrid.config import get_printer_config_or_default
    from .constants import MIN_TILE, TILE_THICKNESS
    printer = get_printer_config_or_default()
    bed_x = printer.get("bed_x", 256)
    bed_y = printer.get("bed_y", 256)
    max_x = bed_x // TILE_SIZE
    max_y = bed_y // TILE_SIZE
    return MIN_TILE <= w <= max_x and MIN_TILE <= h <= max_y
