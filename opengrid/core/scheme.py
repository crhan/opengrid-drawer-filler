"""Scheme generation and evaluation - core functions from split_calc.py"""
from .splitter import split_with_limit, calc_balance, calc_scheme_balance
from .grid import validate_tile, GridConfig
from opengrid.config import get_printer_config_or_default
from .constants import TILE_SIZE


# 方案排序键：成本 -> 独特尺寸 -> 瓦片数 -> 均衡度
SCHEME_SORT_KEY = lambda s: (s['cost'], s['unique_sizes'], s['total_tiles'], s['balance'])


def normalize_tiles(tiles, grid_config: GridConfig = None):
    """Normalize tiles: rotate if it makes the tile valid

    Args:
        tiles: list of (width, height) tuples
        grid_config: optional GridConfig. If None, reads from config.
    """
    from opengrid.config import get_printer_config_or_default
    from .constants import TILE_SIZE

    if grid_config is not None:
        max_x = grid_config.max_cells_x
        max_y = grid_config.max_cells_y
        min_tile = grid_config.min_tile
    else:
        printer = get_printer_config_or_default()
        bed_x = printer.get("bed_x", 256)
        bed_y = printer.get("bed_y", 256)
        max_x = bed_x // TILE_SIZE
        max_y = bed_y // TILE_SIZE
        min_tile = 2

    normalized = []
    for w, h in tiles:
        # Original valid
        if min_tile <= w <= max_x and min_tile <= h <= max_y:
            normalized.append((w, h))
        # Rotated valid (symmetric check)
        elif min_tile <= h <= max_x and min_tile <= w <= max_y:
            normalized.append((h, w))
        else:
            # Invalid, keep original (will fail validation later)
            normalized.append((w, h))
    return normalized


def validate_tiles(tiles):
    """Validate all tiles are within limits"""
    return all(validate_tile(w, h) for w, h in tiles)


def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
    """Find best scheme for given grid dimensions"""
    from .grid import validate_tile as vt
    from .cost import calculate_print_cost

    # Get printer limits from config
    printer = get_printer_config_or_default()
    max_x = printer.get("bed_x", 256) // TILE_SIZE
    max_y = printer.get("bed_y", 256) // TILE_SIZE

    # Check if no split needed
    if vt(x, y):
        return {
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
            'unique_sizes': 1,
            'tile_count': 1,
            'cost': 0,
            'from_inventory': {},
            'need_print': {} if inventory is None else {f"{x}x{y}": 1}
        }

    # Find all schemes and score them
    if inventory:
        all_schemes = find_all_schemes(x, y)
        scored = []
        for scheme in all_schemes:
            cost, from_inv, need_print = calculate_print_cost(scheme['tiles'], inventory, copies)
            unique_sizes = len(set(scheme['tiles']))
            total_tiles = len(scheme['tiles'])
            balance = calc_scheme_balance(scheme['x_splits'], scheme['y_splits'])

            scored.append({
                'scheme': scheme,
                'cost': cost,
                'from_inventory': from_inv,
                'need_print': need_print,
                'unique_sizes': unique_sizes,
                'total_tiles': total_tiles,
                'balance': balance
            })

        scored.sort(key=SCHEME_SORT_KEY)
        best_scored = scored[0]

        best = best_scored['scheme'].copy()
        best.update({
            'cost': best_scored['cost'],
            'from_inventory': best_scored['from_inventory'],
            'need_print': best_scored['need_print'],
            'unique_sizes': best_scored['unique_sizes'],
            'tile_count': best_scored['total_tiles'],
            'balance': best_scored['balance']
        })
        return best

    # No inventory - find simplest scheme
    all_schemes = find_all_schemes(x, y)
    if not all_schemes:
        return None

    all_schemes.sort(key=lambda s: (len(set(s['tiles'])), len(s['tiles']), calc_scheme_balance(s['x_splits'], s['y_splits'])))
    best = all_schemes[0].copy()
    best['unique_sizes'] = len(set(best['tiles']))
    best['tile_count'] = len(best['tiles'])
    best['balance'] = calc_scheme_balance(best['x_splits'], best['y_splits'])

    # If x != y, also check rotated direction
    if x != y:
        rotated_schemes = find_all_schemes(y, x)
        if rotated_schemes:
            rotated_schemes.sort(key=lambda s: (len(set(s['tiles'])), len(s['tiles']), calc_scheme_balance(s['x_splits'], s['y_splits'])))
            rotated = rotated_schemes[0]

            # Normalize rotated tiles
            normalized_tiles = normalize_tiles(rotated['tiles'], max_x, max_y)

            # Check if normalized tiles are valid
            if validate_tiles(normalized_tiles):
                rotated_best = {
                    'x_parts': rotated['y_parts'],
                    'y_parts': rotated['x_parts'],
                    'x_splits': rotated['y_splits'],
                    'y_splits': rotated['x_splits'],
                    'tiles': normalized_tiles,
                    'unique_sizes': len(set(normalized_tiles)),
                    'tile_count': len(normalized_tiles),
                    'balance': calc_scheme_balance(rotated['y_splits'], rotated['x_splits'])
                }

                # Compare: use rotated if it's better
                if (rotated_best['unique_sizes'] < best['unique_sizes'] or
                    (rotated_best['unique_sizes'] == best['unique_sizes'] and rotated_best['tile_count'] < best['tile_count']) or
                    (rotated_best['unique_sizes'] == best['unique_sizes'] and rotated_best['tile_count'] == best['tile_count'] and rotated_best['balance'] < best['balance'])):
                    best = rotated_best

    return best


def find_all_schemes(x, y, max_schemes=2000):
    """Generate all valid split schemes for grid dimensions

    Uses intelligent search range:
    - Small grids: x_search = 1..min(8, x+1), y_search = 1..min(5, y+1)
    - Large grids: search around minimum required splits +/- 1
    """
    # Get printer limits from config
    printer = get_printer_config_or_default()
    max_x = printer.get("bed_x", 256) // TILE_SIZE
    max_y = printer.get("bed_y", 256) // TILE_SIZE

    # Check if no split needed
    if validate_tile(x, y):
        return [{
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
        }]

    schemes = []

    # Calculate minimum required splits
    min_x_parts = max(1, int((x + max_x - 1) // max_x))
    min_y_parts = max(1, int((y + max_y - 1) // max_y))

    # Intelligent search range
    if min_x_parts >= 6 or min_y_parts >= 5:
        # Large grid: search around minimum required splits +/- 1
        x_search = range(max(1, min_x_parts - 1), min_x_parts + 2)
        y_search = range(max(1, min_y_parts - 1), min_y_parts + 2)
    else:
        # Small grid: use wider search range
        x_search = range(1, min(8, x + 1))
        y_search = range(1, min(5, y + 1))

    for x_parts in x_search:
        for y_parts in y_search:
            # Early termination if we have enough schemes
            if len(schemes) >= max_schemes:
                break

            total_tiles = x_parts * y_parts
            # Limit total tiles to prevent combinatorial explosion
            min_required = min_x_parts * min_y_parts
            max_allowed = max(28, min_required)
            if total_tiles > max_allowed:
                continue

            # Limit split results to prevent combination explosion
            x_splits = split_with_limit(x, x_parts, max_x, max_results=500)
            if not x_splits:
                continue

            y_splits = split_with_limit(y, y_parts, max_y, max_results=500)
            if not y_splits:
                continue

            for xs in x_splits:
                # Early termination check
                if len(schemes) >= max_schemes:
                    break

                for ys in y_splits:
                    tiles = []
                    valid = True
                    for xd in xs:
                        for yd in ys:
                            if not validate_tile(xd, yd):
                                valid = False
                                break
                            tiles.append((xd, yd))

                    if not valid:
                        continue

                    # Normalize tiles
                    normalized = normalize_tiles(tiles, max_x, max_y)

                    schemes.append({
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': normalized,
                    })

                    # Early termination check
                    if len(schemes) >= max_schemes:
                        break

    # Sort by unique sizes, then tile count, then balance
    schemes.sort(key=lambda s: (len(set(s['tiles'])), len(s['tiles']), calc_scheme_balance(s['x_splits'], s['y_splits'])))
    return schemes
