# 批量计算结果的展示层：数据构造（build_batch_data）和文本/JSON 输出（print_batch_plan）
#
# 成本走 cost_v2 管线（Tile → Stack → Plate → CostResult），跟单抽屉 SplitResult 同一套；
# 文本输出只渲染 build_batch_data 的结果，不再自己重算一遍，保证两种输出的数字一致。

import json

from opengrid.core.cost import tile_key, normalize_inventory
from opengrid.core.cost_v2 import Tile, calculate_stacks, calculate_plates, calculate_cost
from opengrid.core.stats import format_time
from opengrid.core.split_result import PrinterConfig
from opengrid.core.batch_planner import build_printer_config


__all__ = ['build_batch_data', 'print_batch_plan', 'render_batch_text']


def _format_tiles_from_scheme(scheme):
    """将 scheme['tiles'] (元组列表) 转换为带计数的字典列表（按面积降序）"""
    counts = {}
    for w, h in scheme.get('tiles', []):
        counts[(w, h)] = counts.get((w, h), 0) + 1
    return [
        {"width": w, "height": h, "count": c}
        for (w, h), c in sorted(counts.items(), key=lambda x: x[0][0] * x[0][1], reverse=True)
    ]


def _merge_by_key(merged_tiles):
    """把 merge_and_optimize 的 {(w, h): info} 按方向无关 key 再合并一次。

    不同抽屉可能分别产出 3×8 和 8×3，它们是同一块瓦片，库存和打印都该算在一起。
    保留第一次出现的方向作为展示/生成 STL 的方向。
    """
    result = {}
    for (w, h), info in merged_tiles.items():
        key = tile_key(w, h)
        if key not in result:
            result[key] = {'w': w, 'h': h, 'total': 0, 'by_drawer': []}
        result[key]['total'] += info['total']
        result[key]['by_drawer'].extend(info.get('by_drawer', []))
    return result


def _allocate_drawer_inventory(batch_results, from_inventory):
    """把合并层面实际取用的库存按抽屉顺序分摊回各抽屉。

    每只抽屉的 from_inventory / need_print 都乘上了份数，
    各抽屉求和 == 顶层 inventory_usage，不会出现两边对不上。

    Returns:
        {index_in_batch_results: {"from_inventory": {...}, "need_print": {...}, "coverage": {...}}}
    """
    pool = dict(from_inventory)
    allocations = {}
    for i, r in enumerate(batch_results):
        if not r:
            continue
        needed = {}
        for w, h in r['scheme']['tiles']:
            key = tile_key(w, h)
            needed[key] = needed.get(key, 0) + r['copies']

        from_inv, need_print = {}, {}
        covered_cells = total_cells = 0
        for key, n in needed.items():
            take = min(n, pool.get(key, 0))
            if take:
                pool[key] -= take
                from_inv[key] = take
            if n - take:
                need_print[key] = n - take
            w, h = map(int, key.split('x'))
            total_cells += n * w * h
            covered_cells += take * w * h

        allocations[i] = {
            "coverage": {
                "covered_cells": covered_cells,
                "total_cells": total_cells,
                "percent": int(covered_cells / total_cells * 100) if total_cells else 0,
            },
            "from_inventory": from_inv,
            "need_print": need_print,
        }
    return allocations


def build_batch_data(batch_results, merged_tiles, inventory=None, drawer_names=None, printer_config: PrinterConfig = None):
    """构建统一的批量方案数据结构，文本输出和 JSON 输出都从这里取数

    Returns:
        {
          drawers: [...],                 # 每只抽屉的分割方案 + 库存分摊（已乘份数）
          tiles: [{width, height, count, from_inventory, to_print, prints, stack_layers}],
          stats: {unique_sizes, total_tiles, total_time_min, total_filament_g, total_prints},
          slicer_commands: ["slicer generate WxHxS", ...],
          inventory_usage: {...}          # 仅传了库存时
        }
    """
    if printer_config is None:
        printer_config = build_printer_config()
    if drawer_names is None:
        drawer_names = {}

    inv = normalize_inventory(inventory)
    by_key = _merge_by_key(merged_tiles)
    ordered = sorted(by_key.items(), key=lambda kv: (kv[1]['w'] * kv[1]['h'], kv[1]['w']), reverse=True)

    from_inventory, need_print = {}, {}
    tiles_v2 = []
    for key, t in ordered:
        used = min(inv.get(key, 0), t['total'])
        to_print = t['total'] - used
        t['from_inventory'], t['to_print'] = used, to_print
        if used:
            from_inventory[key] = used
        if to_print:
            need_print[key] = to_print
            tiles_v2.append(Tile(w=t['w'], h=t['h'], copies=to_print))

    stacks = calculate_stacks(tiles_v2, printer_config.max_z, printer_config.tile_thickness)
    plates = calculate_plates(stacks, printer_config.bed_x, printer_config.bed_y)
    cost = calculate_cost(plates)

    tiles_output = []
    for key, t in ordered:
        layers = [s.count for s in stacks if tile_key(s.tile.w, s.tile.h) == key]
        tiles_output.append({
            "width": t['w'],
            "height": t['h'],
            "count": t['total'],
            "from_inventory": t['from_inventory'],
            "to_print": t['to_print'],
            "prints": len(layers),         # 当前每个 Stack 独占一盘
            "stack_layers": layers,
            "sources": [
                {"name": src.get('name', src['size']), "count": src['total']}
                for src in t['by_drawer']
            ],
        })

    allocations = _allocate_drawer_inventory(batch_results, from_inventory)
    drawers_output = []
    for i, r in enumerate(batch_results):
        if not r:
            continue
        idx = r.get('index')
        default_name = f"{r['width']}×{r['depth']}"
        scheme = r['scheme']
        drawers_output.append({
            "name": drawer_names.get(idx, default_name) if idx is not None else default_name,
            "width": r['width'],
            "depth": r['depth'],
            "copies": r['copies'],
            "grid": list(r['grid']) if r.get('grid') else None,
            "scheme": {
                "x_parts": scheme['x_parts'],
                "y_parts": scheme['y_parts'],
                "x_splits": scheme['x_splits'],
                "y_splits": scheme['y_splits'],
            },
            # 每份抽屉的瓦片（不乘份数），格子数 == 抽屉格子数
            "tiles": _format_tiles_from_scheme(scheme),
            "inventory": allocations[i],
        })

    output = {
        "drawers": drawers_output,
        "tiles": tiles_output,
        "stats": {
            "unique_sizes": len(by_key),
            "total_tiles": sum(t['total'] for t in by_key.values()),
            "total_time_min": round(cost.total_cost, 1),
            "total_filament_g": round(cost.total_filament_g, 1),
            "total_prints": cost.plate_count,
        },
        # 每个 Stack 一条，Agent 逐条 exec 即可（顺序无语义）
        "slicer_commands": [
            f"slicer generate {s.tile.w}x{s.tile.h}x{s.count}" for s in stacks
        ],
    }

    if inventory:
        output["inventory_usage"] = {
            "from_inventory": from_inventory,
            "need_print": need_print,
            "total_from_inventory": sum(from_inventory.values()),
            "total_need_print": sum(need_print.values()),
        }

    return output


def print_batch_plan(batch_results, merged_tiles, inventory=None, json_output=False, drawer_names=None, printer_config: PrinterConfig = None):
    """打印批量打印计划（人类可读或 JSON）

    Returns:
        build_batch_data 的结果
    """
    data = build_batch_data(batch_results, merged_tiles, inventory, drawer_names, printer_config)
    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_batch_text(data)
    return data


def render_batch_text(data):
    """把 build_batch_data 的结果渲染成人话文本"""
    print("=" * 70)
    print("openGrid 批量打印计划")
    print("=" * 70)

    print("\n--- 各抽屉分割方案 ---")
    for d in data['drawers']:
        s = d['scheme']
        print(f"\n{d['name']}（{d['width']}×{d['depth']}mm）× {d['copies']} 份:")
        if d.get('grid'):
            print(f"  格子: {d['grid'][0]} × {d['grid'][1]}")
        print(f"  X: {' + '.join(map(str, s['x_splits']))}")
        print(f"  Y: {' + '.join(map(str, s['y_splits']))}")
        tiles = ", ".join(f"{t['width']}×{t['height']}×{t['count']}" for t in d['tiles'])
        print(f"  每份瓦片: {tiles}")

    print("\n" + "=" * 70)
    print("--- 合并后的瓦片清单 ---")
    print("=" * 70)

    for t in data['tiles']:
        w, h = t['width'], t['height']
        print(f"\n{w}×{h} 格 ({w * 28}mm × {h * 28}mm)，共 {t['count']} 块:")
        for src in t['sources']:
            print(f"  来源: {src['name']} {src['count']} 块")
        if t['from_inventory']:
            print(f"  库存: {t['from_inventory']} 块")
        if t['to_print']:
            layers = " + ".join(f"{n} 层" for n in t['stack_layers'])
            print(f"  打印: {t['to_print']} 块 → {t['prints']} 盘（{layers}）")
        else:
            print("  打印: 无（完全使用库存）")

    stats = data['stats']
    print("\n" + "=" * 70)
    print("--- 总计 ---")
    print("=" * 70)
    print(f"瓦片: {stats['total_tiles']} 块，{stats['unique_sizes']} 种尺寸")
    print(f"总打印盘数: {stats['total_prints']}")
    print(f"总耗材: ~{stats['total_filament_g']:.0f}g")
    print(f"总打印时间: ~{format_time(stats['total_time_min'])}")
    if data['slicer_commands']:
        print("\n生成 STL:")
        for cmd in data['slicer_commands']:
            print(f"  uv run scripts/opengrid.py {cmd}")
