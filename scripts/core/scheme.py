"""Scheme generation and evaluation - core functions from split_calc.py"""
from .splitter import split_with_limit, calc_balance, calc_scheme_balance
from .grid import validate_tile
from .constants import MAX_X, MAX_Y


# 方案排序键：成本 -> 独特尺寸 -> 瓦片数 -> 均衡度
SCHEME_SORT_KEY = lambda s: (s['cost'], s['unique_sizes'], s['total_tiles'], s['balance'])


def normalize_tiles(tiles):
    """Normalize tiles: rotate if width exceeds MAX_X but height fits"""
    normalized = []
    for w, h in tiles:
        if w > MAX_X and h <= MAX_Y:
            normalized.append((h, w))
        else:
            normalized.append((w, h))
    return normalized


def validate_tiles(tiles):
    """Validate all tiles are within limits"""
    return all(validate_tile(w, h) for w, h in tiles)


def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
    """Find best scheme for given grid dimensions"""
    from .grid import validate_tile as vt
    from .cost import calculate_print_cost

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
    return all_schemes[0]


def find_all_schemes(x, y):
    """Generate all valid split schemes for grid dimensions"""
    schemes = []

    # Try different x splits
    x_options = split_with_limit(x, 1, MAX_X)
    if not x_options:
        x_options = split_with_limit(x, 2, MAX_X)
    if not x_options:
        x_options = split_with_limit(x, 3, MAX_X)

    # Try different y splits
    y_options = split_with_limit(y, 1, MAX_Y)
    if not y_options:
        y_options = split_with_limit(y, 2, MAX_Y)
    if not y_options:
        y_options = split_with_limit(y, 3, MAX_Y)

    for x_split in x_options:
        for y_split in y_options:
            tiles = []
            for xs in x_split:
                for ys in y_split:
                    tiles.append((xs, ys))

            normalized = normalize_tiles(tiles)
            if validate_tiles(normalized):
                schemes.append({
                    'x_parts': len(x_split),
                    'y_parts': len(y_split),
                    'x_splits': x_split,
                    'y_splits': y_split,
                    'tiles': normalized,
                    'unique_sizes': len(set(normalized)),
                    'tile_count': len(normalized)
                })

    # Sort by unique sizes, then tile count, then balance
    schemes.sort(key=lambda s: (s['unique_sizes'], s['tile_count'], calc_scheme_balance(s['x_splits'], s['y_splits'])))
    return schemes
