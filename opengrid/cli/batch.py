# 批量计算模式的 CLI 编排：解析输入字符串、跑算法、调输出
# 算法实现在 opengrid.core.batch_planner，输出在 opengrid.ui.batch_view

from opengrid.core.batch_planner import (
    build_printer_config as _build_printer_config,
    build_grid_config as _build_grid_config,
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    calculate_batch_cost_with_inventory,
    optimize_batch_global,
)
from opengrid.ui.batch_view import build_batch_data, print_batch_plan, render_batch_text


__all__ = [
    'batch_mode',
    'plan_batch',
    # 以下符号为向后兼容（split.py / 旧测试可能直接 import）
    'calculate_single',
    'merge_and_optimize',
    'calculate_total_prints',
    'calculate_batch_cost_with_inventory',
    'optimize_batch_global',
    'build_batch_data',
    'print_batch_plan',
]


def _assign_drawer_names(items: list[tuple[int, int, int]]) -> dict[int, str]:
    """按输入顺序命名：抽屉A、抽屉B……（跟 SKILL.md 约定一致，Agent 直接用，不用再自己编号）"""
    names = {}
    for idx in range(len(items)):
        letters, n = "", idx
        while True:
            letters = chr(ord('A') + n % 26) + letters
            n = n // 26 - 1
            if n < 0:
                break
        names[idx] = f"抽屉{letters}"
    return names


def plan_batch(items, inventory=None, verbose=False):
    """多抽屉联合规划：逐只算方案 → （有库存时）全局挑方案组合 → 合并瓦片 → 统一数据结构

    Args:
        items: [(width, depth, copies), ...]
        inventory: 可选库存字典 {"6x7": 3, ...}

    Returns:
        build_batch_data 的结果（含 drawers / tiles / stats / slicer_commands / inventory_usage）

    Raises:
        ValueError: 有抽屉无法分割（太小或形状不可分）
    """
    grid_config = _build_grid_config()
    printer_config = _build_printer_config()
    drawer_names = _assign_drawer_names(items)

    batch_results = []
    bad = []
    for idx, (width, depth, copies) in enumerate(items):
        result = calculate_single(width, depth, copies, verbose, index=idx, grid_config=grid_config)
        if result:
            batch_results.append(result)
        else:
            bad.append(f"{width}×{depth}mm")
    if bad:
        # 静默丢掉某只抽屉比报错更糟：用户以为整批都算了
        raise ValueError(f"以下抽屉无法生成有效方案（太小或不可分）: {', '.join(bad)}")

    if inventory:
        optimized = optimize_batch_global(batch_results, inventory=inventory, grid_config=grid_config, printer_config=printer_config)
        if optimized and 'schemes' in optimized:
            for i, scheme in enumerate(optimized['schemes']):
                if i < len(batch_results) and scheme:
                    batch_results[i]['scheme'] = scheme

    merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)
    return build_batch_data(batch_results, merged, inventory, drawer_names, printer_config)


def batch_mode(input_str, verbose=False, inventory=None, json_output=False):
    """批量模式入口（向后兼容）：解析整串输入，打印 JSON 或人话文本

    Returns:
        plan_batch 的结果；解析失败或有抽屉无法分割时返回 None（错误已打到 stderr）
    """
    import json
    import sys
    from opengrid.cli.utils import parse_dimensions

    items = parse_dimensions([input_str])
    if not items:
        print(f"错误: 无法解析尺寸: {input_str!r}（例：265x365:2 325x365）", file=sys.stderr)
        return None
    try:
        data = plan_batch(items, inventory, verbose)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return None

    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_batch_text(data)
    return data
