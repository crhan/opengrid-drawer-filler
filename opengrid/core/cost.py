"""Cost calculation functions"""
from typing import Optional

from .constants import (
    FILAMENT_MAIN_PER_CELL,
    FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL,
    SWAP_PENALTY,
    MAX_Z,
    FULL_THICKNESS,
)
from .cost_v2 import (
    Tile as TileV2,
    calculate_stacks,
    calculate_plates,
    calculate_cost as calculate_cost_v2,
)


def _match_inventory(
    tiles: list[tuple[int, int]],
    inventory: dict,
    copies: int
) -> tuple[dict, dict]:
    """
    计算库存匹配结果。

    Args:
        tiles: 瓦片列表 [(w, h), ...]
        inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
        copies: 打印份数

    Returns:
        (from_inventory, need_print)
        - from_inventory: 从库存取的瓦片 {"6x8": 1, ...}
        - need_print: 仍需打印的瓦片 {"6x8": 2, ...}
    """
    # 规格化：小边在前（6x8 而非 8x6）
    tile_counts: dict[str, int] = {}
    for w, h in tiles:
        key = f"{min(w, h)}x{max(w, h)}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory: dict[str, int] = {}
    need_print: dict[str, int] = {}

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0) if inventory else 0
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    return from_inventory, need_print


def calculate_print_cost(tiles, inventory, copies, printer_config: Optional[dict] = None):
    """Calculate print cost (in time minutes) and inventory usage

    Args:
        tiles: 瓦片列表 [(w, h), ...]
        inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
        copies: 打印份数
        printer_config: 可选的打印机配置 dict，包含 max_z, bed_x, bed_y, tile_thickness

    Returns: (cost, from_inventory, need_print)
        - cost: 总打印时间（分钟），0 表示完全使用库存
        - from_inventory: 从库存取的瓦片 {"6x7": 2, ...}
        - need_print: 仍需打印的瓦片 {"6x7": 1, ...}
    """
    from_inventory, need_print = _match_inventory(tiles, inventory, copies)

    if not need_print:
        return 0, from_inventory, need_print

    # 使用传入的打印机配置或默认值
    max_z = printer_config.get("max_z", MAX_Z) if printer_config else MAX_Z
    tile_thickness = printer_config.get("tile_thickness", FULL_THICKNESS) if printer_config else FULL_THICKNESS
    bed_x = printer_config.get("bed_x", 256) if printer_config else 256
    bed_y = printer_config.get("bed_y", 256) if printer_config else 256

    # 构造 v2 Tile 列表（need_print 的每个条目 = 一种尺寸 + copies 数量）
    tiles_v2 = []
    for key, count in need_print.items():
        w, h = map(int, key.split('x'))
        tiles_v2.append(TileV2(w=w, h=h, copies=count))

    # v2 pipeline：Tile[] → Stack[] → Plate[] → CostResult
    stacks = calculate_stacks(tiles_v2, max_z, tile_thickness)
    plates = calculate_plates(stacks, bed_x, bed_y)
    result = calculate_cost_v2(plates)

    return result.total_cost, from_inventory, need_print


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
