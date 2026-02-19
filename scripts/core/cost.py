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

    # 先尝试直接匹配
    direct_cost, from_inventory, need_print = calculate_print_cost(tiles, inventory, copies)

    # 如果直接匹配成本为 0，不需要重新规划
    if direct_cost == 0:
        return None

    # 如果 need_print 为空但 cost > 0，说明库存不足但无法拆分
    if not need_print:
        return None

    # 计算原始成本（无库存）
    original_cost, _, _ = calculate_print_cost(tiles, {}, copies)

    # 确定网格尺寸
    if grid is not None:
        max_w, max_h = grid
    else:
        # 从瓦片列表推断格子尺寸
        if not tiles:
            return None
        max_w = max(w for w, h in tiles)
        max_h = max(h for w, h in tiles)

    # 找到可用的库存尺寸
    available_sizes = {k: v for k, v in inventory.items() if v > 0}
    if not available_sizes:
        return None

    # 计算原始格子数量
    original_cells = sum(w * h for w, h in tiles)

    # 记录当前最佳方案（原始方案）
    best_plan = {
        'cost': direct_cost,
        'from_inventory': from_inventory,
        'need_print': need_print,
        'tiles': tiles,
    }

    # 遍历每种库存尺寸，尝试找到更好的方案
    for inv_key, inv_count in available_sizes.items():
        all_schemes = find_all_schemes(max_w, max_h)

        for scheme in all_schemes:
            scheme_tiles = scheme['tiles']
            scheme_cells = sum(w * h for w, h in scheme_tiles)

            # 验证格子数量一致
            if scheme_cells != original_cells:
                continue

            # 计算使用库存的成本
            cost, from_inv, need_p = calculate_print_cost(scheme_tiles, inventory, copies)

            # 检查是否使用了库存
            if not from_inv:
                continue

            # 检查库存使用是否不超过提供数量
            if sum(from_inv.values()) > inv_count * copies:
                continue

            # 检查成本是否有改善
            if cost < best_plan['cost']:
                best_plan = {
                    'cost': cost,
                    'from_inventory': from_inv,
                    'need_print': need_p,
                    'tiles': scheme_tiles,
                }

    # 如果没有改进，返回 None
    if best_plan['cost'] >= original_cost:
        return None

    return best_plan
