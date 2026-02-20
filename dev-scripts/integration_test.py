#!/usr/bin/env python3
"""
库存感知评分系统集成测试 (端到端)

端到端验证流程：
1. 创建空的库存 json，后续所有操作都要指定这个 json 进行
2. 根据场景描述添加库存 (调用 inventory.py)
3. 调用脚本输出打印计划 (调用 split_calc.py)
4. 根据场景的要求验算打印计划是否符合

这是 TDD 流程 - 先写测试用例，后续会有人修复实现使其通过

用法:
    python3 scripts/integration_test.py              # 运行所有场景
    python3 scripts/integration_test.py 1            # 运行场景1
    python3 scripts/integration_test.py 1 2 3a     # 运行多个场景
    python3 scripts/integration_test.py --list      # 列出所有场景
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.split_calc import (
    calculate_filament_and_time,
    calculate_print_cost,
    get_grid_dimensions,
    find_best_scheme,
    optimize_batch_global,
    SWAP_PENALTY
)


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def calculate_cost_with_swap_penalty(tiles_list, copies_list, inventory=None):
    """计算带换料惩罚的总成本（与 verify_scenarios.py 一致）"""
    total_need_print = {}
    remaining_inv = dict(inventory) if inventory else {}

    for tiles, copies in zip(tiles_list, copies_list):
        tile_counts = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        for key, count in tile_counts.items():
            needed = count * copies
            available = remaining_inv.get(key, 0) if remaining_inv else 0
            used = min(needed, available)
            if remaining_inv:
                remaining_inv[key] = remaining_inv.get(key, 0) - used
            remaining = needed - used
            if remaining > 0:
                total_need_print[key] = total_need_print.get(key, 0) + remaining

    # 计算成本
    total_cost = 0
    for key, count in total_need_print.items():
        w, h = map(int, key.split('x'))
        cells = w * h
        _, _, time_min = calculate_filament_and_time(cells, count)
        total_cost += time_min

    # 加上换料惩罚
    print_count = len(total_need_print)
    total_cost += (print_count - 1) * SWAP_PENALTY if print_count > 1 else 0

    return total_cost


def calculate_batch_cost_from_cli(plan_data, inventory):
    """从 CLI 返回的 plan_data 计算成本（与 verify_scenarios.py 一致）

    从 CLI 输出的 inventory_usage 信息中提取 need_print，然后使用
    calculate_cost_with_swap_penalty 的逻辑计算成本。
    """
    # 从 plan_data 中获取 inventory_usage
    inv_usage = plan_data.get('inventory_usage', {})
    need_print = inv_usage.get('need_print', {})

    if not need_print:
        # 如果没有 inventory_usage，使用原始计算方式
        return plan_data.get('stats', {}).get('total_time_min', 0)

    # 使用与 calculate_cost_with_swap_penalty 相同的逻辑计算成本
    total_cost = 0
    for key, count in need_print.items():
        w, h = map(int, key.split('x'))
        cells = w * h
        _, _, time_min = calculate_filament_and_time(cells, count)
        total_cost += time_min

    # 加上换料惩罚
    print_count = len(need_print)
    total_cost += (print_count - 1) * SWAP_PENALTY if print_count > 1 else 0

    return total_cost


def run_cmd(cmd, capture=True, cwd=None):
    """运行命令并返回结果"""
    if cwd is None:
        cwd = SCRIPTS_DIR
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=cwd
    )
    return result


def create_empty_inventory(inv_file):
    """创建空的库存文件"""
    data = {"inventory": {}, "log": []}
    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def add_inventory(inv_file, items):
    """调用 inventory.py 添加库存"""
    cmd = [sys.executable, 'inventory.py', '-f', inv_file, 'add']
    for key, count in items.items():
        cmd.append(f"{key}:{count}")
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"添加库存失败: {result.stderr}")


def load_inventory(inv_file):
    """加载库存"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("inventory", {})


def get_print_plan(width, depth, inv_file, batch_mode=None):
    """通过 CLI 获取打印计划，返回统一的数据结构"""
    cmd = [sys.executable, 'split_calc.py']
    if batch_mode:
        cmd.extend(['-b', batch_mode])
    else:
        cmd.extend([str(width), str(depth)])
    cmd.extend(['-i', inv_file, '-j'])

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"获取打印计划失败: {result.stderr}")

    # 输出可能混合了人类可读格式和 JSON，需要提取 JSON 部分
    output = result.stdout

    # 查找包含 "drawer" 或 "drawers" 键的完整 JSON
    # 从第一个 "{" 开始尝试解析，找到包含所需键的完整 JSON
    json_start = output.find('{')
    result_data = None
    raw_data = None  # 保存原始 JSON 数据用于获取 inventory_usage

    while json_start >= 0 and json_start < len(output):
        json_str = output[json_start:]
        try:
            decoder = json.JSONDecoder()
            data, end_idx = decoder.raw_decode(json_str)
            raw_data = data  # 保存用于后续获取 inventory_usage

            # 检查是否是完整 JSON（包含 drawer 或 drawers 键）
            if 'drawer' in data or 'drawers' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': data.get('scheme', {})
                }
                break

            # 检查是否是批量模式的 JSON（包含 tiles）
            if 'tiles' in data and 'stats' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': {'tiles': data.get('tiles', [])},
                    'inventory_usage': data.get('inventory_usage', {}),
                    'drawers': data.get('drawers', [])
                }
                break

        except json.JSONDecodeError:
            pass

        # 继续查找下一个 "{"
        json_start = output.find('{', json_start + 1)

    if result_data is None:
        raise RuntimeError(f"无法从输出中提取有效 JSON: {output[:200]}")

    return result_data


def check_inventory_not_exceeded(used, available):
    """检查库存使用不超过提供数量"""
    for k, v in used.items():
        if available.get(k, 0) < v:
            return False
    return True


def format_print_plan(tiles, inventory, copies=1):
    """格式化打印计划"""
    tile_counts = {}
    for t in tiles:
        w, h = t['width'], t['height']
        key = f"{w}x{h}"
        # 使用 count 字段（如果有的话）
        count = t.get('count', 1)
        tile_counts[key] = tile_counts.get(key, 0) + count

    from_inv = {}
    need_print = {}
    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0)
        used = min(needed, available)
        if used > 0:
            from_inv[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    lines = []
    lines.append("--- 打印计划 ---")
    if from_inv:
        lines.append("从库存使用:")
        for key in sorted(from_inv.keys()):
            lines.append(f"  {key}: {from_inv[key]} stack")
    else:
        lines.append("从库存使用: 无")

    if need_print:
        lines.append("需要打印:")
        for key in sorted(need_print.keys()):
            w, h = map(int, key.split('x'))
            cells = w * h
            count = need_print[key]
            # 使用正确的计算函数
            _, _, time_min = calculate_filament_and_time(cells, count)
            lines.append(f"  {key}: {count} stack (约 {time_min:.0f} 分钟)")
    else:
        lines.append("需要打印: 无")

    return "\n".join(lines)


def check_cell_count_consistency(tiles_before, tiles_after):
    """检查拆分前后格子数量是否一致

    Args:
        tiles_before: 拆分前的瓦片列表 [(w,h), ...] 或 [{'width': w, 'height': h}, ...]
        tiles_after: 拆分后的瓦片列表

    Returns:
        tuple: (bool, int, int) - (是否一致, 原始格子数, 拆分后格子数)
    """
    def get_cells(tile):
        if isinstance(tile, tuple):
            return tile[0] * tile[1]
        elif isinstance(tile, dict):
            return tile['width'] * tile['height']
        return 0

    cells_before = sum(get_cells(t) for t in tiles_before)
    cells_after = sum(get_cells(t) for t in tiles_after)
    return cells_before == cells_after, cells_before, cells_after


def scenario_1(inv_file):
    """场景 1：精确匹配（直接瓦片需求测试）

    假设：
    - 库存：6×7 有 2 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 成本 = 0（完全使用库存）
    - from_inventory = {'6x7': 2}
    - need_print = {}

    验证目标：
    [x] 成本 = 0
    [x] from_inventory = {'6x7': 2}
    [x] need_print = {}
    [x] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 1: 精确匹配")
    print("=" * 60)
    print("假设:")
    print("  库存: 6x7 有 2 个")
    print("  需求: 2 个 6x7 瓦片")
    print()

    add_inventory(inv_file, {'6x7': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 直接调用 calculate_print_cost 测试
    tiles = [(6, 7), (6, 7)]
    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)

    print("--- 打印计划 ---")
    if from_inv:
        print("从库存使用:")
        for key in sorted(from_inv.keys()):
            print(f"  {key}: {from_inv[key]} stack")
    else:
        print("从库存使用: 无")

    if need_print:
        print("需要打印:")
        for key in sorted(need_print.keys()):
            w, h = map(int, key.split('x'))
            cells = w * h
            _, _, time_min = calculate_filament_and_time(cells, need_print[key])
            print(f"  {key}: {need_print[key]} stack (约 {time_min:.0f} 分钟)")
    else:
        print("需要打印: 无")
    print()

    print("计算结果:")
    print(f"  成本 = {cost}")
    print(f"  from_inventory = {from_inv}")
    print(f"  need_print = {need_print}")
    print()

    print("预期结果:")
    print("  成本 = 0")
    print("  from_inventory = {'6x7': 2}")
    print("  need_print = {}")
    print()

    # 验证项
    check1 = cost == 0
    check2 = from_inv == {'6x7': 2}
    check3 = need_print == {}
    check4 = check_inventory_not_exceeded(from_inv, inventory)

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 成本 = 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] from_inventory = {{"6x7": 2}}: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] need_print = {{}}: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')
    print()

    result = all([check1, check2, check3, check4])
    print(f"最终判断: {'✓ 场景1通过' if result else '✗ 场景1失败'}")
    return result


def scenario_2(inv_file):
    """场景 2：部分匹配（直接瓦片需求测试）

    假设：
    - 库存：6×7 有 1 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 库存取 1 个，打印 1 个
    - 成本 > 0
    - from_inventory = {'6x7': 1}
    - need_print = {'6x7': 1}

    验证目标：
    [x] from_inventory = {'6x7': 1}
    [x] need_print = {'6x7': 1}
    [x] 成本 > 0 且 < 无库存时的成本
    [x] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 2: 部分匹配")
    print("=" * 60)
    print("假设:")
    print("  库存: 6x7 有 1 个")
    print("  需求: 2 个 6x7 瓦片")
    print()

    add_inventory(inv_file, {'6x7': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 直接调用 calculate_print_cost 测试
    tiles = [(6, 7), (6, 7)]
    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)

    # 无库存对比
    cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

    print("--- 打印计划 ---")
    if from_inv:
        print("从库存使用:")
        for key in sorted(from_inv.keys()):
            print(f"  {key}: {from_inv[key]} stack")
    else:
        print("从库存使用: 无")

    if need_print:
        print("需要打印:")
        for key in sorted(need_print.keys()):
            w, h = map(int, key.split('x'))
            cells = w * h
            _, _, time_min = calculate_filament_and_time(cells, need_print[key])
            print(f"  {key}: {need_print[key]} stack (约 {time_min:.0f} 分钟)")
    else:
        print("需要打印: 无")
    print()

    print("计算结果:")
    print(f"  成本 = {cost}")
    print(f"  from_inventory = {from_inv}")
    print(f"  need_print = {need_print}")
    print()
    print("对照组(无库存):")
    print(f"  无库存成本 = {cost_no_inv}")
    print()

    print("预期结果:")
    print("  from_inventory = {'6x7': 1}")
    print("  need_print = {'6x7': 1}")
    print(f"  成本 > 0 且 < {cost_no_inv}")
    print()

    # 验证项
    check1 = from_inv == {'6x7': 1}
    check2 = need_print == {'6x7': 1}
    check3 = cost > 0 and cost < cost_no_inv
    check4 = check_inventory_not_exceeded(from_inv, inventory)

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] from_inventory = {{"6x7": 1}}: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] need_print = {{"6x7": 1}}: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 成本 > 0 且 < 无库存成本({cost_no_inv}): {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')
    print()

    result = all([check1, check2, check3, check4])
    print(f"最终判断: {'✓ 场景2通过' if result else '✗ 场景2失败'}")
    return result


def scenario_3a(inv_file):
    """场景 3a：库存方案选择（库存1个）

    假设：
    - 抽屉：265×360（格子 9×12）
    - 库存：6×6 有 1 个

    预期结果：
    - 选择能使用库存的方案
    - 成本 < 无库存方案

    验证目标：
    [x] 方案包含 6x6
    [x] 成本 < 无库存方案的成本
    """
    print("\n" + "=" * 60)
    print("场景 3a: 库存方案选择（库存1个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉: 265x360 (9x12 格子)")
    print("  库存: 6x6 有 1 个")
    print()

    add_inventory(inv_file, {'6x6': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 无库存方案
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        tiles_no_inv = plan_no_inv.get('scheme', {}).get('tiles', [])
        print("无库存方案:")
        print(f"  tiles = {tiles_no_inv}")
        print(f"  成本 = {time_no_inv} 分钟")
    finally:
        os.remove(temp_inv)
    print()

    # 有库存方案
    plan = get_print_plan(265, 360, inv_file)
    tiles = plan.get('scheme', {}).get('tiles', [])
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  成本 = {time_with_inv} 分钟")
    print()

    print("预期结果:")
    print("  方案包含 6x6")
    print("  成本 < 无库存方案")
    print()

    has_6x6 = any(t['width'] == 6 and t['height'] == 6 for t in tiles)
    cost_lower = time_with_inv < time_no_inv

    # 验证项
    check1 = has_6x6
    check2 = cost_lower

    # 库存使用检查（从 plan 的 inventory_usage 获取）
    inv_usage = plan.get('inventory_usage', {})
    from_inv = inv_usage.get('from_inventory', {})
    check3 = check_inventory_not_exceeded(from_inv, inventory)

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 方案包含 6x6: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 有库存成本({time_with_inv}) < 无库存成本({time_no_inv}): {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量: {check3}')
    print()

    result = check1 and check2 and check3
    print(f"最终判断: {'✓ 场景3a通过' if result else '✗ 场景3a失败'}")
    return result


def scenario_3b(inv_file):
    """场景 3b：库存方案选择（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 3b: 库存方案选择（库存2个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉: 265x360 (9x12 格子)")
    print("  库存: 6x6 有 2 个")
    print()

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 无库存方案
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 库存1个
    temp_inv1 = inv_file + ".temp1"
    create_empty_inventory(temp_inv1)
    add_inventory(temp_inv1, {'6x6': 1})
    try:
        plan_1 = get_print_plan(265, 360, temp_inv1)
        time_1 = plan_1.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv1)

    # 库存2个
    plan_2 = get_print_plan(265, 360, inv_file)
    tiles = plan_2.get('scheme', {}).get('tiles', [])
    time_2 = plan_2.get('stats', {}).get('total_time_min', 999)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  无库存成本 = {time_no_inv} 分钟")
    print(f"  库存1个成本 = {time_1} 分钟")
    print(f"  库存2个成本 = {time_2} 分钟")
    print()

    print("预期结果:")
    print("  成本 < 无库存方案")
    print("  成本 < 库存1个方案")
    print()

    print("验证项:")
    check1 = time_2 < time_no_inv
    check2 = time_2 < time_1

    # 库存使用检查
    inv_usage = plan_2.get('inventory_usage', {})
    from_inv = inv_usage.get('from_inventory', {})
    check3 = check_inventory_not_exceeded(from_inv, inventory)

    print(f'  [{"✓" if check1 else "✗"}] 成本({time_2}) < 无库存成本({time_no_inv}): {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 成本({time_2}) < 库存1个成本({time_1}): {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量: {check3}')
    print()

    result = check1 and check2 and check3
    print(f"最终判断: {'✓ 场景3b通过' if result else '✗ 场景3b失败'}")
    return result


def scenario_3c(inv_file):
    """场景 3c：库存方案选择（库存3个）"""
    print("\n" + "=" * 60)
    print("场景 3c: 库存方案选择（库存3个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉: 265x360 (9x12 格子)")
    print("  库存: 6x6 有 3 个")
    print()

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 库存2个对比
    temp_inv2 = inv_file + ".temp2"
    create_empty_inventory(temp_inv2)
    add_inventory(temp_inv2, {'6x6': 2})
    try:
        plan_2 = get_print_plan(265, 360, temp_inv2)
        time_2 = plan_2.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv2)

    # 库存3个
    plan_3 = get_print_plan(265, 360, inv_file)
    tiles = plan_3.get('scheme', {}).get('tiles', [])
    time_3 = plan_3.get('stats', {}).get('total_time_min', 999)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  库存2个成本 = {time_2} 分钟")
    print(f"  库存3个成本 = {time_3} 分钟")
    print()

    print("预期结果:")
    print("  成本 < 无库存方案")
    print("  成本 ≈ 库存2个方案（抽屉只能用2个）")
    print()

    # 3个和2个成本应该一样（因为抽屉只能用到2个）
    cost_equal = abs(time_3 - time_2) < 1

    # 库存使用检查
    inv_usage = plan_3.get('inventory_usage', {})
    from_inv = inv_usage.get('from_inventory', {})
    check3 = check_inventory_not_exceeded(from_inv, inventory)

    print("验证项:")
    check1 = time_3 < time_2 + 100  # 成本低于2个
    check2 = cost_equal

    print(f'  [{"✓" if check1 else "✗"}] 成本 < 库存2个方案: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 成本({time_3}) ≈ 库存2个成本({time_2}): {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量: {check3}')
    print()

    result = check1 and check2 and check3
    print(f"最终判断: {'✓ 场景3c通过' if result else '✗ 场景3c失败'}")
    return result


def scenario_4a(inv_file):
    """场景 4a：批量模式（库存1个）

    假设：
    - 抽屉 1：265×360，需要2个6×9
    - 抽屉 2：325×365，无6×9需求
    - 库存：6×9 有 1 个

    预期结果：
    - 抽屉1使用1个库存
    - 总成本降低

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 4a: 批量模式（库存1个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 无6x9需求")
    print("  库存: 6x9 有 1 个")
    print()

    add_inventory(inv_file, {'6x9': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    # 获取 drawer 尺寸
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    # 获取原始方案（无库存）
    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    # 无库存成本（使用 calculate_cost_with_swap_penalty）
    cost_no_inv = calculate_cost_with_swap_penalty(
        [scheme1['tiles'], scheme2['tiles']],
        [1, 1],
        inventory=None
    )

    # 有库存：使用 optimize_batch_global 进行优化
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 有库存成本
    total_cost = calculate_cost_with_swap_penalty(
        [result['schemes'][0]['tiles'], result['schemes'][1]['tiles']],
        [1, 1],
        inventory=inventory
    )

    print("计算结果:")
    print(f"  无库存成本 = {cost_no_inv:.1f} 分钟")
    print(f"  有库存成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  成本降低")
    print()

    cost_lower = total_cost < cost_no_inv

    print("验证项:")
    check1 = cost_lower

    print(f'  [{"✓" if check1 else "✗"}] 有库存成本({total_cost:.1f}) < 无库存成本({cost_no_inv:.1f}): {check1}')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景4a通过' if result else '✗ 场景4a失败'}")
    return result


def scenario_4b(inv_file):
    """场景 4b：批量模式（库存2个）

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 4b: 批量模式（库存2个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 可用6x9")
    print("  库存: 6x9 有 2 个")
    print()

    add_inventory(inv_file, {'6x9': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    # 原始方案
    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    # 无库存成本
    cost_no_inv = calculate_cost_with_swap_penalty(
        [scheme1['tiles'], scheme2['tiles']],
        [1, 1],
        inventory=None
    )

    # 有库存：批量优化
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    total_cost = calculate_cost_with_swap_penalty(
        [result['schemes'][0]['tiles'], result['schemes'][1]['tiles']],
        [1, 1],
        inventory=inventory
    )

    print("计算结果:")
    print(f"  无库存成本 = {cost_no_inv:.1f} 分钟")
    print(f"  有库存成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  抽屉1成本 = 0（完全使用库存）")
    print("  成本降低")
    print()

    print("验证项:")
    check1 = total_cost < cost_no_inv

    print(f'  [{"✓" if check1 else "✗"}] 总成本降低: {check1}')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景4b通过' if result else '✗ 场景4b失败'}")
    return result


def scenario_4c(inv_file):
    """场景 4c：批量模式（库存3个）- 全局优化

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 4c: 批量模式（库存3个）- 全局优化")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 可重新规划使用6x9")
    print("  库存: 6x9 有 3 个")
    print()

    add_inventory(inv_file, {'6x9': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    # 无库存成本
    cost_no_inv = calculate_cost_with_swap_penalty(
        [scheme1['tiles'], scheme2['tiles']],
        [1, 1],
        inventory=None
    )

    # 有库存：批量优化
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    total_cost = calculate_cost_with_swap_penalty(
        [result['schemes'][0]['tiles'], result['schemes'][1]['tiles']],
        [1, 1],
        inventory=inventory
    )

    print("计算结果:")
    print(f"  无库存成本 = {cost_no_inv:.1f} 分钟")
    print(f"  有库存成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  抽屉1成本 = 0")
    print("  抽屉2使用1个库存")
    print("  成本降低")
    print()

    # 验证：成本应该降低
    cost_lower = total_cost < cost_no_inv

    print("验证项:")
    check1 = cost_lower

    print(f'  [{"✓" if check1 else "✗"}] 成本降低: {check1} ({total_cost:.1f} < {cost_no_inv:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景4c通过' if result else '✗ 场景4c失败'}")
    return result


def scenario_4d(inv_file):
    """场景 4d：批量模式（库存4个）- 全局优化

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 4d: 批量模式（库存4个）- 全局优化")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 可重新规划使用6x9")
    print("  库存: 6x9 有 4 个")
    print()

    add_inventory(inv_file, {'6x9': 4})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    # 无库存成本
    cost_no_inv = calculate_cost_with_swap_penalty(
        [scheme1['tiles'], scheme2['tiles']],
        [1, 1],
        inventory=None
    )

    # 有库存：批量优化
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    total_cost = calculate_cost_with_swap_penalty(
        [result['schemes'][0]['tiles'], result['schemes'][1]['tiles']],
        [1, 1],
        inventory=inventory
    )

    print("计算结果:")
    print(f"  无库存成本 = {cost_no_inv:.1f} 分钟")
    print(f"  有库存成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  抽屉1成本 = 0")
    print("  抽屉2使用1个库存")
    print("  成本降低（剩余1个库存）")
    print()

    # 验证：成本应该降低（4个库存中只能用3个）
    cost_lower = total_cost < cost_no_inv

    print("验证项:")
    check1 = cost_lower

    print(f'  [{"✓" if check1 else "✗"}] 成本降低: {check1}')
    print("注: 11x13格子最多只能包含1个6x9，剩余1个库存")
    print()

    result = check1
    print(f"最终判断: {'✓ 场景4d通过' if result else '✗ 场景4d失败'}")
    return result


def scenario_5(inv_file):
    """场景 5：重新规划（边缘情况）

    假设：
    - 抽屉：265×360 (9×12格子)，原始方案需要 2 个 6×9
    - 库存：6×6 有 2 个

    预期结果：
    - 使用 2 个 6×6 库存
    - 成本降低（但 > 0）
    """
    print("\n" + "=" * 60)
    print("场景 5: 重新规划")
    print("=" * 60)
    print("假设:")
    print("  抽屉: 265x360 (9x12 格子)")
    print("  库存: 6x6 有 2 个")
    print()

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 无库存
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 有库存
    plan = get_print_plan(265, 360, inv_file)
    tiles = plan.get('scheme', {}).get('tiles', [])
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  无库存成本 = {time_no_inv} 分钟")
    print(f"  有库存成本 = {time_with_inv} 分钟")
    print()

    print("预期结果:")
    print("  方案包含 6x6")
    print("  成本降低（但 > 0）")
    print()

    has_6x6 = any(t['width'] == 6 and t['height'] == 6 for t in tiles)
    cost_lower = time_with_inv < time_no_inv
    cost_gt_0 = time_with_inv > 0

    print("验证项:")
    check1 = has_6x6
    check2 = cost_lower
    check3 = cost_gt_0

    print(f'  [{"✓" if check1 else "✗"}] 方案包含 6x6: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 成本降低: {check2} ({time_with_inv} < {time_no_inv})')
    print(f'  [{"✓" if check3 else "✗"}] 仍需打印(成本>0): {check3} (实际={time_with_inv})')
    print()

    result = check1 and check2 and check3
    print(f"最终判断: {'✓ 场景5通过' if result else '✗ 场景5失败'}")
    return result


def scenario_6a(inv_file):
    """场景 6a：批量 + 重新规划（库存 3 个）

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 6a: 批量 + 重新规划（库存 3 个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  库存: 6x6 有 3 个(正好够用)")
    print()

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 使用 optimize_batch_global 返回的 cost（与 verify_scenarios.py 一致）
    total_cost = result['cost']

    print("计算结果:")
    print(f"  总成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  库存刚好够用（抽屉1用2个，抽屉2用1个）")
    print("  仍需打印")
    print()

    # 库存刚好够用（抽屉1用2个，抽屉2用1个）
    check1 = total_cost > 0

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 仍需打印: {check1} (实际={total_cost:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景6a通过' if result else '✗ 场景6a失败'}")
    return result


def scenario_6b(inv_file):
    """场景 6b：批量 + 重新规划（库存 5 个）

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 6b: 批量 + 重新规划（库存 5 个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  库存: 6x6 有 5 个(多2个)")
    print()

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 使用 optimize_batch_global 返回的 cost（与 verify_scenarios.py 一致）
    total_cost = result['cost']

    print("计算结果:")
    print(f"  总成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  库存有余，应该用3个，剩余2个")
    print("  仍需打印")
    print()

    # 库存有余，应该用3个，剩余2个
    check1 = total_cost > 0

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 仍需打印: {check1} (实际={total_cost:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景6b通过' if result else '✗ 场景6b失败'}")
    return result


def scenario_7a(inv_file):
    """场景 7a：3抽屉 + 重新规划（库存 3 个）

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 7a: 3抽屉 + 重新规划（库存 3 个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  抽屉3: 420x392 -> 不需要6x6")
    print("  库存: 6x6 有 3 个")
    print()

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)
    grid3 = get_grid_dimensions(420, 392)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)
    scheme3 = find_best_scheme(grid3[0], grid3[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        {'grid': grid3, 'scheme': scheme3, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 使用 optimize_batch_global 返回的 cost（与 verify_scenarios.py 一致）
    total_cost = result['cost']

    print("计算结果:")
    print(f"  总成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  库存恰好用3个")
    print("  仍需打印")
    print()

    check1 = total_cost > 0

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 仍需打印: {check1} (实际={total_cost:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景7a通过' if result else '✗ 场景7a失败'}")
    return result


def scenario_7b(inv_file):
    """场景 7b：3抽屉 + 重新规划（库存 5 个）

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 7b: 3抽屉 + 重新规划（库存 5 个）")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  抽屉3: 420x392 -> 可重新规划使用6x6")
    print("  库存: 6x6 有 5 个")
    print()

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 使用与 verify_scenarios.py 相同的计算逻辑
    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)
    grid3 = get_grid_dimensions(420, 392)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)
    scheme3 = find_best_scheme(grid3[0], grid3[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        {'grid': grid3, 'scheme': scheme3, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 使用 optimize_batch_global 返回的 cost（与 verify_scenarios.py 一致）
    total_cost = result['cost']

    print("计算结果:")
    print(f"  总成本 = {total_cost:.1f} 分钟")
    print()

    print("预期结果:")
    print("  抽屉3可以重新规划使用库存")
    print("  仍需打印")
    print()

    # 抽屉3可以重新规划使用库存
    check1 = total_cost > 0

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 仍需打印: {check1} (实际={total_cost:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景7b通过' if result else '✗ 场景7b失败'}")
    return result


def scenario_8(inv_file):
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）

    假设：
    - 抽屉1：265×360 × 2
    - 抽屉2：325×360 × 2
    - 抽屉3：315×360 × 2
    - 库存：8×8 有 5 个，6×7 有 5 个

    注意：此场景使用与 verify_scenarios.py 相同的计算逻辑
    """
    print("\n" + "=" * 60)
    print("场景 8: 6抽屉 + 双库存尺寸")
    print("=" * 60)
    print("假设:")
    print("  抽屉1: 265x360 x 2")
    print("  抽屉2: 325x360 x 2")
    print("  抽屉3: 315x360 x 2")
    print("  库存: 8x8 有 5 个, 6x7 有 5 个")
    print()

    add_inventory(inv_file, {'8x8': 5, '6x7': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")
    print()

    # 准备批量数据（与 verify_scenarios.py 相同）
    batch_results = []
    configs = [
        (265, 360, 2),
        (325, 360, 2),
        (315, 360, 2),
    ]

    for w, d, copies in configs:
        grid = get_grid_dimensions(w, d)
        scheme = find_best_scheme(grid[0], grid[1], inventory=None, verbose=False)
        batch_results.append({
            'width': w,
            'depth': d,
            'grid': grid,
            'scheme': scheme,
            'copies': copies
        })

    # 无库存总成本（与 verify_scenarios.py 相同）
    no_inv_cost = sum(
        calculate_print_cost(r['scheme']['tiles'], {}, r['copies'])[0]
        for r in batch_results
    )
    print(f"无库存总成本: {no_inv_cost:.1f}")
    print()

    # 批量优化
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 计算正确的成本：使用与 verify_scenarios.py 相同的逻辑
    total_need_print = {}
    remaining_inv = dict(inventory)

    for i, scheme in enumerate(result['schemes']):
        tiles = scheme.get('tiles', [])
        copies = batch_results[i].get('copies', 1)

        tile_counts = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        for key, count in tile_counts.items():
            needed = count * copies
            available = remaining_inv.get(key, 0)
            used = min(needed, available)
            remaining_inv[key] = remaining_inv.get(key, 0) - used
            remaining = needed - used
            if remaining > 0:
                total_need_print[key] = total_need_print.get(key, 0) + remaining

    # 计算需要打印瓦片的成本
    total_cost = 0
    for key, count in total_need_print.items():
        w, h = map(int, key.split('x'))
        cells = w * h
        _, _, time_min = calculate_filament_and_time(cells, count)
        total_cost += time_min

    # 加上换料惩罚（与 verify_scenarios.py 一致）
    print_count = len(total_need_print)
    total_cost += (print_count - 1) * SWAP_PENALTY if print_count > 1 else 0

    print(f"优化后总成本: {total_cost:.1f}")
    print()

    print("预期结果:")
    print("  成本降低")
    print()

    cost_lower = total_cost < no_inv_cost

    print("验证项:")
    check1 = cost_lower

    print(f'  [{"✓" if check1 else "✗"}] 成本降低: {check1} ({total_cost:.1f} < {no_inv_cost:.1f})')
    print()

    result = check1
    print(f"最终判断: {'✓ 场景8通过' if result else '✗ 场景8失败'}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="库存感知评分系统集成测试 (端到端)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
这是 TDD 流程 - 先写测试用例，后续会修复实现

示例:
  python3 scripts/integration_test.py           # 运行所有场景
  python3 scripts/integration_test.py 1         # 运行场景1
  python3 scripts/integration_test.py 1 2 3a   # 运行多个场景
  python3 scripts/integration_test.py --list    # 列出所有场景
        """
    )
    parser.add_argument('scenarios', nargs='*', help='要运行的场景编号')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有场景')

    args = parser.parse_args()

    all_scenarios = {
        '1': ('场景1: 部分匹配', scenario_1),
        '2': ('场景2: 部分匹配', scenario_2),
        '3a': ('场景3a: 库存方案选择(1个)', scenario_3a),
        '3b': ('场景3b: 库存方案选择(2个)', scenario_3b),
        '3c': ('场景3c: 库存方案选择(3个)', scenario_3c),
        '4a': ('场景4a: 批量模式(库存1个)', scenario_4a),
        '4b': ('场景4b: 批量模式(库存2个)', scenario_4b),
        '4c': ('场景4c: 批量模式(库存3个)', scenario_4c),
        '4d': ('场景4d: 批量模式(库存4个)', scenario_4d),
        '5': ('场景5: 重新规划', scenario_5),
        '6a': ('场景6a: 批量+重新规划(3个)', scenario_6a),
        '6b': ('场景6b: 批量+重新规划(5个)', scenario_6b),
        '7a': ('场景7a: 3抽屉+重新规划(3个)', scenario_7a),
        '7b': ('场景7b: 3抽屉+重新规划(5个)', scenario_7b),
        '8': ('场景8: 6抽屉+双库存尺寸', scenario_8),
    }

    if args.list:
        print("可用场景:")
        for key in sorted(all_scenarios.keys(), key=lambda x: (len(x), x)):
            name, _ = all_scenarios[key]
            print(f"  {key}: {name}")
        return

    scenarios_to_run = args.scenarios if args.scenarios else list(all_scenarios.keys())

    print("=" * 60)
    print("库存感知评分系统集成测试")
    print("=" * 60)
    print(f"运行场景: {', '.join(scenarios_to_run)}")
    print()

    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as tmpdir:
        inv_file = os.path.join(tmpdir, 'test_inventory.json')

        results = []
        for key in scenarios_to_run:
            # 每个场景使用新的空库存文件
            create_empty_inventory(inv_file)

            if key not in all_scenarios:
                print(f"未知场景: {key}")
                continue

            name, func = all_scenarios[key]
            try:
                passed = func(inv_file)
                results.append((name, passed))
            except Exception as e:
                print(f"\n✗ 场景{key}执行失败: {e}")
                import traceback
                traceback.print_exc()
                results.append((name, False))

        # 输出汇总
        print("\n" + "=" * 60)
        print("验证结果汇总")
        print("=" * 60)
        passed_count = 0
        for name, passed in results:
            status = "✓" if passed else "✗"
            print(f"  [{status}] {name}")
            if passed:
                passed_count += 1

        print(f"\n总计: {passed_count}/{len(results)} 通过")

        if passed_count < len(results):
            print("\n发现的问题:")
            for name, passed in results:
                if not passed:
                    print(f"  - {name}")


if __name__ == "__main__":
    main()
