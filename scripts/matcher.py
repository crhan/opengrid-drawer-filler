"""Inventory matching algorithm"""


def get_inventory_match(tiles, copies, inv):
    """Calculate inventory match for a scheme

    Args:
        tiles: list of (w, h) tuples
        copies: print copies
        inv: inventory dict

    Returns:
        {
            "from_inventory": {"7x5": 3},
            "need_print": {"10x5": 3},
            "match_score": 3
        }
    """
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}
    match_score = 0

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inv.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining
        match_score += used

    return {
        "from_inventory": from_inventory,
        "need_print": need_print,
        "match_score": match_score
    }
