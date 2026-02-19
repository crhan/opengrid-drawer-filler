#!/usr/bin/env python3
"""
库存感知评分系统 v2 验证脚本

用法:
    python3 scripts/verify_scenarios.py              # 运行所有场景
    python3 scripts/verify_scenarios.py 5            # 运行场景5
    python3 scripts/verify_scenarios.py 4c          # 运行场景4c
    python3 scripts/verify_scenarios.py 1 2 3a       # 运行多个场景
    python3 scripts/verify_scenarios.py all          # 运行所有场景

执行 docs/verification-report.md 中的所有验证场景
"""

import os
import sys
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from split_calc import (
    calculate_print_cost,
    calculate_filament_and_time,
    get_grid_dimensions,
    find_best_scheme,
    replan_with_inventory,
    optimize_batch_global,
    find_all_schemes
)


def format_print_plan(tiles, inventory, copies=1):
    """格式化打印计划"""
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

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
            _, _, time_min = calculate_filament_and_time(cells, count)
            lines.append(f"  {key}: {count} stack (约 {time_min:.0f} 分钟)")
    else:
        lines.append("需要打印: 无")

    return "\n".join(lines)


def check_inventory_not_exceeded(from_inv, inventory):
    """检查使用的库存是否超过提供的数量

    Args:
        from_inv: 使用的库存字典 {'6x6': 2, ...}
        inventory: 提供的库存字典 {'6x6': 5, ...}

    Returns:
        bool: True 如果使用不超过提供
    """
    for key, used in from_inv.items():
        available = inventory.get(key, 0)
        if used > available:
            return False
    return True


def check_cell_count_consistency(tiles_before, tiles_after):
    """检查拆分前后格子数量是否一致

    Args:
        tiles_before: 拆分前的瓦片列表 [(w,h), ...]
        tiles_after: 拆分后的瓦片列表 [(w,h), ...]

    Returns:
        tuple: (bool, int, int) - (是否一致, 原始格子数, 拆分后格子数)
    """
    cells_before = sum(w * h for w, h in tiles_before)
    cells_after = sum(w * h for w, h in tiles_after)
    return cells_before == cells_after, cells_before, cells_after


def format_batch_print_plan(batch_results, inventory, optimized_schemes=None):
    """格式化批量打印计划

    Args:
        batch_results: 原始批量结果（用于显示方案信息）
        inventory: 库存字典
        optimized_schemes: 优化后的方案列表（用于计算库存使用），如果为None则使用batch_results
    """
    lines = []
    lines.append("--- 批量打印计划 ---")

    total_from_inv = {}
    total_need_print = {}

    # 使用优化后的方案（如果提供）来计算库存使用
    schemes_to_use = optimized_schemes if optimized_schemes else [r.get('scheme', {}) for r in batch_results]

    for i, scheme in enumerate(schemes_to_use):
        drawer_name = f"抽屉{i+1}"
        tiles = scheme.get('tiles', [])
        grid = batch_results[i].get('grid', (0, 0)) if i < len(batch_results) else (0, 0)

        lines.append(f"\n{drawer_name} ({grid[0]}x{grid[1]}格子):")

        tile_counts = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        from_inv = {}
        need_print = {}
        for key, count in tile_counts.items():
            available = inventory.get(key, 0)
            used = min(count, available)
            if used > 0:
                from_inv[key] = used
                total_from_inv[key] = total_from_inv.get(key, 0) + used
            remaining = count - used
            if remaining > 0:
                need_print[key] = remaining
                total_need_print[key] = total_need_print.get(key, 0) + remaining

        if from_inv:
            for key in sorted(from_inv.keys()):
                lines.append(f"  库存使用 {key}: {from_inv[key]}")
        if need_print:
            for key in sorted(need_print.keys()):
                w, h = map(int, key.split('x'))
                cells = w * h
                _, _, time_min = calculate_filament_and_time(cells, need_print[key])
                lines.append(f"  打印 {key}: {need_print[key]} stack (约 {time_min:.0f}分钟)")

    lines.append("\n--- 汇总 ---")
    if total_from_inv:
        lines.append("库存使用汇总:")
        for key in sorted(total_from_inv.keys()):
            lines.append(f"  {key}: {total_from_inv[key]}")
    if total_need_print:
        lines.append("打印汇总:")
        for key in sorted(total_need_print.keys()):
            w, h = map(int, key.split('x'))
            cells = w * h
            _, _, time_min = calculate_filament_and_time(cells, total_need_print[key])
            lines.append(f"  {key}: {total_need_print[key]} stack (约 {time_min:.0f}分钟)")

    return "\n".join(lines)


def scenario_1():
    """场景 1：精确匹配"""
    print("\n" + "="*60)
    print("场景 1: 精确匹配")
    print("="*60)
    print("假设: 库存 6x7 有 2 个, 需求 2 个 6x7 瓦片")
    print()

    tiles = [(6, 7), (6, 7)]
    inventory = {'6x7': 2}
    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  成本 (cost) = {cost}")
    print(f"  from_inventory = {from_inv}")
    print(f"  need_print = {need_print}")
    print()
    print("预期结果:")
    print("  成本 = 0")
    print('  from_inventory = {"6x7": 2}')
    print("  need_print = {}")
    print()

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


def scenario_2():
    """场景 2：部分匹配"""
    print("\n" + "="*60)
    print("场景 2: 部分匹配")
    print("="*60)
    print("假设: 库存 6x7 有 1 个, 需求 2 个 6x7 瓦片")
    print()

    tiles = [(6, 7), (6, 7)]
    inventory = {'6x7': 1}

    cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
    cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

    print(format_print_plan(tiles, inventory, copies=1))
    print()

    print("计算结果:")
    print(f"  成本 (cost) = {cost}")
    print(f"  from_inventory = {from_inv}")
    print(f"  need_print = {need_print}")
    print()
    print("对照组(无库存):")
    print(f"  无库存成本 = {cost_no_inv}")
    print()
    print("预期结果:")
    print("  库存取1个, 打印1个")
    print('  from_inventory = {"6x7": 1}')
    print('  need_print = {"6x7": 1}')
    print(f"  成本 > 0 且 < {cost_no_inv}")
    print()

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


def scenario_3a():
    """场景 3a：库存方案选择（库存1个）"""
    print("\n" + "="*60)
    print("场景 3a: 库存方案选择（库存1个）")
    print("="*60)
    print("假设: 抽屉 265x360 (9x12格子), 库存 6x6 有 1 个")
    print()

    grid = get_grid_dimensions(265, 360)
    print(f"抽屉格子尺寸: {grid}")
    print()

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    print("无库存时的方案:")
    print(f"  tiles = {result_no_inv.get('tiles')}")
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]
    print(f"  成本 = {cost_no_inv}")
    print()

    inventory = {'6x6': 1}
    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)

    print(format_print_plan(result_with_inv.get('tiles', []), inventory, copies=1))
    print()

    print("有库存时的方案:")
    print(f"  tiles = {result_with_inv.get('tiles')}")
    cost_with_inv = result_with_inv.get('cost', 0)
    print(f"  成本 = {cost_with_inv}")
    print(f"  from_inventory = {result_with_inv.get('from_inventory', {})}")
    print()

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    cost_lower = cost_with_inv < cost_no_inv
    from_inv_result = result_with_inv.get('from_inventory', {})
    check_inventory = check_inventory_not_exceeded(from_inv_result, inventory)

    print("验证项:")
    print(f'  [{"✓" if has_6x6 else "✗"}] 方案包含 6x6: {has_6x6}')
    print(f'  [{"✓" if cost_lower else "✗"}] 有库存成本({cost_with_inv}) < 无库存成本({cost_no_inv}): {cost_lower}')
    print(f'  [{"✓" if check_inventory else "✗"}] 库存使用不超过提供数量: {check_inventory}')
    print()

    result = all([has_6x6, cost_lower, check_inventory])
    print(f"最终判断: {'✓ 场景3a通过' if result else '✗ 场景3a失败'}")
    return result


def scenario_3b():
    """场景 3b：库存方案选择（库存2个）"""
    print("\n" + "="*60)
    print("场景 3b: 库存方案选择（库存2个）")
    print("="*60)
    print("假设: 抽屉 265x360 (9x12格子), 库存 6x6 有 2 个")
    print()

    grid = get_grid_dimensions(265, 360)
    print(f"抽屉格子尺寸: {grid}")
    print()

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    print("无库存时的方案:")
    print(f"  tiles = {result_no_inv.get('tiles')}")
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]
    print(f"  成本 = {cost_no_inv}")
    print()

    # 先计算库存1个时的成本
    inventory_1 = {'6x6': 1}
    result_1 = find_best_scheme(9, 12, inventory=inventory_1, verbose=False)
    cost_1 = result_1.get('cost', 0)
    print(f"库存1个时的成本 = {cost_1}")
    print()

    inventory = {'6x6': 2}
    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)

    print(format_print_plan(result_with_inv.get('tiles', []), inventory, copies=1))
    print()

    print("有库存时的方案:")
    print(f"  tiles = {result_with_inv.get('tiles')}")
    cost_with_inv = result_with_inv.get('cost', 0)
    print(f"  成本 = {cost_with_inv}")
    print(f"  from_inventory = {result_with_inv.get('from_inventory', {})}")
    print()

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    cost_lower = cost_with_inv < cost_no_inv
    cost_lower_than_1 = cost_with_inv < cost_1
    from_inv_result = result_with_inv.get('from_inventory', {})
    check_inventory = check_inventory_not_exceeded(from_inv_result, inventory)

    print("验证项:")
    print(f'  [{"✓" if has_6x6 else "✗"}] 方案包含 6x6: {has_6x6}')
    print(f'  [{"✓" if cost_lower else "✗"}] 有库存成本({cost_with_inv}) < 无库存成本({cost_no_inv}): {cost_lower}')
    print(f'  [{"✓" if cost_lower_than_1 else "✗"}] 成本({cost_with_inv}) < 库存1个时成本({cost_1}): {cost_lower_than_1}')
    print(f'  [{"✓" if check_inventory else "✗"}] 库存使用不超过提供数量: {check_inventory}')
    print()

    result = all([has_6x6, cost_lower, cost_lower_than_1, check_inventory])
    print(f"最终判断: {'✓ 场景3b通过' if result else '✗ 场景3b失败'}")
    return result


def scenario_3c():
    """场景 3c：库存方案选择（库存3个）"""
    print("\n" + "="*60)
    print("场景 3c: 库存方案选择（库存3个）")
    print("="*60)
    print("假设: 抽屉 265x360 (9x12格子), 库存 6x6 有 3 个")
    print()

    grid = get_grid_dimensions(265, 360)
    print(f"抽屉格子尺寸: {grid}")
    print()

    result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
    print("无库存时的方案:")
    print(f"  tiles = {result_no_inv.get('tiles')}")
    cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]
    print(f"  成本 = {cost_no_inv}")
    print()

    # 先计算库存2个时的成本
    inventory_2 = {'6x6': 2}
    result_2 = find_best_scheme(9, 12, inventory=inventory_2, verbose=False)
    cost_2 = result_2.get('cost', 0)
    print(f"库存2个时的成本 = {cost_2}")
    print()

    inventory = {'6x6': 3}
    result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)

    print(format_print_plan(result_with_inv.get('tiles', []), inventory, copies=1))
    print()

    print("有库存时的方案:")
    print(f"  tiles = {result_with_inv.get('tiles')}")
    cost_with_inv = result_with_inv.get('cost', 0)
    print(f"  成本 = {cost_with_inv}")
    print(f"  from_inventory = {result_with_inv.get('from_inventory', {})}")
    print()

    has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
    cost_lower = cost_with_inv < cost_no_inv
    cost_equal_2 = abs(cost_with_inv - cost_2) < 0.01  # 成本等于库存2个时
    from_inv_result = result_with_inv.get('from_inventory', {})
    check_inventory = check_inventory_not_exceeded(from_inv_result, inventory)

    print("验证项:")
    print(f'  [{"✓" if has_6x6 else "✗"}] 方案包含 6x6: {has_6x6}')
    print(f'  [{"✓" if cost_lower else "✗"}] 有库存成本({cost_with_inv}) < 无库存成本({cost_no_inv}): {cost_lower}')
    print(f'  [{"✓" if cost_equal_2 else "✗"}] 成本({cost_with_inv}) ≈ 库存2个时成本({cost_2}): {cost_equal_2}')
    print(f'  [{"✓" if check_inventory else "✗"}] 库存使用不超过提供数量: {check_inventory}')
    print()

    result = all([has_6x6, cost_lower, cost_equal_2, check_inventory])
    print(f"最终判断: {'✓ 场景3c通过' if result else '✗ 场景3c失败'}")
    return result


def scenario_4a():
    """场景 4a：批量模式（库存1个）"""
    print("\n" + "="*60)
    print("场景 4a: 批量模式（库存1个）")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 (9x12格子) -> 需要2个6x9")
    print("  抽屉2: 325x365 (11x13格子) -> 无6x9需求")
    print("  库存: 6x9 有 1 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

    print(f"抽屉1原始方案: {scheme1['tiles']}")
    print(f"抽屉2原始方案: {scheme2['tiles']}")
    print()

    # 无库存成本
    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )
    print(f"无库存总成本: {cost_no_inv}")
    print()

    # 库存1个
    inventory = {'6x9': 1}
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]

    # 计算总库存使用量
    total_used = sum(inv1.values()) + sum(inv2.values())

    print(f"优化后成本:")
    print(f"  抽屉1: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2: {drawer2_cost}, 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")
    print(f"  库存使用: {total_used}个, 提供: 1个")
    print()

    check1 = result['cost'] < cost_no_inv
    check2 = total_used <= 1  # 库存1个
    check3 = inv1.get('6x9', 0) == 1  # 抽屉1使用1个库存

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 总成本降低: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 库存使用不超过提供数量({total_used}<=1): {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 抽屉1使用1个库存: {check3} (实际={inv1.get("6x9", 0)})')
    print()

    result_final = check1 and check2 and check3
    print(f"最终判断: {'✓ 场景4a通过' if result_final else '✗ 场景4a失败'}")
    return result_final


def scenario_4b():
    """场景 4b：批量模式（库存2个）"""
    print("\n" + "="*60)
    print("场景 4b: 批量模式（库存2个）")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365")
    print("  库存: 6x9 有 2 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory={'6x9': 2}, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory={'6x9': 2}, verbose=False)

    print(f"抽屉1方案: {scheme1['tiles']}")
    print(f"抽屉2方案: {scheme2['tiles']}")
    print()

    # 无库存成本
    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )
    print(f"无库存总成本: {cost_no_inv}")
    print()

    # 库存2个
    inventory = {'6x9': 2}
    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
    total_used = sum(inv1.values()) + sum(inv2.values())

    print(f"优化后成本:")
    print(f"  抽屉1: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2: 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")
    print(f"  库存使用: {total_used}个, 提供: 2个")
    print()

    check1 = drawer1_cost == 0
    check2 = result['cost'] < cost_no_inv
    check3 = total_used <= 2  # 库存2个

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 总成本降低: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量({total_used}<=2): {check3}')
    print()

    result_final = all([check1, check2, check3])
    print(f"最终判断: {'✓ 场景4b通过' if result_final else '✗ 场景4b失败'}")
    return result_final


def scenario_4c():
    """场景 4c：批量模式（库存3个）- 全局优化"""
    print("\n" + "="*60)
    print("场景 4c: 批量模式（库存3个）- 全局优化")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 可重新规划使用6x9")
    print("  库存: 6x9 有 3 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    inventory = {'6x9': 3}
    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    print(f"抽屉1方案: {scheme1['tiles']}")
    print(f"抽屉2方案: {scheme2['tiles']}")
    print()

    # 无库存成本
    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )
    print(f"无库存总成本: {cost_no_inv}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
    total_used = sum(inv1.values()) + sum(inv2.values())

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]

    print(f"优化后成本:")
    print(f"  抽屉1: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2: {drawer2_cost}, 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")
    print(f"  库存使用: {total_used}个, 剩余: {3-total_used}个")
    print()

    check1 = drawer1_cost == 0
    check2 = drawer2_cost > 0  # 抽屉2需要打印
    check3 = total_used <= 3  # 库存3个
    check4 = inv2.get('6x9', 0) == 1  # 抽屉2使用1个库存

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2} (实际={drawer2_cost})')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量({total_used}<=3): {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 抽屉2使用1个库存: {check4} (实际={inv2.get("6x9", 0)})')
    print()

    result_final = all([check1, check2, check3, check4])
    print(f"最终判断: {'✓ 场景4c通过' if result_final else '✗ 场景4c失败'}")
    return result_final


def scenario_4d():
    """场景 4d：批量模式（库存4个）- 全局优化"""
    print("\n" + "="*60)
    print("场景 4d: 批量模式（库存4个）- 全局优化")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x9")
    print("  抽屉2: 325x365 -> 可重新规划使用6x9")
    print("  库存: 6x9 有 4 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    inventory = {'6x9': 4}
    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    print(f"抽屉1方案: {scheme1['tiles']}")
    print(f"抽屉2方案: {scheme2['tiles']}")
    print()

    # 无库存成本
    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )
    print(f"无库存总成本: {cost_no_inv}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
    total_used = sum(inv1.values()) + sum(inv2.values())

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]

    print(f"优化后成本:")
    print(f"  抽屉1: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2: {drawer2_cost}, 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")
    print(f"  库存使用: {total_used}个, 剩余: {4-total_used}个")
    print()

    check1 = drawer1_cost == 0
    check2 = drawer2_cost > 0  # 抽屉2需要打印
    check3 = total_used <= 4  # 库存4个
    check4 = inv2.get('6x9', 0) == 2  # 抽屉2使用2个库存

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 = 0: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2} (实际={drawer2_cost})')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量({total_used}<=4): {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 抽屉2使用2个库存: {check4} (实际={inv2.get("6x9", 0)})')
    print()

    result_final = all([check1, check2, check3, check4])
    print(f"最终判断: {'✓ 场景4d通过' if result_final else '✗ 场景4d失败'}")
    return result_final


def scenario_5():
    """场景 5：重新规划"""
    print("\n" + "="*60)
    print("场景 5: 重新规划")
    print("="*60)
    print("假设:")
    print("  抽屉: 265x360 (9x12格子)")
    print("  原始方案: 2个6x9")
    print("  库存: 6x6 有 2 个")
    print()

    grid = get_grid_dimensions(265, 360)
    print(f"抽屉格子尺寸: {grid}")
    print()

    # 使用 find_best_scheme 获取原始方案
    scheme = find_best_scheme(grid[0], grid[1], inventory=None, verbose=False)
    tiles = scheme.get('tiles', [])
    print(f"原始方案: {tiles}")
    print()

    inventory = {'6x6': 2}

    cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)
    print(f"原方案成本(无库存): {cost_no_inv}")
    print()

    result = replan_with_inventory(tiles, inventory, copies=1)

    if result:
        print("重新规划结果:")
        print(format_print_plan(result.get('tiles', []), inventory, copies=1))
        print()
        print(f"  tiles = {result.get('tiles')}")
        print(f"  cost = {result.get('cost')}")
        print(f"  from_inventory = {result.get('from_inventory', {})}")
        print(f"  need_print = {result.get('need_print', {})}")
    else:
        print("  返回 None（不需要重新规划）")
    print()

    has_6x6 = any(w == 6 and h == 6 for w, h in result.get('tiles', [])) if result else False
    need_print = result.get('need_print', {}) if result else {}
    check1 = result is not None
    check2 = has_6x6
    check3 = len(need_print) > 0  # 必须仍需打印
    check4 = result['cost'] < cost_no_inv if result else False
    check5 = check_inventory_not_exceeded(result.get('from_inventory', {}), inventory) if result else False

    # 检查格子数量一致性
    cells_consistent, cells_before, cells_after = check_cell_count_consistency(tiles, result.get('tiles', [])) if result else (False, 0, 0)
    check6 = cells_consistent

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] replan_with_inventory 返回非空结果: {check1}')
    print(f'  [{"✓" if check2 else "✗"}] 方案包含 6x6 瓦片: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] need_print 不为空（仍需打印）: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 成本 < 原方案成本: {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 库存使用不超过提供数量: {check5}')
    print(f'  [{"✓" if check6 else "✗"}] 格子数量一致({cells_before}={cells_after}): {check6}')
    print()

    result_final = all([check1, check2, check3, check4, check5, check6])
    print(f"最终判断: {'✓ 场景5通过' if result_final else '✗ 场景5失败'}")
    return result_final


def scenario_6a():
    """场景 6a：批量 + 重新规划（库存 3 个）"""
    print("\n" + "="*60)
    print("场景 6a: 批量 + 重新规划(库存3个)")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  库存: 6x6 有 3 个(正好够用)")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    inventory = {'6x6': 3}

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    print(f"抽屉1方案: {scheme1['tiles']}")
    print(f"  成本: {scheme1.get('cost')}")
    print(f"  from_inventory: {scheme1.get('from_inventory', {})}")
    print()

    print(f"抽屉2方案: {scheme2['tiles']}")
    print(f"  成本: {scheme2.get('cost')}")
    print(f"  from_inventory: {scheme2.get('from_inventory', {})}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
    total_used = sum(inv1.values()) + sum(inv2.values())

    print(f"批量优化结果:")
    print(f"  抽屉1成本: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2成本: {drawer2_cost}, 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")
    print(f"  库存使用: {total_used}个, 提供: 3个")

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2]
    )
    print(f"  无库存总成本: {cost_no_inv}")
    print()

    check1 = drawer1_cost > 0  # 抽屉1使用库存但仍需打印
    check2 = drawer2_cost > 0
    check3 = result['cost'] < cost_no_inv
    check4 = total_used <= 3  # 库存3个

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0（使用库存但仍需打印）: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2} (实际={drawer2_cost})')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量({total_used}<=3): {check4}')
    print()

    result_final = all([check1, check2, check3, check4])
    print(f"最终判断: {'✓ 场景6a通过' if result_final else '✗ 场景6a失败'}")
    return result_final


def scenario_6b():
    """场景 6b：批量 + 重新规划（库存 5 个）"""
    print("\n" + "="*60)
    print("场景 6b: 批量 + 重新规划(库存5个)")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  库存: 6x6 有 5 个(多2个)")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)

    inventory = {'6x6': 5}

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

    print(f"抽屉1方案: {scheme1['tiles']}")
    print(f"  成本: {scheme1.get('cost')}")
    print(f"  from_inventory: {scheme1.get('from_inventory', {})}")
    print()

    print(f"抽屉2方案: {scheme2['tiles']}")
    print(f"  成本: {scheme2.get('cost')}")
    print(f"  from_inventory: {scheme2.get('from_inventory', {})}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
    inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
    inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
    print(f"批量优化结果:")
    print(f"  抽屉1成本: {drawer1_cost}, 使用库存: {inv1}")
    print(f"  抽屉2成本: {drawer2_cost}, 使用库存: {inv2}")
    print(f"  总成本: {result['cost']}")

    total_used = sum(inv1.values()) + sum(inv2.values())
    remaining = 5 - total_used
    print(f"  库存使用: {total_used}个, 剩余: {remaining}个")
    print()

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0] for s in [scheme1, scheme2]
    )

    check1 = drawer1_cost > 0  # 抽屉1使用库存但仍需打印
    check2 = drawer2_cost > 0  # 抽屉2成本 > 0 (打印剩余)
    check3 = result['cost'] < cost_no_inv  # 总成本降低
    check4 = total_used <= 5  # 库存5个
    check5 = total_used == 3 and remaining == 2  # 库存使用3个，剩余2个

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0（使用库存但仍需打印）: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2} (实际={drawer2_cost})')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量({total_used}<=5): {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 库存扣减正确(使用3个，剩余2个): {check5} (使用{total_used}个，剩余{remaining}个)')
    print()

    result_final = check1 and check2 and check3 and check4 and check5
    print(f"最终判断: {'✓ 场景6b通过' if result_final else '✗ 场景6b失败'}")
    return result_final


def scenario_7a():
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""
    print("\n" + "="*60)
    print("场景 7a: 3抽屉+重新规划(库存3个)")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  抽屉3: 420x392 -> 不需要6x6")
    print("  库存: 6x6 有 3 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)
    grid3 = get_grid_dimensions(420, 392)

    inventory = {'6x6': 3}

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)
    scheme3 = find_best_scheme(grid3[0], grid3[1], inventory=inventory, verbose=False)

    print(f"抽屉1: {scheme1['tiles']}, 成本: {scheme1.get('cost')}")
    print(f"抽屉2: {scheme2['tiles']}, 成本: {scheme2.get('cost')}")
    print(f"抽屉3: {scheme3['tiles']}, 成本: {scheme3.get('cost')}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        {'grid': grid3, 'scheme': scheme3, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    print("批量优化结果:")
    for i, s in enumerate(result['schemes']):
        c = calculate_print_cost(s['tiles'], inventory, copies=1)[0]
        inv = calculate_print_cost(s['tiles'], inventory, copies=1)[1]
        print(f"  抽屉{i+1}: 成本={c}, 使用库存={inv}")
    print(f"  总成本: {result['cost']}")

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2, scheme3]
    )
    print(f"  无库存总成本: {cost_no_inv}")
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]

    # 格子数量一致性检查
    drawer1_cells_consistent, drawer1_cells_before, drawer1_cells_after = check_cell_count_consistency(
        scheme1['tiles'], result['schemes'][0]['tiles']
    )
    drawer2_cells_consistent, drawer2_cells_before, drawer2_cells_after = check_cell_count_consistency(
        scheme2['tiles'], result['schemes'][1]['tiles']
    )
    drawer3_cells_consistent, drawer3_cells_before, drawer3_cells_after = check_cell_count_consistency(
        scheme3['tiles'], result['schemes'][2]['tiles']
    )
    all_cells_consistent = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

    total_used = sum(
        sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
        for s in result['schemes']
    )
    check1 = drawer1_cost > 0  # 抽屉1使用库存但仍需打印
    check2 = result['cost'] < cost_no_inv  # 总成本降低
    check3 = total_used <= 3  # 库存3个
    check4 = all_cells_consistent  # 格子数量一致

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0（使用库存但仍需打印）: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 总成本 < 无库存成本: {check2}')
    print(f'  [{"✓" if check3 else "✗"}] 库存使用不超过提供数量({total_used}<=3): {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 格子数量一致: {check4} (抽屉1:{drawer1_cells_before}={drawer1_cells_after}, 抽屉2:{drawer2_cells_before}={drawer2_cells_after}, 抽屉3:{drawer3_cells_before}={drawer3_cells_after})')
    print()

    result_final = check1 and check2 and check3 and check4
    print(f"最终判断: {'✓ 场景7a通过' if result_final else '✗ 场景7a失败'}")
    return result_final


def scenario_7b():
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""
    print("\n" + "="*60)
    print("场景 7b: 3抽屉+重新规划(库存5个) - 最复杂场景")
    print("="*60)
    print("假设:")
    print("  抽屉1: 265x360 -> 需要2个6x6")
    print("  抽屉2: 325x365 -> 需要1个6x6")
    print("  抽屉3: 420x392 -> 可重新规划使用6x6")
    print("  库存: 6x6 有 5 个")
    print()

    grid1 = get_grid_dimensions(265, 360)
    grid2 = get_grid_dimensions(325, 365)
    grid3 = get_grid_dimensions(420, 392)

    inventory = {'6x6': 5}

    scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
    scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)
    scheme3 = find_best_scheme(grid3[0], grid3[1], inventory=inventory, verbose=False)

    print(f"抽屉1: {scheme1['tiles']}, 成本: {scheme1.get('cost')}")
    print(f"抽屉2: {scheme2['tiles']}, 成本: {scheme2.get('cost')}")
    print(f"抽屉3: {scheme3['tiles']}, 成本: {scheme3.get('cost')}")
    print()

    batch_results = [
        {'grid': grid1, 'scheme': scheme1, 'copies': 1},
        {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        {'grid': grid3, 'scheme': scheme3, 'copies': 1},
    ]
    result = optimize_batch_global(batch_results, inventory=inventory)

    print(format_batch_print_plan(batch_results, inventory, optimized_schemes=result['schemes']))
    print()

    print("批量优化结果:")
    for i, s in enumerate(result['schemes']):
        c = calculate_print_cost(s['tiles'], inventory, copies=1)[0]
        inv = calculate_print_cost(s['tiles'], inventory, copies=1)[1]
        print(f"  抽屉{i+1}: 成本={c}, 使用库存={inv}")
    print(f"  总成本: {result['cost']}")

    cost_no_inv = sum(
        calculate_print_cost(s['tiles'], {}, copies=1)[0]
        for s in [scheme1, scheme2, scheme3]
    )
    print(f"  无库存总成本: {cost_no_inv}")
    print()

    drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
    drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]

    # 格子数量一致性检查
    drawer1_cells_consistent, drawer1_cells_before, drawer1_cells_after = check_cell_count_consistency(
        scheme1['tiles'], result['schemes'][0]['tiles']
    )
    drawer2_cells_consistent, drawer2_cells_before, drawer2_cells_after = check_cell_count_consistency(
        scheme2['tiles'], result['schemes'][1]['tiles']
    )
    drawer3_cells_consistent, drawer3_cells_before, drawer3_cells_after = check_cell_count_consistency(
        scheme3['tiles'], result['schemes'][2]['tiles']
    )
    all_cells_consistent = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

    total_used = sum(
        sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
        for s in result['schemes']
    )
    check1 = drawer1_cost > 0  # 抽屉1使用库存但仍需打印
    check2 = drawer2_cost > 0  # 抽屉2成本 > 0
    check3 = result['cost'] < cost_no_inv  # 总成本降低
    check4 = total_used <= 5  # 库存5个
    check5 = all_cells_consistent  # 格子数量一致

    print("验证项:")
    print(f'  [{"✓" if check1 else "✗"}] 抽屉1成本 > 0（使用库存但仍需打印）: {check1} (实际={drawer1_cost})')
    print(f'  [{"✓" if check2 else "✗"}] 抽屉2成本 > 0: {check2} (实际={drawer2_cost})')
    print(f'  [{"✓" if check3 else "✗"}] 总成本 < 无库存成本: {check3}')
    print(f'  [{"✓" if check4 else "✗"}] 库存使用不超过提供数量({total_used}<=5): {check4}')
    print(f'  [{"✓" if check5 else "✗"}] 格子数量一致: {check5} (抽屉1:{drawer1_cells_before}={drawer1_cells_after}, 抽屉2:{drawer2_cells_before}={drawer2_cells_after}, 抽屉3:{drawer3_cells_before}={drawer3_cells_after})')
    print()

    result_final = check1 and check2 and check3 and check4 and check5
    print(f"最终判断: {'✓ 场景7b通过' if result_final else '✗ 场景7b失败'}")
    return result_final


def main():
    parser = argparse.ArgumentParser(
        description="库存感知评分系统 v2 验证脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/verify_scenarios.py           # 运行所有场景
  python3 scripts/verify_scenarios.py 5           # 运行场景5
  python3 scripts/verify_scenarios.py 4c         # 运行场景4c
  python3 scripts/verify_scenarios.py 1 2 3a     # 运行多个场景
  python3 scripts/verify_scenarios.py all        # 运行所有场景

可用场景: 1, 2, 3a, 3b, 3c, 4a, 4b, 4c, 4d, 5, 6a, 6b, 7a, 7b
        """
    )
    parser.add_argument('scenarios', nargs='*', help='要运行的场景编号或标识 (如: 5, 4c, 1 2 3a)')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有可用场景')

    args = parser.parse_args()

    # 定义所有场景
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
    }

    # 列出所有场景
    if args.list:
        print("可用场景:")
        for key in ['1', '2', '3a', '3b', '3c', '4a', '4b', '4c', '4d', '5', '6a', '6b', '7a', '7b']:
            name, _ = all_scenarios[key]
            print(f"  {key}: {name}")
        return

    # 确定要运行的场景
    if not args.scenarios or 'all' in args.scenarios:
        # 运行所有场景
        scenarios_to_run = list(all_scenarios.keys())
    else:
        scenarios_to_run = args.scenarios

    # 验证场景标识是否有效
    invalid_scenarios = [s for s in scenarios_to_run if s not in all_scenarios]
    if invalid_scenarios:
        print(f"错误: 无效的场景标识: {invalid_scenarios}")
        print(f"可用场景: {list(all_scenarios.keys())}")
        return

    print("="*60)
    print("库存感知评分系统 v2 验证")
    print("="*60)
    print(f"运行场景: {', '.join(scenarios_to_run)}")
    print()

    results = []

    # 按顺序运行场景
    for key in ['1', '2', '3a', '3b', '3c', '4a', '4b', '4c', '4d', '5', '6a', '6b', '7a', '7b']:
        if key in scenarios_to_run:
            name, func = all_scenarios[key]
            passed = func()
            results.append((name, passed))

    # 汇总结果
    if len(results) > 1:
        print("\n" + "="*60)
        print("验证结果汇总")
        print("="*60)
        for name, passed in results:
            print(f"  [{'✓' if passed else '✗'}] {name}")

        total = len(results)
        passed_count = sum(1 for _, p in results if p)
        print(f"\n总计: {passed_count}/{total} 通过")

        if passed_count < total:
            print("\n发现的问题:")
            for name, passed in results:
                if not passed:
                    print(f"  - {name}")


if __name__ == "__main__":
    main()
