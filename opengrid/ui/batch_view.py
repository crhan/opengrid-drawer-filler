# 批量计算结果的展示层：数据构造（build_batch_data）和文本/JSON 输出（print_batch_plan）

import json

from opengrid.core import get_max_stacks
from opengrid.core.constants import (
    FILAMENT_MAIN_PER_CELL,
    FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL,
)
from opengrid.core.stats import calculate_filament_and_time, format_time
from opengrid.core.split_result import PrinterConfig
from opengrid.core.batch_planner import build_printer_config


__all__ = ['build_batch_data', 'print_batch_plan']


def _format_tiles_from_scheme(scheme):
    """将 scheme['tiles'] (元组列表) 转换为带计数的字典列表（按面积降序）"""
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

    Returns:
        包含 coverage/from_inventory/need_print 的字典；无瓦片时返回 None
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

    Returns:
        包含 drawers/tiles/stats/inventory_usage 的统一字典
    """
    if printer_config is None:
        printer_config = build_printer_config()

    if drawer_names is None:
        drawer_names = {}

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
    """打印批量打印计划（人类可读或 JSON）

    Returns:
        包含 total_main/total_support/total_filament/total_time/total_prints 的统计字典
    """
    if printer_config is None:
        printer_config = build_printer_config()

    from opengrid.core.constants import TILE_THICKNESS
    from opengrid.config import load_config_or_default

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
