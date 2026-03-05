# 批量计算模式：合并多抽屉的分割方案、成本优化、打印计划输出
# 从 split.py 迁移，供 handle_split 调用，不含参数解析逻辑

import json
import re
from opengrid.core import find_best_scheme, find_all_schemes, get_grid_dimensions, get_max_stacks, MIN_TILE
from opengrid.core.constants import (
    FILAMENT_MAIN_PER_CELL,
    FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL,
)
from opengrid.core.cost import calculate_print_cost
from opengrid.core.stats import calculate_filament_and_time, format_time
from opengrid.core.split_result import PrinterConfig
from opengrid.core.grid import GridConfig
from opengrid.config import load_config_or_default, get_printer_config_or_default


__all__ = [
    'batch_mode',
    'calculate_single',
    'merge_and_optimize',
    'calculate_total_prints',
    'calculate_batch_cost_with_inventory',
    'optimize_batch_global',
    'build_batch_data',
    'print_batch_plan',
]


def _build_printer_config() -> PrinterConfig:
    """从当前配置构造 PrinterConfig

    Returns:
        PrinterConfig 实例，包含打印机床尺寸、Z 轴限制、瓦片厚度等参数
    """
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


def _build_grid_config() -> GridConfig:
    """从当前配置构造 GridConfig

    Returns:
        GridConfig 实例，包含最大格子数约束
    """
    printer = _build_printer_config()
    return GridConfig(
        max_cells_x=printer.max_cells_x,
        max_cells_y=printer.max_cells_y,
    )


def calculate_single(width, depth, copies=1, verbose=False, index=None, grid_config: GridConfig = None):
    """计算单个尺寸的分割方案

    Args:
        width: 抽屉宽度 (mm)
        depth: 抽屉深度 (mm)
        copies: 打印份数
        verbose: 是否详细输出
        index: 在批量任务中的索引，用于映射到抽屉名称
        grid_config: GridConfig 实例，如果为 None 则使用默认配置

    Returns:
        包含 width/depth/copies/grid/scheme/index 的字典，如果无法分割则返回 None
    """
    if grid_config is None:
        grid_config = _build_grid_config()

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

    策略:
    1. 收集所有需要的瓦片尺寸
    2. 统计每个尺寸的总需求数量（含份数）
    3. 返回合并后的字典供打印计划使用

    Args:
        batch_results: 批量计算结果列表，每个元素来自 calculate_single
        drawer_names: 可选的抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        字典 {(w, h): {'total': int, 'by_drawer': [...]}}
    """
    if printer_config is None:
        printer_config = _build_printer_config()

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

    Args:
        batch_results: 批量计算结果列表，每个元素包含 width, depth, copies, scheme
        schemes: 对应的分割方案列表
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        (total_prints, details): 总打印次数和每个尺寸 (w, h) 的详细信息字典
    """
    if printer_config is None:
        printer_config = _build_printer_config()

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
    """计算批量方案的总成本，正确追踪库存使用

    正确的逻辑：按节省成本排序，优先给节省多的抽屉分配库存

    Args:
        schemes: 分割方案列表
        batch_results: 批量计算结果列表
        inventory: 库存字典 {"6x7": 3, ...}

    Returns:
        (total_cost, inventory_usage): 总成本和每个抽屉索引的库存使用情况
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

    Args:
        batch_results: 批量计算结果列表
        inventory: 可选库存字典 {"6x7": 3, ...}
        grid_config: GridConfig 实例，如果为 None 则使用默认配置
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        包含 schemes/total_prints/cost/improved 的字典，如果无输入则返回 None
    """
    if grid_config is None:
        grid_config = _build_grid_config()
    if printer_config is None:
        printer_config = _build_printer_config()

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


def _format_tiles_from_scheme(scheme):
    """将 scheme['tiles'] (元组列表) 转换为带计数的字典列表

    Args:
        scheme: 分割方案字典，包含 tiles 键

    Returns:
        按面积降序排列的 [{"width": w, "height": h, "count": c}, ...] 列表
    """
    tiles = scheme.get('tiles', [])
    if not tiles:
        return []
    counts = {}
    for w, h in tiles:
        key = (w, h)
        counts[key] = counts.get(key, 0) + 1
    return [
        {"width": w, "height": h, "count": c}
        for (w, h), c in sorted(counts.items(), key=lambda x: x[0][0] * x[0][1], reverse=True)
    ]


def _build_single_inventory(scheme, inventory):
    """构建单个方案的库存覆盖信息

    Args:
        scheme: 分割方案字典
        inventory: 库存字典 {"6x7": 3, ...}

    Returns:
        包含 coverage/from_inventory/need_print 的字典，如果无瓦片则返回 None
    """
    from_inv = scheme.get('from_inventory', {})
    need_print = scheme.get('need_print', {})

    if scheme.get('tiles'):
        tiles = scheme.get('tiles', [])
        tile_counts = {}
        for w, h in tiles:
            key = f"{min(w, h)}x{max(w, h)}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        if from_inv:
            for key, inv_count in from_inv.items():
                total_needed = tile_counts.get(key, 0)
                need_print[key] = max(0, total_needed - inv_count)
        else:
            need_print = tile_counts

    need_print = {k: v for k, v in need_print.items() if v > 0}

    all_needed = {}
    if from_inv:
        for k, v in from_inv.items():
            all_needed[k] = all_needed.get(k, 0) + v
    if need_print:
        for k, v in need_print.items():
            all_needed[k] = all_needed.get(k, 0) + v

    if not all_needed:
        return None

    total_cells_needed = 0
    cells_covered = 0
    for key in all_needed.keys():
        w, h = map(int, key.split("x"))
        area = w * h
        need = all_needed[key]
        available = inventory.get(key, 0) if inventory else 0

        total_cells_needed += need * area
        cells_covered += min(need, available) * area

    coverage_percent = int(cells_covered / total_cells_needed * 100) if total_cells_needed > 0 else 0

    return {
        "coverage": {
            "covered_cells": cells_covered,
            "total_cells": total_cells_needed,
            "percent": coverage_percent
        },
        "from_inventory": from_inv,
        "need_print": need_print
    }


def build_batch_data(batch_results, merged_tiles, inventory=None, drawer_names=None, printer_config: PrinterConfig = None):
    """构建统一的批量方案数据结构，用于生成人类可读输出和 JSON 输出

    Args:
        batch_results: 批量计算结果列表
        merged_tiles: 合并后的瓦片字典，来自 merge_and_optimize
        inventory: 库存字典
        drawer_names: 抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        包含 drawers/tiles/stats/inventory_usage 的统一字典
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    from opengrid.core.constants import TILE_THICKNESS

    if drawer_names is None:
        drawer_names = {}

    tile_thickness = printer_config.tile_thickness
    max_stacks = get_max_stacks(printer_config)
    sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0
    tiles_output = []

    from_inventory = {}
    need_print_tiles = {}

    for (w, h), info in sorted_tiles:
        cells = w * h
        total_stacks = info['total']

        key = f"{min(w, h)}x{max(w, h)}"
        available = inventory.get(key, 0) if inventory else 0
        to_print = max(0, total_stacks - available)

        if available > 0:
            from_inventory[key] = min(available, total_stacks)
        if to_print > 0:
            need_print_tiles[key] = to_print

        if to_print > max_stacks:
            num_prints = (to_print + max_stacks - 1) // max_stacks
            stacks_per_print = to_print // num_prints
            remainder = to_print % num_prints

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells
                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        elif to_print > 0:
            main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)
            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1

        tiles_output.append({
            "width": w,
            "height": h,
            "stacks": total_stacks,
            "prints": total_prints if to_print > 0 else 0,
            "from_inventory": from_inventory.get(key, 0),
            "to_print": to_print
        })

    drawers_output = []
    from_inventory_agg = {}
    need_print_agg = {}

    for r in batch_results:
        if not r:
            continue
        width = r['width']
        depth = r['depth']
        copies = r['copies']
        scheme = r['scheme']
        idx = r.get('index')

        name = drawer_names.get(idx, f"{width}×{depth}") if idx is not None else f"{width}×{depth}"

        drawer_inv = _build_single_inventory(scheme, inventory) or {}
        drawer_from_inv = drawer_inv.get('from_inventory', {})
        drawer_need_print = drawer_inv.get('need_print', {})

        for k, v in drawer_from_inv.items():
            from_inventory_agg[k] = from_inventory_agg.get(k, 0) + v
        for k, v in drawer_need_print.items():
            need_print_agg[k] = need_print_agg.get(k, 0) + v

        drawers_output.append({
            "name": name,
            "width": width,
            "depth": depth,
            "copies": copies,
            "scheme": {
                "x_parts": scheme['x_parts'],
                "y_parts": scheme['y_parts'],
                "x_splits": scheme['x_splits'],
                "y_splits": scheme['y_splits'],
            },
            "tiles": _format_tiles_from_scheme(scheme),
            "inventory": drawer_inv
        })

    output = {
        "drawers": drawers_output,
        "tiles": tiles_output,
        "stats": {
            "total_filament_g": round(total_main + total_support),
            "total_time_min": int(total_time),
            "total_prints": total_prints
        }
    }

    if inventory and (from_inventory_agg or need_print_agg):
        output["inventory_usage"] = {
            "from_inventory": from_inventory_agg,
            "need_print": need_print_agg
        }

    return output


def print_batch_plan(batch_results, merged_tiles, inventory=None, json_output=False, drawer_names=None, printer_config: PrinterConfig = None):
    """打印批量打印计划（人类可读或 JSON 格式）

    Args:
        batch_results: 批量计算结果列表
        merged_tiles: 合并后的瓦片字典
        inventory: 库存字典
        json_output: 如果为 True 则输出 JSON 到 stdout，否则输出人类可读文本
        drawer_names: 抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        包含 total_main/total_support/total_filament/total_time/total_prints 的统计字典
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    from opengrid.core.constants import TILE_THICKNESS
    from opengrid.config import get_printer_config_or_default, load_config_or_default

    if drawer_names is None:
        drawer_names = {}

    config = load_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    interface_separation = config.get("opengrid", {}).get("interface_separation", 0.2)
    stacking_method = config.get("opengrid", {}).get("stacking_method", "Ironing")
    base_thickness = TILE_THICKNESS.get(tile_type, 6.8)
    if stacking_method == "Ironing":
        tile_thickness = base_thickness + 2 * interface_separation
    else:
        tile_thickness = base_thickness + 0.4 + 2 * interface_separation

    if json_output:
        output = build_batch_data(batch_results, merged_tiles, inventory, drawer_names, printer_config)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        total_filament = output['stats']['total_filament_g']
        return {
            'total_main': total_filament * 0.75,
            'total_support': total_filament * 0.25,
            'total_filament': total_filament,
            'total_time': output['stats']['total_time_min'],
            'total_prints': output['stats']['total_prints']
        }

    print("=" * 70)
    print("openGrid 批量打印计划 - 合并优化版")
    print("=" * 70)

    if drawer_names:
        print("\n--- 打印目标 ---")
        print(f"\n| 名字 | 尺寸 | 份数 |")
        print(f"|------|------|------|")
        for result in batch_results:
            if not result:
                continue
            idx = result.get('index')
            if idx is not None and idx in drawer_names:
                name = drawer_names[idx]
                width = result['width']
                depth = result['depth']
                copies = result['copies']
                print(f"| {name} | {width}×{depth}mm | {copies} |")

    print("\n--- 各尺寸分割方案 ---")
    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']
        x, y = result['grid']

        idx = result.get('index')
        if idx is not None and idx in drawer_names:
            name = drawer_names[idx]
            print(f"\n{name} × {copies} 份:")
        else:
            print(f"\n{width}×{depth}mm × {copies}份:")
        print(f"  格子: {x} × {y}")
        print(f"  分割: {scheme['x_parts']}×{scheme['y_parts']}")
        print(f"  X: {' + '.join(map(str, scheme['x_splits']))}")
        print(f"  Y: {' + '.join(map(str, scheme['y_splits']))}")

    print("\n" + "=" * 70)
    print("--- 合并后的瓦片清单（可一起打印）---")
    print("=" * 70)

    max_stacks = get_max_stacks(printer_config)
    sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0

    for (w, h), info in sorted_tiles:
        cells = w * h
        total_stacks = info['total']

        print(f"\n{w}×{h} 格 ({w*28}mm × {h*28}mm):")

        for src in info['by_drawer']:
            drawer_name = src.get('name', src['size'])
            print(f"  来源: {drawer_name} = {src['total']} stack")

        key = f"{w}x{h}"
        available = inventory.get(key, 0) if inventory else 0
        to_print = max(0, total_stacks - available)

        if inventory:
            if available > 0:
                print(f"  库存: {min(available, total_stacks)}")
            if to_print > 0:
                print(f"  需打印: {to_print}")
            else:
                print(f"  需打印: 无 (完全使用库存)")

        if to_print > max_stacks:
            num_prints = (to_print + max_stacks - 1) // max_stacks
            stacks_per_print = to_print // num_prints
            remainder = to_print % num_prints

            height = stacks_per_print * tile_thickness

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"  打印: {num_prints}次 ({stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells
                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                print(f"  打印: {num_prints}次 (每次{stacks_per_print} stack, {height:.0f}mm)")
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        elif to_print > 0:
            height = to_print * tile_thickness
            main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)

            print(f"  打印: 1次 ({to_print} stack, {height:.0f}mm)")
            print(f"    耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1

    print("\n" + "=" * 70)
    print("--- 总计 ---")
    print("=" * 70)
    print(f"总耗材: ~{total_main + total_support:.0f}g")
    print(f"  主耗材: ~{total_main:.0f}g")
    print(f"  支撑耗材: ~{total_support:.0f}g")
    print(f"总打印次数: {total_prints}次")
    print(f"总打印时间: ~{format_time(total_time)}")

    return {
        'total_main': total_main,
        'total_support': total_support,
        'total_filament': total_main + total_support,
        'total_time': total_time,
        'total_prints': total_prints
    }


def batch_mode(input_str, verbose=False, inventory=None, json_output=False):
    """批量计算模式入口，解析输入字符串并输出合并优化的打印计划

    Args:
        input_str: 输入字符串，支持 "265x365:2 325x365:2" 或 "265 365 2 325 365 2" 格式
        verbose: 是否详细输出
        inventory: 可选库存字典 {"6x7": 3, ...}
        json_output: 为 True 时输出 JSON 到 stdout，否则输出人类可读文本

    Returns:
        print_batch_plan 返回的统计字典，解析失败时返回 None
    """
    grid_config = _build_grid_config()
    printer_config = _build_printer_config()

    items = []

    pattern = r'(\d+)[x×](\d+)(?::(\d+))?'
    matches = re.findall(pattern, input_str)

    if matches:
        for m in matches:
            width = int(m[0])
            depth = int(m[1])
            copies = int(m[2]) if m[2] else 1
            items.append((width, depth, copies))

    if not items:
        parts = input_str.split()
        i = 0
        while i + 2 < len(parts):
            try:
                width = int(parts[i])
                depth = int(parts[i+1])
                copies = int(parts[i+2])
                items.append((width, depth, copies))
                i += 3
            except Exception:
                break

    if not items:
        print("无法解析输入格式")
        print("支持的格式:")
        print("  265x365:2 325x365:2 315x365:2")
        print("  265x365 325x365 315x365 (默认每项1份)")
        print("  265 365 2 325 365 2 315 365 2")
        return None

    drawer_names = {}
    size_counts = {}

    for idx, (width, depth, copies) in enumerate(items):
        size_key = f"{width}×{depth}"
        if size_key not in size_counts:
            size_counts[size_key] = 0
        size_counts[size_key] += 1

    size_indices = {}
    for idx, (width, depth, copies) in enumerate(items):
        size_key = f"{width}×{depth}"
        if size_key not in size_indices:
            size_indices[size_key] = 1
        else:
            size_indices[size_key] += 1

        if size_counts[size_key] == 1:
            drawer_names[idx] = size_key
        else:
            drawer_names[idx] = f"{size_key}#{size_indices[size_key]}"

    def _print(msg):
        """JSON 模式下静默所有非 JSON 输出"""
        if not json_output:
            print(msg)

    _print(f"解析到 {len(items)} 个抽屉:")
    for idx, (w, d, c) in enumerate(items):
        name = drawer_names[idx]
        _print(f"  {name}: {w}×{d}mm × {c}份")

    if inventory:
        _print(f"库存: {inventory}")
    _print("")

    batch_results = []
    for idx, (width, depth, copies) in enumerate(items):
        result = calculate_single(width, depth, copies, verbose, index=idx, grid_config=grid_config)
        if result:
            batch_results.append(result)
        else:
            _print(f"警告: {width}×{depth}mm 无法生成有效方案")

    if not batch_results:
        _print("错误: 没有有效的尺寸")
        return None

    if inventory:
        optimized = optimize_batch_global(batch_results, inventory=inventory, grid_config=grid_config, printer_config=printer_config)
        if optimized and 'schemes' in optimized:
            for i, scheme in enumerate(optimized['schemes']):
                if i < len(batch_results) and scheme:
                    batch_results[i]['scheme'] = scheme
        merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)
    else:
        merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)

    stats = print_batch_plan(
        batch_results, merged,
        inventory=inventory,
        json_output=json_output,
        drawer_names=drawer_names,
        printer_config=printer_config
    )
    return stats
