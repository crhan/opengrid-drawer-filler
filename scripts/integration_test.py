#!/usr/bin/env python3
"""
库存感知评分系统集成测试

端到端验证流程：
1. 创建空的库存 json，后续所有操作都要指定这个 json 进行
2. 根据场景描述添加库存
3. 调用脚本输出打印计划
4. 根据场景的要求验算打印计划是否符合

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
import shutil

# 添加 scripts 目录到路径
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from split_calc import (
    calculate_print_cost,
    get_grid_dimensions,
    find_best_scheme,
    replan_with_inventory,
    optimize_batch_global,
)


def create_empty_inventory(inv_file):
    """创建空的库存文件"""
    data = {"inventory": {}, "log": []}
    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def add_inventory(inv_file, items):
    """调用 inventory.py 添加库存"""
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, 'inventory.py'), '-f', inv_file, 'add']
    for key, count in items.items():
        cmd.append(f"{key}:{count}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"添加库存失败: {result.stderr}")
        return False
    return True


def load_inventory(inv_file):
    """加载库存"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("inventory", {})


def check_cell_count_consistency(tiles_before, tiles_after):
    """检查拆分前后格子数量是否一致"""
    cells_before = sum(w * h for w, h in tiles_before)
    cells_after = sum(w * h for w, h in tiles_after)
    return cells_before == cells_after, cells_before, cells_after


def check_inventory_not_exceeded(from_inv, inventory):
    """检查库存使用不超过提供数量"""
    for k, v in from_inv.items():
        if inventory.get(k, 0) < v:
            return False
    return True


def scenario_1(inv_file):
    """场景 1：精确匹配"""
    print("\n" + "=" * 60)
    print("场景 1: 精确匹配")
    print("=" * 60)

    # 添加库存
    add_inventory(inv_file, {'6x7': 2})
    inventory = load_inventory(inv_file)

    tiles = [(6, 7), (6, 7)]
    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)

    print(f"成本 = {cost}")
    print(f"from_inventory = {from_inv}")
    print(f"need_print = {need_print}")

    check1 = cost == 0
    check2 = from_inv == {'6x7': 2}
    check3 = need_print == {}
    check4 = check_inventory_not_exceeded(from_inv, inventory)

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 成本 = 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] from_inventory = {{"6x7": 2}}: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] need_print = {{}}: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')

    result = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景1通过' if result else '✗ 场景1失败'}")
    return result


def scenario_2(inv_file):
    """场景 2：部分匹配"""
    print("\n" + "=" * 60)
    print("场景 2: 部分匹配")
    print("=" * 60)

    add_inventory(inv_file, {'6x7': 1})
    inventory = load_inventory(inv_file)

    tiles = [(6, 7), (6, 7)]
    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
    cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

    print(f"成本 = {cost}")
    print(f"from_inventory = {from_inv}")
    print(f"need_print = {need_print}")
    print(f"无库存成本 = {cost_no_inv}")

    check1 = from_inv == {'6x7': 1}
    check2 = need_print == {'6x7': 1}
    check3 = cost > 0 and cost < cost_no_inv
    check4 = check_inventory_not_exceeded(from_inv, inventory)

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] from_inventory = {{"6x7": 1}}: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] need_print = {{"6x7": 1}}: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 成本 > 0 且 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')

    result = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景2通过' if result else '✗ 场景2失败'}")
    return result


def scenario_3a(inv_file):
    """场景 3a：库存方案选择（库存1个）"""
    print("\n" + "=" * 60)
    print("场景 3a: 库存方案选择（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 1})
    inventory = load_inventory(inv_file)

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)
    cost_with_inv = result_with_inv.get('cost', 0)

    print(f"无库存方案: {result_no_inv['tiles']}, 成本 = {cost_no_inv}")
    print(f"有库存方案: {result_with_inv['tiles']}, 成本 = {cost_with_inv}")

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    from_inv_result = result_with_inv.get('from_inventory', {})

    check1 = has_6x6
    check2 = cost_with_inv < cost_no_inv
    check3 = check_inventory_not_exceeded(from_inv_result, inventory)

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 方案包含 6x6: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 有库存成本 < 无库存成本: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量: {check3}')

    result = all([check1, check2, check3])
    print(f"\n最终判断: {'✓ 场景3a通过' if result else '✗ 场景3a失败'}")
    return result


def scenario_3b(inv_file):
    """场景 3b：库存方案选择（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 3b: 库存方案选择（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

    inventory_1 = {'6x6': 1}
    result_1 = find_best_scheme(9, 12, inventory=inventory_1, verbose=False)
    cost_1 = result_1.get('cost', 0)

    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)
    cost_with_inv = result_with_inv.get('cost', 0)

    print(f"无库存成本 = {cost_no_inv}")
    print(f"库存1个成本 = {cost_1}")
    print(f"库存2个成本 = {cost_with_inv}")

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    from_inv_result = result_with_inv.get('from_inventory', {})

    check1 = has_6x6
    check2 = cost_with_inv < cost_no_inv
    check3 = cost_with_inv < cost_1
    check4 = check_inventory_not_exceeded(from_inv_result, inventory)

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 方案包含 6x6: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 有库存成本 < 无库存成本: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 成本 < 库存1个时成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')

    result = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景3b通过' if result else '✗ 场景3b失败'}")
    return result


def scenario_3c(inv_file):
    """场景 3c：库存方案选择（库存3个）"""
    print("\n" + "=" * 60)
    print("场景 3c: 库存方案选择（库存3个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

    inventory_2 = {'6x6': 2}
    result_2 = find_best_scheme(9, 12, inventory=inventory_2, verbose=False)
    cost_2 = result_2.get('cost', 0)

    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)
    cost_with_inv = result_with_inv.get('cost', 0)

    print(f"无库存成本 = {cost_no_inv}")
    print(f"库存2个成本 = {cost_2}")
    print(f"库存3个成本 = {cost_with_inv}")

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    from_inv_result = result_with_inv.get('from_inventory', {})

    check1 = has_6x6
    check2 = cost_with_inv < cost_no_inv
    check3 = abs(cost_with_inv - cost_2) < 0.01
    check4 = check_inventory_not_exceeded(from_inv_result, inventory)

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 方案包含 6x6: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 有库存成本 < 无库存成本: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 成本 ≈ 库存2个时成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量: {check4}')

    result = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景3c通过' if result else '✗ 场景3c失败'}")
    return result


def scenario_4a(inv_file):
    """场景 4a：批量模式（库存1个）"""
    print("\n" + "=" * 60)
    print("场景 4a: 批量模式（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 1})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    total_used = sum(inv1_used.values()) + sum(inv2_used.values())

    print(f"无库存总成本 = {cost_no_inv}")
    print(f"优化后总成本 = {result['cost']}")
    print(f"抽屉1使用库存: {inv1_used}")
    print(f"抽屉2使用库存: {inv2_used}")

    check1 = result['cost'] < cost_no_inv
    check2 = total_used <= 1
    check3 = inv1_used.get('6x9', 0) == 1

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 总成本降低: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 库存使用不超过1个: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 抽屉1使用1个库存: {check3}')

    result_final = all([check1, check2, check3])
    print(f"\n最终判断: {'✓ 场景4a通过' if result_final else '✗ 场景4a失败'}")
    return result_final


def scenario_4b(inv_file):
    """场景 4b：批量模式（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 4b: 批量模式（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 2})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory={'6x9': 2}, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory={'6x9': 2}, verbose=False)

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    total_used = sum(inv1_used.values()) + sum(inv2_used.values())

    print(f"无库存总成本 = {cost_no_inv}")
    print(f"优化后总成本 = {result['cost']}")
    print(f"抽屉1成本 = {drawer1_cost}")
    print(f"库存使用: {total_used}")

    check1 = drawer1_cost == 0
    check2 = result['cost'] < cost_no_inv
    check3 = total_used <= 2

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 总成本降低: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过2个: {check3}')

    result_final = all([check1, check2, check3])
    print(f"\n最终判断: {'✓ 场景4b通过' if result_final else '✗ 场景4b失败'}")
    return result_final


def scenario_4c(inv_file):
    """场景 4c：批量模式（库存3个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4c: 批量模式（库存3个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 3})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    total_used = sum(inv1_used.values()) + sum(inv2_used.values())

    print(f"抽屉1成本 = {drawer1_cost}")
    print(f"抽屉2成本 = {drawer2_cost}")
    print(f"抽屉1使用库存: {inv1_used}")
    print(f"抽屉2使用库存: {inv2_used}")
    print(f"库存使用: {total_used}")

    check1 = drawer1_cost == 0
    check2 = drawer2_cost > 0
    check3 = total_used <= 3
    check4 = inv2_used.get('6x9', 0) == 1

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过3个: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 抽屉2使用1个库存: {check4}')

    result_final = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景4c通过' if result_final else '✗ 场景4c失败'}")
    return result_final


def scenario_4d(inv_file):
    """场景 4d：批量模式（库存4个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4d: 批量模式（库存4个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 4})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)  # 11x13格子

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    total_used = sum(inv1_used.values()) + sum(inv2_used.values())

    print(f"抽屉1成本 = {drawer1_cost}")
    print(f"抽屉2成本 = {drawer2_cost}")
    print(f"抽屉1使用库存: {inv1_used}")
    print(f"抽屉2使用库存: {inv2_used}")
    print(f"库存使用: {total_used}, 剩余: {4-total_used}")

    check1 = drawer1_cost == 0
    check2 = drawer2_cost > 0
    check3 = total_used <= 4
    check4 = inv2_used.get('6x9', 0) >= 1  # 11x13格子最多只能包含1个6x9

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过4个: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 抽屉2至少使用1个库存: {check4}')
    print("注: 11x13格子最多只能包含1个6x9")

    result_final = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景4d通过' if result_final else '✗ 场景4d失败'}")
    return result_final


def scenario_5(inv_file):
    """场景 5：重新规划"""
    print("\n" + "=" * 60)
    print("场景 5: 重新规划")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)

    grid = get_grid_dimensions(265, 360)
    scheme = find_best_scheme(grid[0], grid[1], inventory=None, verbose=False)
    tiles = scheme.get('tiles', [])

    cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

    result = replan_with_inventory(tiles, inventory, copies=1, grid=grid)

    has_6x6 = any(w == 6 and h == 6 for w, h in result.get('tiles', [])) if result else False
    need_print = result.get('need_print', {}) if result else {}

    print(f"原方案: {tiles}")
    print(f"原方案成本: {cost_no_inv}")
    print(f"重新规划后: {result['tiles'] if result else 'None'}")
    print(f"成本: {result['cost'] if result else 'N/A'}")

    cells_consistent, cells_before, cells_after = check_cell_count_consistency(tiles, result.get('tiles', [])) if result else (False, 0, 0)

    check1 = result is not None
    check2 = has_6x6
    check3 = len(need_print) > 0
    check4 = result['cost'] < cost_no_inv if result else False
    check5 = check_inventory_not_exceeded(result.get('from_inventory', {}), inventory) if result else False
    check6 = cells_consistent

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] replan_with_inventory 返回非空结果: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 方案包含 6x6 瓦片: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] need_print 不为空: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 成本 < 原方案成本: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 库存使用不超过提供数量: {check5}')
    print(f'  [{"✓" if check6 else "✗"}] 格子数量一致({cells_before}={cells_after}): {check6}')

    result_final = all([check1, check2, check3, check4, check5, check6])
    print(f"\n最终判断: {'✓ 场景5通过' if result_final else '✗ 场景5失败'}")
    return result_final


def scenario_6a(inv_file):
    """场景 6a：批量 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 6a: 批量 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    total_used = sum(inv1_used.values()) + sum(inv2_used.values())

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )

    # 格子数量一致性
    drawer1_cells_consistent, _, _ = check_cell_count_consistency(
        scheme1['tiles'], result['schemes'][0]['tiles']
    )
    drawer2_cells_consistent, _, _ = check_cell_count_consistency(
        scheme2['tiles'], result['schemes'][1]['tiles']
    )

    print(f"抽屉1成本: {drawer1_cost}")
    print(f"抽屉2成本: {drawer2_cost}")
    print(f"总成本: {result['cost']}")
    print(f"无库存成本: {cost_no_inv}")
    print(f"库存使用: {total_used}")

    check1 = drawer1_cost > 0
    check2 = drawer2_cost > 0
    check3 = result['cost'] < cost_no_inv
    check4 = total_used <= 3
    check5 = drawer1_cells_consistent and drawer2_cells_consistent

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过3个: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 格子数量一致: {check5}')

    result_final = all([check1, check2, check3, check4, check5])
    print(f"\n最终判断: {'✓ 场景6a通过' if result_final else '✗ 场景6a失败'}")
    return result_final


def scenario_6b(inv_file):
    """场景 6b：批量 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 6b: 批量 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    inv1_used = calculate_print_cost(result['schemes'][0]['tiles'], remaining_inv, copies=1)[1]
    for k, v in inv1_used.items():
        remaining_inv[k] -= v
    inv2_used = calculate_print_cost(result['schemes'][1]['tiles'], remaining_inv, copies=1)[1]

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    total_used = sum(inv1_used.values()) + sum(inv2_used.values())
    remaining = 5 - total_used

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )

    print(f"抽屉1成本: {drawer1_cost}")
    print(f"抽屉2成本: {drawer2_cost}")
    print(f"总成本: {result['cost']}")
    print(f"库存使用: {total_used}, 剩余: {remaining}")

    check1 = drawer1_cost > 0
    check2 = drawer2_cost > 0
    check3 = result['cost'] < cost_no_inv
    check4 = total_used <= 5
    check5 = total_used == 3 and remaining == 2

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过5个: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 库存使用3个，剩余2个: {check5}')

    result_final = all([check1, check2, check3, check4, check5])
    print(f"\n最终判断: {'✓ 场景6b通过' if result_final else '✗ 场景6b失败'}")
    return result_final


def scenario_7a(inv_file):
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 7a: 3抽屉 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

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

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2, scheme3]
    )

    # 格子数量一致性
    drawer1_cells_consistent, _, _ = check_cell_count_consistency(
        scheme1['tiles'], result['schemes'][0]['tiles']
    )
    drawer2_cells_consistent, _, _ = check_cell_count_consistency(
        scheme2['tiles'], result['schemes'][1]['tiles']
    )
    drawer3_cells_consistent, _, _ = check_cell_count_consistency(
        scheme3['tiles'], result['schemes'][2]['tiles']
    )

    total_used = sum(
        sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
        for s in result['schemes']
    )

    print(f"抽屉1成本: {drawer1_cost}")
    print(f"总成本: {result['cost']}")
    print(f"库存使用: {total_used}")

    check1 = drawer1_cost > 0
    check2 = result['cost'] < cost_no_inv
    check3 = total_used == 3
    check4 = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 总成本 < 无库存成本: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用恰好3个: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 格子数量一致: {check4}')

    result_final = all([check1, check2, check3, check4])
    print(f"\n最终判断: {'✓ 场景7a通过' if result_final else '✗ 场景7a失败'}")
    return result_final


def scenario_7b(inv_file):
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 7b: 3抽屉 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)

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

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2, scheme3]
    )

    # 格子数量一致性
    drawer1_cells_consistent, _, _ = check_cell_count_consistency(
        scheme1['tiles'], result['schemes'][0]['tiles']
    )
    drawer2_cells_consistent, _, _ = check_cell_count_consistency(
        scheme2['tiles'], result['schemes'][1]['tiles']
    )
    drawer3_cells_consistent, _, _ = check_cell_count_consistency(
        scheme3['tiles'], result['schemes'][2]['tiles']
    )

    total_used = sum(
        sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
        for s in result['schemes']
    )

    print(f"抽屉1成本: {drawer1_cost}")
    print(f"抽屉2成本: {drawer2_cost}")
    print(f"总成本: {result['cost']}")
    print(f"库存使用: {total_used}")

    check1 = drawer1_cost > 0
    check2 = drawer2_cost > 0
    check3 = result['cost'] < cost_no_inv
    check4 = total_used <= 5
    check5 = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过5个: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 格子数量一致: {check5}')

    result_final = all([check1, check2, check3, check4, check5])
    print(f"\n最终判断: {'✓ 场景7b通过' if result_final else '✗ 场景7b失败'}")
    return result_final


def scenario_8(inv_file):
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）"""
    print("\n" + "=" * 60)
    print("场景 8: 6抽屉 + 双库存尺寸")
    print("=" * 60)

    add_inventory(inv_file, {'8x8': 5, '6x7': 5})
    inventory = load_inventory(inv_file)

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

    no_inv_cost = sum(
        calculate_print_cost(r['scheme']['tiles'], {}, r['copies'])[0]
        for r in batch_results
    )

    result = optimize_batch_global(batch_results, inventory=inventory)

    # 按顺序计算库存使用
    remaining_inv = dict(inventory)
    drawer_costs = []
    drawer_inv = []
    for i, r in enumerate(batch_results):
        scheme = result['schemes'][i]
        cost, from_inv, need_print = calculate_print_cost(scheme['tiles'], remaining_inv, r['copies'])
        drawer_costs.append(cost)
        drawer_inv.append(from_inv)
        for k, v in from_inv.items():
            remaining_inv[k] = remaining_inv.get(k, 0) - v

    total_inv = {}
    for inv in drawer_inv:
        for k, v in inv.items():
            total_inv[k] = total_inv.get(k, 0) + v

    # 格子数量一致性
    all_cells_consistent = True
    for i, r in enumerate(batch_results):
        original_tiles = r['scheme']['tiles']
        optimized_tiles = result['schemes'][i]['tiles']
        consistent, _, _ = check_cell_count_consistency(original_tiles, optimized_tiles)
        all_cells_consistent = all_cells_consistent and consistent

    print(f"无库存总成本: {no_inv_cost}")
    print(f"优化后总成本: {result['cost']}")
    print(f"库存使用汇总: {total_inv}")

    check1 = result['cost'] < no_inv_cost
    check2 = total_inv.get('8x8', 0) <= inventory['8x8']
    check3 = total_inv.get('6x7', 0) <= inventory['6x7']
    check4 = all(c > 0 for c in drawer_costs)
    check5 = all_cells_consistent

    print("\n验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 总成本降低: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 8x8库存不超限: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 6x7库存不超限: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 所有抽屉都有打印: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 格子数量一致: {check5}')

    result_final = check1 and check2 and check3 and check4 and check5
    print(f"\n最终判断: {'✓ 场景8通过' if result_final else '✗ 场景8失败'}")
    return result_final


def main():
    parser = argparse.ArgumentParser(
        description="库存感知评分系统集成测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
        '1': ('场景1: 精确匹配', scenario_1),
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
                results.append((key, passed))
            except Exception as e:
                print(f"\n✗ 场景{key}执行失败: {e}")
                import traceback
                traceback.print_exc()
                results.append((key, False))

        # 输出汇总
        print("\n" + "=" * 60)
        print("验证结果汇总")
        print("=" * 60)
        passed_count = 0
        for key, passed in results:
            name, _ = all_scenarios[key]
            status = "✓" if passed else "✗"
            print(f"  [{status}] {name}")
            if passed:
                passed_count += 1

        print(f"\n总计: {passed_count}/{len(results)} 通过")


if __name__ == "__main__":
    main()
