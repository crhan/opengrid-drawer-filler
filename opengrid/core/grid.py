"""Grid dimension calculations"""
from .constants import TILE_SIZE, MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS


def get_max_stacks():
    """Calculate maximum number of stacks based on Z height"""
    return int(MAX_Z // FULL_THICKNESS)


def get_grid_dimensions(width_mm, depth_mm):
    """Calculate available grid cells for drawer dimensions"""
    x = width_mm // TILE_SIZE
    y = depth_mm // TILE_SIZE
    return x, y


def validate_tile(w, h):
    """Validate if a tile size is within printer limits"""
    from .constants import MIN_TILE
    return MIN_TILE <= w <= MAX_X and MIN_TILE <= h <= MAX_Y
