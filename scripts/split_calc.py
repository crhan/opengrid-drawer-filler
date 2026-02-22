"""Compatibility shim for split_calc - re-exports from new modules"""
# Re-export constants from opengrid.core
from opengrid.core import (
    TILE_SIZE, MAX_X, MAX_Y, MIN_TILE, MAX_Z, FULL_THICKNESS,
    TILE_THICKNESS, PRESETS as CORE_PRESETS,
)
# SWAP_PENALTY is defined in constants.py but not exported
SWAP_PENALTY = 60
from opengrid.core.grid import get_max_stacks, get_grid_dimensions, validate_tile
from opengrid.core.splitter import split_with_limit, calc_balance, calc_scheme_balance
from opengrid.core.scheme import find_best_scheme, find_all_schemes, normalize_tiles, validate_tiles
from opengrid.core.cost import calculate_print_cost, replan_with_inventory
from opengrid.core.stats import calculate_filament_and_time


# Override format_time with English-compatible version for tests
def format_time(minutes):
    """Format minutes to human readable string (English format for compatibility)"""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h{mins}m"
from opengrid.cli.utils import parse_dimensions, parse_batch_input

# Additional constants that were in old split_calc.py
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


def parse_preset(preset_name, copies=1):
    """Parse preset name to dimensions"""
    if preset_name in PRESETS:
        w, h, _ = PRESETS[preset_name]
        return [(w, h, copies)]
    return None


def calculate_single(width, depth, copies=1, verbose=False, index=None):
    """Calculate best scheme for a single dimension"""
    from opengrid.cli.formatters import print_plan

    x, y = get_grid_dimensions(width, depth)

    if x < MIN_TILE or y < MIN_TILE:
        return None

    scheme = find_best_scheme(x, y, verbose)

    if not scheme:
        return None

    return {
        'width': width,
        'depth': depth,
        'copies': copies,
        'grid': (x, y),
        'scheme': scheme,
        'index': index,
    }


# Legacy functions not in new codebase - provide minimal stubs
def merge_and_optimize(batch_results, drawer_names=None):
    """Legacy function - merge and optimize batch results"""
    if not batch_results:
        return {}
    # Simple pass-through for compatibility
    return {
        'merged_tiles': {},
        'unique_sizes': set(),
    }


def calculate_total_prints(batch_results, schemes):
    """Legacy function - calculate total prints"""
    total = 0
    for result in batch_results:
        if 'tile_count' in result:
            total += result.get('copies', 1) * result.get('tile_count', 0)
    return total


def optimize_batch_global(batch_results, inventory=None):
    """Legacy function - optimize batch globally"""
    return batch_results


# Backward compatibility exports
__all__ = [
    # Constants
    'TILE_SIZE', 'MAX_X', 'MAX_Y', 'MIN_TILE', 'MAX_Z', 'FULL_THICKNESS',
    'TILE_THICKNESS', 'PRESETS',
    # Functions from grid
    'get_max_stacks', 'get_grid_dimensions', 'validate_tile',
    # Functions from splitter
    'split_with_limit', 'calc_balance', 'calc_scheme_balance',
    # Functions from scheme
    'find_best_scheme', 'find_all_schemes', 'normalize_tiles', 'validate_tiles',
    # Functions from cost
    'calculate_print_cost', 'replan_with_inventory',
    # Functions from stats
    'calculate_filament_and_time', 'format_time',
    # Functions from utils
    'parse_dimensions', 'parse_batch_input', 'parse_preset',
    # Legacy functions
    'calculate_single', 'merge_and_optimize', 'calculate_total_prints',
    'optimize_batch_global',
]
