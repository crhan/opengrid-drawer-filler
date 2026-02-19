"""Core constants for openGrid calculations"""

# Grid dimensions
TILE_SIZE = 28  # mm per cell
MIN_TILE = 2    # minimum tile size in cells
MAX_X = 10      # placeholder, set from config
MAX_Y = 11      # placeholder, set from config
MAX_Z = 325     # placeholder, set from config

# Tile thickness by type (mm)
TILE_THICKNESS = {
    "Full": 6.8,
    "Lite": 4.0,
    "Heavy": 13.8
}

# Calculated after config load
FULL_THICKNESS = 7.2  # default

# Filament estimates (based on实测数据)
FILAMENT_MAIN_PER_CELL = 1.13     # g/cell/layer
FILAMENT_SUPPORT_PER_CELL = 0.06  # g/cell/layer
PRINT_TIME_PER_CELL = 3.1         # minutes/cell/layer

# Swap penalty for color changes (minutes)
SWAP_PENALTY = 60

# Preset drawer sizes
PRESETS = {
    "klean": (270, 170, "Klean件盒"),
    "ikea-sunda": (360, 500, "IKEA Sunda"),
    "ikea-kal": (360, 500, "IKEA KAL"),
    "ikea-alex": (360, 500, "IKEA Alex"),
    "standard": (400, 400, "标准抽屉"),
    "small": (300, 300, "小抽屉"),
    "medium": (400, 400, "中抽屉"),
    "large": (500, 500, "大抽屉"),
}


def recalculate_derived_constants(tile_size=None, max_z=None, bed_x=None, bed_y=None,
                                  tile_type="Full", interface_separation=0.2,
                                  stacking_method="Ironing"):
    """Update derived constants from config"""
    global TILE_SIZE, MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS

    if tile_size is not None:
        TILE_SIZE = tile_size
    if max_z is not None:
        MAX_Z = max_z
    if bed_x is not None:
        MAX_X = bed_x // TILE_SIZE
    if bed_y is not None:
        MAX_Y = bed_y // TILE_SIZE

    # Calculate FULL_THICKNESS
    base_thickness = TILE_THICKNESS.get(tile_type, 6.8)
    if stacking_method == "Ironing":
        FULL_THICKNESS = base_thickness + 2 * interface_separation
    else:
        FULL_THICKNESS = base_thickness + 0.4 + 2 * interface_separation

    return {
        "TILE_SIZE": TILE_SIZE,
        "MAX_X": MAX_X,
        "MAX_Y": MAX_Y,
        "MAX_Z": MAX_Z,
        "FULL_THICKNESS": FULL_THICKNESS,
    }
