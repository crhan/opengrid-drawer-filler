# 批量计算模式的 CLI 编排：解析输入字符串、跑算法、调输出
# 算法实现在 opengrid.core.batch_planner，输出在 opengrid.ui.batch_view

import re

from opengrid.core.batch_planner import (
    build_printer_config as _build_printer_config,
    build_grid_config as _build_grid_config,
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    calculate_batch_cost_with_inventory,
    optimize_batch_global,
)
from opengrid.ui.batch_view import build_batch_data, print_batch_plan


__all__ = [
    'batch_mode',
    # 以下符号为向后兼容（split.py / 旧测试可能直接 import）
    'calculate_single',
    'merge_and_optimize',
    'calculate_total_prints',
    'calculate_batch_cost_with_inventory',
    'optimize_batch_global',
    'build_batch_data',
    'print_batch_plan',
]


def _parse_items(input_str: str) -> list[tuple[int, int, int]]:
    """解析批量输入字符串为 [(width, depth, copies), ...]

    支持两种格式：
    - "265x365:2 325x365"（冒号份数，缺省 1）
    - "265 365 2 325 365 1"（裸数字三元组）
    """
    pattern = r'(\d+)[x×](\d+)(?::(\d+))?'
    matches = re.findall(pattern, input_str)
    if matches:
        return [(int(w), int(d), int(c) if c else 1) for w, d, c in matches]

    items = []
    parts = input_str.split()
    i = 0
    while i + 2 < len(parts):
        try:
            items.append((int(parts[i]), int(parts[i + 1]), int(parts[i + 2])))
            i += 3
        except Exception:
            break
    return items


def _assign_drawer_names(items: list[tuple[int, int, int]]) -> dict[int, str]:
    """同尺寸出现多次时加 #N 后缀，便于 Agent / 用户区分。"""
    size_counts = {}
    for width, depth, _ in items:
        key = f"{width}×{depth}"
        size_counts[key] = size_counts.get(key, 0) + 1

    drawer_names = {}
    size_indices = {}
    for idx, (width, depth, _) in enumerate(items):
        key = f"{width}×{depth}"
        size_indices[key] = size_indices.get(key, 0) + 1
        drawer_names[idx] = key if size_counts[key] == 1 else f"{key}#{size_indices[key]}"
    return drawer_names


def batch_mode(input_str, verbose=False, inventory=None, json_output=False):
    """批量计算模式入口，解析输入字符串并输出合并优化的打印计划

    Args:
        input_str: 抽屉尺寸串，如 "265x365:2 325x365:2" 或 "265 365 2 325 365 2"
        verbose: 详细输出
        inventory: 可选库存字典 {"6x7": 3, ...}
        json_output: True 输出 JSON 到 stdout；False 输出人话文本

    Returns:
        print_batch_plan 返回的统计字典；解析失败时返回 None
    """
    grid_config = _build_grid_config()
    printer_config = _build_printer_config()

    items = _parse_items(input_str)
    if not items:
        print("无法解析输入格式")
        print("支持的格式:")
        print("  265x365:2 325x365:2 315x365:2")
        print("  265x365 325x365 315x365 (默认每项1份)")
        print("  265 365 2 325 365 2 315 365 2")
        return None

    drawer_names = _assign_drawer_names(items)

    def _say(msg):
        """JSON 模式下静默所有非 JSON 输出"""
        if not json_output:
            print(msg)

    _say(f"解析到 {len(items)} 个抽屉:")
    for idx, (w, d, c) in enumerate(items):
        _say(f"  {drawer_names[idx]}: {w}×{d}mm × {c}份")

    if inventory:
        _say(f"库存: {inventory}")
    _say("")

    batch_results = []
    for idx, (width, depth, copies) in enumerate(items):
        result = calculate_single(width, depth, copies, verbose, index=idx, grid_config=grid_config)
        if result:
            batch_results.append(result)
        else:
            _say(f"警告: {width}×{depth}mm 无法生成有效方案")

    if not batch_results:
        _say("错误: 没有有效的尺寸")
        return None

    if inventory:
        optimized = optimize_batch_global(batch_results, inventory=inventory, grid_config=grid_config, printer_config=printer_config)
        if optimized and 'schemes' in optimized:
            for i, scheme in enumerate(optimized['schemes']):
                if i < len(batch_results) and scheme:
                    batch_results[i]['scheme'] = scheme

    merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)

    return print_batch_plan(
        batch_results, merged,
        inventory=inventory,
        json_output=json_output,
        drawer_names=drawer_names,
        printer_config=printer_config
    )
