# 批量计算核心算法：配置构造、单个抽屉计算、多方案合并、全局优化
# 不含 CLI 解析、文本/JSON 输出。

from opengrid.core import find_best_scheme, find_all_schemes, get_grid_dimensions, get_max_stacks, MIN_TILE
from opengrid.core.cost import calculate_print_cost
from opengrid.core.split_result import PrinterConfig
from opengrid.core.grid import GridConfig
from opengrid.config import load_config_or_default, get_printer_config_or_default


__all__ = [
    'build_printer_config',
    'build_grid_config',
    'calculate_single',
    'merge_and_optimize',
    'calculate_total_prints',
    'calculate_batch_cost_with_inventory',
    'optimize_batch_global',
]


def build_printer_config() -> PrinterConfig:
    """从当前配置构造 PrinterConfig"""
    config = load_config_or_default()
    printer = get_printer_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    tile_size = config.get("opengrid", {}).get("tile_size", 28)

    from opengrid.core.constants import TILE_THICKNESS
    thickness = TILE_THICKNESS.get(tile_type, 7.2)

    bed_x = printer.get("bed_x", 256)
    bed_y = printer.get("bed_y", 256)

    return PrinterConfig(
        max_z=printer.get("max_z", 256),
        bed_x=bed_x,
        bed_y=bed_y,
        tile_thickness=thickness,
        max_cells_x=bed_x // tile_size,
        max_cells_y=bed_y // tile_size,
    )


def build_grid_config() -> GridConfig:
    """从当前配置构造 GridConfig"""
    printer = build_printer_config()
    return GridConfig(
        max_cells_x=printer.max_cells_x,
        max_cells_y=printer.max_cells_y,
    )


def calculate_single(width, depth, copies=1, verbose=False, index=None, grid_config: GridConfig = None):
    """计算单个尺寸的分割方案

    Returns:
        包含 width/depth/copies/grid/scheme/index 的字典；无法分割时返回 None
    """
    if grid_config is None:
        grid_config = build_grid_config()

    x, y = get_grid_dimensions(width, depth)

    if x < MIN_TILE or y < MIN_TILE:
        return None

    scheme = find_best_scheme(x, y, grid_config, verbose)

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


def merge_and_optimize(batch_results, drawer_names=None, printer_config: PrinterConfig = None):
    """合并多个尺寸的方案，统计每个瓦片尺寸的总需求数量

    Returns:
        字典 {(w, h): {'total': int, 'by_drawer': [...]}}
    """
    if printer_config is None:
        printer_config = build_printer_config()

    if drawer_names is None:
        drawer_names = {}

    all_tiles = {}

    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']
        idx = result.get('index')

        tile_counts = {}
        for w, h in scheme['tiles']:
            key = (w, h)
            tile_counts[key] = tile_counts.get(key, 0) + 1

        for (w, h), count in tile_counts.items():
            if (w, h) not in all_tiles:
                all_tiles[(w, h)] = {'total': 0, 'by_drawer': []}

            total_for_drawer = count * copies
            all_tiles[(w, h)]['total'] += total_for_drawer

            drawer_name = drawer_names.get(idx, f"{width}×{depth}") if idx is not None else f"{width}×{depth}"

            all_tiles[(w, h)]['by_drawer'].append({
                'size': f"{width}×{depth}",
                'name': drawer_name,
                'copies': copies,
                'tiles_per_copy': count,
                'total': total_for_drawer,
                'index': idx
            })

    return all_tiles


def calculate_total_prints(batch_results, schemes, printer_config: PrinterConfig = None):
    """计算给定方案组合的总打印次数

    Returns:
        (total_prints, details): 总打印次数 + 每个尺寸 (w, h) 的详细信息字典
    """
    if printer_config is None:
        printer_config = build_printer_config()

    all_tiles = {}
    for result, scheme in zip(batch_results, schemes):
        if result is None or scheme is None:
            continue
        copies = result['copies']
        for w, h in scheme['tiles']:
            key = (w, h)
            if key not in all_tiles:
                all_tiles[key] = 0
            all_tiles[key] += copies

    max_stacks = get_max_stacks(printer_config)
    total_prints = 0
    details = {}

    for (w, h), stacks in all_tiles.items():
        prints_needed = (stacks + max_stacks - 1) // max_stacks
        total_prints += prints_needed
        details[(w, h)] = {
            'stacks': stacks,
            'print_count': prints_needed
        }

    return total_prints, details


def calculate_batch_cost_with_inventory(schemes, batch_results, inventory):
    """计算批量方案的总成本，按节省成本排序优先分配库存

    Returns:
        (total_cost, inventory_usage): 总成本 + 每个抽屉索引的库存使用情况
    """
    if not inventory:
        return sum(
            calculate_print_cost(s['tiles'], {}, batch_results[i].get('copies', 1))[0]
            for i, s in enumerate(schemes) if s
        ), {}

    savings = []
    for i, scheme in enumerate(schemes):
        if scheme is None:
            continue

        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        cost_no_inv, _, _ = calculate_print_cost(scheme['tiles'], {}, copies)
        cost_with_inv, from_inv, _ = calculate_print_cost(scheme['tiles'], inventory, copies)

        saved = cost_no_inv - cost_with_inv
        savings.append({
            'index': i,
            'scheme': scheme,
            'cost_no_inv': cost_no_inv,
            'cost_with_inv': cost_with_inv,
            'from_inv': from_inv,
            'saved': saved
        })

    savings.sort(key=lambda x: x['saved'], reverse=True)

    remaining_inv = dict(inventory)
    total_cost = 0
    inventory_usage = {}

    for item in savings:
        i = item['index']
        scheme = item['scheme']
        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        can_use = True
        for key, needed in item['from_inv'].items():
            if remaining_inv.get(key, 0) < needed:
                can_use = False
                break

        if can_use:
            cost = item['cost_with_inv']
            for key, used in item['from_inv'].items():
                remaining_inv[key] -= used
            inventory_usage[i] = item['from_inv']
        else:
            cost = item['cost_no_inv']
            inventory_usage[i] = {}

        total_cost += cost

    return total_cost, inventory_usage


def optimize_batch_global(batch_results, inventory=None, grid_config: GridConfig = None, printer_config: PrinterConfig = None):
    """贪心 + 局部搜索全局优化，为每个抽屉选择最优的分割方案组合

    Returns:
        包含 schemes/total_prints/cost/improved 的字典；无输入时返回 None
    """
    if grid_config is None:
        grid_config = build_grid_config()
    if printer_config is None:
        printer_config = build_printer_config()

    if not batch_results:
        return None

    initial_schemes = []
    for i, r in enumerate(batch_results):
        if r is None:
            initial_schemes.append(None)
            continue
        x, y = r['grid']
        copies = r.get('copies', 1)
        scheme = find_best_scheme(x, y, grid_config, inventory=None, copies=copies)
        initial_schemes.append(scheme)

    if inventory:
        initial_cost, _ = calculate_batch_cost_with_inventory(
            initial_schemes, batch_results, inventory
        )
    else:
        initial_total, _ = calculate_total_prints(batch_results, initial_schemes, printer_config)
        initial_cost = initial_total

    all_options = []
    for result in batch_results:
        if result is None:
            all_options.append([None])
            continue
        x, y = result['grid']
        schemes = find_all_schemes(x, y, grid_config)
        all_options.append(schemes)

    best_schemes = initial_schemes.copy()
    best_cost = initial_cost

    for i, options in enumerate(all_options):
        if len(options) <= 1:
            continue

        for option in options:
            test_schemes = best_schemes.copy()
            test_schemes[i] = option

            if None in test_schemes:
                continue

            if inventory:
                total, _ = calculate_batch_cost_with_inventory(
                    test_schemes, batch_results, inventory
                )
            else:
                total, _ = calculate_total_prints(batch_results, test_schemes, printer_config)

            if total < best_cost:
                best_schemes = test_schemes
                best_cost = total

    if inventory:
        final_cost, final_inv_usage = calculate_batch_cost_with_inventory(
            best_schemes, batch_results, inventory
        )
        for i, scheme in enumerate(best_schemes):
            if scheme is not None and i in final_inv_usage:
                scheme['from_inventory'] = final_inv_usage[i]
    else:
        final_cost = best_cost

    return {
        'schemes': best_schemes,
        'total_prints': best_cost if not inventory else None,
        'cost': final_cost if inventory else None,
        'initial_prints': initial_cost if not inventory else None,
        'initial_cost': initial_cost if inventory else None,
        'improved': best_cost < initial_cost
    }
