"""Cost calculation functions"""
from .constants import FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL, PRINT_TIME_PER_CELL


def calculate_print_cost(tiles, inventory, copies):
    """Calculate print cost and inventory usage

    Returns: (cost, from_inventory, need_print)
    """
    if not inventory:
        # No inventory - all need printing
        tile_counts = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        need_print = {k: v * copies for k, v in tile_counts.items()}
        return sum(need_print.values()), {}, need_print

    # Calculate inventory match
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}
    total_cost = 0

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining
            total_cost += remaining

    return total_cost, from_inventory, need_print


def replan_with_inventory(tiles, inventory, copies):
    """Try to replan using available inventory tiles"""
    # Simplified - just return None to indicate no alternative
    return None
