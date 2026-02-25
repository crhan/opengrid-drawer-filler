"""Cost calculation functions"""
from .constants import FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL, PRINT_TIME_PER_CELL, SWAP_PENALTY


def calculate_print_cost(tiles, inventory, copies):
    """Calculate print cost (in time minutes) and inventory usage

    Returns: (cost, from_inventory, need_print)
        - cost: total time cost in minutes, 0 means fully using inventory
        - from_inventory: tiles taken from inventory {"6x7": 2, ...}
        - need_print: tiles that need printing {"6x7": 1, ...}
    """
    # Count tiles (normalize key: smaller number first, e.g., 6x9 not 9x6)
    tile_counts = {}
    for w, h in tiles:
        key = f"{min(w, h)}x{max(w, h)}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}

    # Calculate inventory match
    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0) if inventory else 0
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    # Calculate time cost for printing
    total_time = 0
    total_prints = len(need_print)  # Each unique size needs one print

    for key, count in need_print.items():
        if count > 0:
            w, h = map(int, key.split('x'))
            cells = w * h
            # Calculate time: cells * time per cell * stacks (count)
            time_min = cells * PRINT_TIME_PER_CELL * count
            total_time += time_min

    # Add swap penalty (between each unique print)
    if total_prints > 1:
        total_time += (total_prints - 1) * SWAP_PENALTY

    return total_time, from_inventory, need_print


def replan_with_inventory(tiles: list, inventory: dict, copies: int = 1, grid: tuple = None):
    """
    当库存尺寸不匹配时，重新规划方案以最大化利用库存

    Args:
        tiles: 原始瓦片需求 [(w,h), ...]
        inventory: 可用库存 {"6x7": 3, ...}
        copies: 打印份数
        grid: 可选的网格尺寸 (width, height)

    Returns:
        重新规划后的方案，或 None（如果不需要重新规划）
    """
    from .scheme import find_all_schemes

    # Calculate direct match cost
    direct_cost, from_inventory, need_print = calculate_print_cost(tiles, inventory, copies)

    # If cost is 0, no need to replan
    if direct_cost == 0:
        return None

    # If need_print is empty but cost > 0, means inventory insufficient but cannot split
    if not need_print:
        return None

    # Calculate original cost (without inventory)
    original_cost, _, _ = calculate_print_cost(tiles, {}, copies)

    # Determine grid size
    if grid is not None:
        max_w, max_h = grid
    else:
        # Infer from tiles
        if not tiles:
            return None
        max_w = max(w for w, h in tiles)
        max_h = max(h for w, h in tiles)

    # Find available inventory sizes
    available_sizes = {k: v for k, v in inventory.items() if v > 0}
    if not available_sizes:
        return None

    # Calculate original cell count
    original_cells = sum(w * h for w, h in tiles)

    # Record current best plan (original plan)
    best_plan = {
        'cost': direct_cost,
        'from_inventory': from_inventory,
        'need_print': need_print,
        'tiles': tiles,
    }

    # Try each inventory size to find better plan
    for inv_key, inv_count in available_sizes.items():
        all_schemes = find_all_schemes(max_w, max_h)

        for scheme in all_schemes:
            scheme_tiles = scheme['tiles']
            scheme_cells = sum(w * h for w, h in scheme_tiles)

            # Verify cell count matches
            if scheme_cells != original_cells:
                continue

            # Calculate cost using inventory
            cost, from_inv, need_p = calculate_print_cost(scheme_tiles, inventory, copies)

            # Check if inventory was used
            if not from_inv:
                continue

            # Check if inventory usage doesn't exceed available
            if sum(from_inv.values()) > inv_count * copies:
                continue

            # Check if cost improved
            if cost < best_plan['cost']:
                best_plan = {
                    'cost': cost,
                    'from_inventory': from_inv,
                    'need_print': need_p,
                    'tiles': scheme_tiles,
                }

    # If no improvement, return None
    if best_plan['cost'] >= original_cost:
        return None

    return best_plan
