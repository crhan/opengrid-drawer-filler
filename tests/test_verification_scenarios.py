"""
库存感知评分系统验证测试

将 verify_scenarios.py 中的所有验证场景迁移到单元测试，
确保测试要求与验证脚本完全一致。

场景：
1. 精确匹配 - 成本 = 0
2. 部分匹配 - 只计算差额
3a. 库存方案选择(1个) - 算法优先选择库存方案
3b. 库存方案选择(2个) - 成本进一步降低
3c. 库存方案选择(3个) - 完全使用库存
4a. 批量模式(库存1个) - 部分使用库存
4b. 批量模式(库存2个) - 抽屉1成本=0
4c. 批量模式(库存3个) - 全局优化
4d. 批量模式(库存4个) - 全局优化+剩余库存
5. 重新规划 - 非精确匹配处理
6a. 批量+重新规划(3个) - 库存刚好够用
6b. 批量+重新规划(5个) - 库存有余
7a. 3抽屉+重新规划(3个) - 3抽屉全局优化
7b. 3抽屉+重新规划(5个) - 库存重新规划优化
8. 6抽屉+双库存尺寸(8x8,6x7) - 多种库存尺寸批量优化
"""

import pytest

from opengrid.core import (
    calculate_print_cost,
    get_grid_dimensions,
    find_best_scheme,
    replan_with_inventory,
)

from opengrid.cli.commands.split import optimize_batch_global


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


class TestScenario1ExactMatch:
    """场景 1：精确匹配 - 成本 = 0"""

    def test_cost_zero_when_exact_match(self):
        """精确匹配时成本为 0"""
        tiles = [(6, 7), (6, 7)]
        inventory = {'6x7': 2}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)

        assert cost == 0, f"Expected 0, got {cost}"
        assert from_inv == {'6x7': 2}
        assert need_print == {}
        assert check_inventory_not_exceeded(from_inv, inventory)


class TestScenario2PartialMatch:
    """场景 2：部分匹配 - 只计算差额"""

    def test_partial_match_cost_calculation(self):
        """部分匹配时只计算差额"""
        tiles = [(6, 7), (6, 7)]  # 需要 2 个 6x7
        inventory = {'6x7': 1}     # 只有 1 个

        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

        assert from_inv == {'6x7': 1}
        assert need_print == {'6x7': 1}
        assert cost > 0 and cost < cost_no_inv
        assert check_inventory_not_exceeded(from_inv, inventory)


class TestScenario3aInventoryScheme1:
    """场景 3a：库存方案选择（库存1个）"""

    def test_prefers_inventory_solution_1(self):
        """有库存1个时优先选择库存方案"""
        grid = get_grid_dimensions(265, 360)  # 9x12格子
        inventory = {'6x6': 1}

        result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
        cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

        result_with_inv = find_best_scheme(9, 12, inventory=inventory, verbose=False)
        cost_with_inv = result_with_inv.get('cost', 0)

        has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
        from_inv_result = result_with_inv.get('from_inventory', {})

        assert has_6x6, "方案应包含 6x6"
        assert cost_with_inv < cost_no_inv, f"成本应降低: {cost_with_inv} < {cost_no_inv}"
        assert check_inventory_not_exceeded(from_inv_result, inventory)


class TestScenario3bInventoryScheme2:
    """场景 3b：库存方案选择（库存2个）"""

    def test_prefers_inventory_solution_2(self):
        """有库存2个时成本进一步降低"""
        grid = get_grid_dimensions(265, 360)  # 9x12格子

        result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
        cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

        inventory_1 = {'6x6': 1}
        result_1 = find_best_scheme(9, 12, inventory=inventory_1, verbose=False)
        cost_1 = result_1.get('cost', 0)

        inventory_2 = {'6x6': 2}
        result_with_inv = find_best_scheme(9, 12, inventory=inventory_2, verbose=False)
        cost_with_inv = result_with_inv.get('cost', 0)

        has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
        from_inv_result = result_with_inv.get('from_inventory', {})

        assert has_6x6, "方案应包含 6x6"
        assert cost_with_inv < cost_no_inv, f"成本应降低: {cost_with_inv} < {cost_no_inv}"
        assert cost_with_inv < cost_1, f"成本应低于库存1个时: {cost_with_inv} < {cost_1}"
        assert check_inventory_not_exceeded(from_inv_result, inventory_2)


class TestScenario3cInventoryScheme3:
    """场景 3c：库存方案选择（库存3个）"""

    def test_prefers_inventory_solution_3(self):
        """有库存3个时成本等于库存2个（抽屉只能用到2个）"""
        grid = get_grid_dimensions(265, 360)  # 9x12格子

        result_no_inv = find_best_scheme(9, 12, inventory=None, verbose=False)
        cost_no_inv = calculate_print_cost(result_no_inv['tiles'], {}, copies=1)[0]

        inventory_2 = {'6x6': 2}
        result_2 = find_best_scheme(9, 12, inventory=inventory_2, verbose=False)
        cost_2 = result_2.get('cost', 0)

        inventory_3 = {'6x6': 3}
        result_with_inv = find_best_scheme(9, 12, inventory=inventory_3, verbose=False)
        cost_with_inv = result_with_inv.get('cost', 0)

        has_6x6 = any(w == 6 and h == 6 for w, h in result_with_inv.get('tiles', []))
        from_inv_result = result_with_inv.get('from_inventory', {})

        assert has_6x6, "方案应包含 6x6"
        assert cost_with_inv < cost_no_inv, f"成本应降低: {cost_with_inv} < {cost_no_inv}"
        assert abs(cost_with_inv - cost_2) < 0.01, f"成本应等于库存2个时: {cost_with_inv} ≈ {cost_2}"
        assert check_inventory_not_exceeded(from_inv_result, inventory_3)


class TestScenario4aBatch1Inventory:
    """场景 4a：批量模式（库存1个）"""

    def test_batch_mode_1_inventory(self):
        """批量模式下库存1个，部分使用"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)

        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=None, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=None, verbose=False)

        # 无库存成本
        cost_no_inv = sum(
            calculate_print_cost(s['tiles'], {}, copies=1)[0]
            for s in [scheme1, scheme2]
        )

        # 库存1个
        inventory = {'6x9': 1}
        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]

        total_used = sum(inv1.values()) + sum(inv2.values())

        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used <= 1, f"库存使用不超过1个: {total_used}"
        assert inv1.get('6x9', 0) == 1, f"抽屉1应使用1个库存: {inv1.get('6x9', 0)}"


class TestScenario4bBatch2Inventory:
    """场景 4b：批量模式（库存2个）"""

    def test_batch_mode_2_inventory(self):
        """批量模式下库存2个，抽屉1成本=0"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)

        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory={'6x9': 2}, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory={'6x9': 2}, verbose=False)

        cost_no_inv = sum(
            calculate_print_cost(s['tiles'], {}, copies=1)[0]
            for s in [scheme1, scheme2]
        )

        inventory = {'6x9': 2}
        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
        total_used = sum(inv1.values()) + sum(inv2.values())

        assert drawer1_cost == 0, f"抽屉1成本应为0: {drawer1_cost}"
        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used <= 2, f"库存使用不超过2个: {total_used}"


class TestScenario4cBatch3Inventory:
    """场景 4c：批量模式（库存3个）- 全局优化"""

    def test_batch_mode_3_inventory_global_optimization(self):
        """批量模式下库存3个，全局优化"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)

        inventory = {'6x9': 3}
        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
        total_used = sum(inv1.values()) + sum(inv2.values())

        assert drawer1_cost == 0, f"抽屉1成本应为0: {drawer1_cost}"
        assert drawer2_cost > 0, f"抽屉2成本应大于0: {drawer2_cost}"
        assert total_used <= 3, f"库存使用不超过3个: {total_used}"
        assert inv2.get('6x9', 0) == 1, f"抽屉2应使用1个库存: {inv2.get('6x9', 0)}"


class TestScenario4dBatch4Inventory:
    """场景 4d：批量模式（库存4个）- 全局优化+剩余库存"""

    def test_batch_mode_4_inventory_with_remaining(self):
        """批量模式下库存4个，11x13格子最多只能包含1个6x9"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)  # 11x13格子

        inventory = {'6x9': 4}
        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
        total_used = sum(inv1.values()) + sum(inv2.values())

        assert drawer1_cost == 0, f"抽屉1成本应为0: {drawer1_cost}"
        assert drawer2_cost > 0, f"抽屉2成本应大于0: {drawer2_cost}"
        assert total_used <= 4, f"库存使用不超过4个: {total_used}"
        # 11x13格子最多只能包含1个6x9，所以抽屉2只能用1个库存
        assert inv2.get('6x9', 0) >= 1, f"抽屉2应至少使用1个库存: {inv2.get('6x9', 0)}"


class TestScenario5Replan:
    """场景 5：重新规划"""

    def test_replan_with_partial_inventory(self):
        """库存尺寸不匹配时重新规划"""
        grid = get_grid_dimensions(265, 360)  # 9x12格子

        scheme = find_best_scheme(grid[0], grid[1], inventory=None, verbose=False)
        tiles = scheme.get('tiles', [])  # [(6,9), (6,9)]

        inventory = {'6x6': 2}

        cost_no_inv, _, _ = calculate_print_cost(tiles, {}, copies=1)

        result = replan_with_inventory(tiles, inventory, copies=1, grid=grid)

        assert result is not None, "应返回重新规划后的结果"
        has_6x6 = any(w == 6 and h == 6 for w, h in result.get('tiles', []))
        need_print = result.get('need_print', {})

        assert has_6x6, "方案应包含 6x6"
        assert len(need_print) > 0, "仍需打印"
        assert result['cost'] < cost_no_inv, "成本应降低"
        assert check_inventory_not_exceeded(result.get('from_inventory', {}), inventory)

        # 格子数量一致性
        cells_consistent, cells_before, cells_after = check_cell_count_consistency(tiles, result.get('tiles', []))
        assert cells_consistent, f"格子数量应一致: {cells_before} = {cells_after}"


class TestScenario6aBatchWithReplan3:
    """场景 6a：批量 + 重新规划（库存 3 个）"""

    def test_batch_with_replan_3_inventory(self):
        """批量模式下库存刚好够用"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)

        inventory = {'6x6': 3}

        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]
        total_used = sum(inv1.values()) + sum(inv2.values())

        cost_no_inv = sum(
            calculate_print_cost(s['tiles'], {}, copies=1)[0]
            for s in [scheme1, scheme2]
        )

        # 格子数量一致性检查
        drawer1_cells_consistent, _, _ = check_cell_count_consistency(
            scheme1['tiles'], result['schemes'][0]['tiles']
        )
        drawer2_cells_consistent, _, _ = check_cell_count_consistency(
            scheme2['tiles'], result['schemes'][1]['tiles']
        )

        assert drawer1_cost > 0, f"抽屉1成本应大于0: {drawer1_cost}"
        assert drawer2_cost > 0, f"抽屉2成本应大于0: {drawer2_cost}"
        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used <= 3, f"库存使用不超过3个: {total_used}"
        assert drawer1_cells_consistent and drawer2_cells_consistent, "格子数量应一致"


class TestScenario6bBatchWithReplan5:
    """场景 6b：批量 + 重新规划（库存 5 个）"""

    def test_batch_with_replan_5_inventory(self):
        """批量模式下库存有余"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)

        inventory = {'6x6': 5}

        scheme1 = find_best_scheme(grid1[0], grid1[1], inventory=inventory, verbose=False)
        scheme2 = find_best_scheme(grid2[0], grid2[1], inventory=inventory, verbose=False)

        batch_results = [
            {'grid': grid1, 'scheme': scheme1, 'copies': 1},
            {'grid': grid2, 'scheme': scheme2, 'copies': 1},
        ]
        result = optimize_batch_global(batch_results, inventory=inventory)

        drawer1_cost = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[0]
        drawer2_cost = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[0]
        inv1 = calculate_print_cost(result['schemes'][0]['tiles'], inventory, copies=1)[1]
        inv2 = calculate_print_cost(result['schemes'][1]['tiles'], inventory, copies=1)[1]

        total_used = sum(inv1.values()) + sum(inv2.values())
        remaining = 5 - total_used

        cost_no_inv = sum(
            calculate_print_cost(s['tiles'], {}, copies=1)[0]
            for s in [scheme1, scheme2]
        )

        assert drawer1_cost > 0, f"抽屉1成本应大于0: {drawer1_cost}"
        assert drawer2_cost > 0, f"抽屉2成本应大于0: {drawer2_cost}"
        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used <= 5, f"库存使用不超过5个: {total_used}"
        assert total_used == 3 and remaining == 2, f"库存使用3个，剩余2个: 使用{total_used}个，剩余{remaining}个"


class TestScenario7aThreeDrawersWithReplan3:
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""

    def test_3_drawers_with_3_inventory(self):
        """3个抽屉，库存刚好够用"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)
        grid3 = get_grid_dimensions(420, 392)

        inventory = {'6x6': 3}

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

        total_used = sum(
            sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
            for s in result['schemes']
        )

        # 格子数量一致性检查
        drawer1_cells_consistent, _, _ = check_cell_count_consistency(
            scheme1['tiles'], result['schemes'][0]['tiles']
        )
        drawer2_cells_consistent, _, _ = check_cell_count_consistency(
            scheme2['tiles'], result['schemes'][1]['tiles']
        )
        drawer3_cells_consistent, _, _ = check_cell_count_consistency(
            scheme3['tiles'], result['schemes'][2]['tiles']
        )
        all_cells_consistent = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

        assert drawer1_cost > 0, f"抽屉1成本应大于0: {drawer1_cost}"
        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used == 3, f"库存应恰好使用3个: {total_used}"
        assert all_cells_consistent, "格子数量应一致"


class TestScenario7bThreeDrawersWithReplan5:
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""

    def test_3_drawers_with_5_inventory(self):
        """3个抽屉，库存有余，需要重新规划"""
        grid1 = get_grid_dimensions(265, 360)
        grid2 = get_grid_dimensions(325, 365)
        grid3 = get_grid_dimensions(420, 392)

        inventory = {'6x6': 5}

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

        total_used = sum(
            sum(calculate_print_cost(s['tiles'], inventory, copies=1)[1].values())
            for s in result['schemes']
        )

        # 格子数量一致性检查
        drawer1_cells_consistent, _, _ = check_cell_count_consistency(
            scheme1['tiles'], result['schemes'][0]['tiles']
        )
        drawer2_cells_consistent, _, _ = check_cell_count_consistency(
            scheme2['tiles'], result['schemes'][1]['tiles']
        )
        drawer3_cells_consistent, _, _ = check_cell_count_consistency(
            scheme3['tiles'], result['schemes'][2]['tiles']
        )
        all_cells_consistent = drawer1_cells_consistent and drawer2_cells_consistent and drawer3_cells_consistent

        assert drawer1_cost > 0, f"抽屉1成本应大于0: {drawer1_cost}"
        assert drawer2_cost > 0, f"抽屉2成本应大于0: {drawer2_cost}"
        assert result['cost'] < cost_no_inv, "总成本应降低"
        assert total_used <= 5, f"库存使用不超过5个: {total_used}"
        assert all_cells_consistent, "格子数量应一致"


class TestScenario8SixDrawersDualInventory:
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）"""

    def test_6_drawers_dual_inventory_sizes(self):
        """多个抽屉、多种库存尺寸的全局优化"""
        # 准备批量数据 (3个尺寸 × 2份 = 6个抽屉)
        batch_results = []
        configs = [
            (265, 360, 2),  # 抽屉1,2
            (325, 360, 2),  # 抽屉3,4
            (315, 360, 2),  # 抽屉5,6
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

        inventory = {'8x8': 5, '6x7': 5}

        # 无库存总成本
        no_inv_cost = sum(
            calculate_print_cost(r['scheme']['tiles'], {}, r['copies'])[0]
            for r in batch_results
        )

        # 批量优化
        result = optimize_batch_global(batch_results, inventory=inventory)

        # 按顺序计算每个抽屉的库存使用（模拟批量优化过程）
        drawer_costs = []
        drawer_inv = []

        remaining_inv = dict(inventory)
        for i, r in enumerate(batch_results):
            scheme = result['schemes'][i]
            cost, from_inv, need_print = calculate_print_cost(scheme['tiles'], remaining_inv, r['copies'])
            drawer_costs.append(cost)
            drawer_inv.append(from_inv)
            # 更新剩余库存
            for k, v in from_inv.items():
                remaining_inv[k] = remaining_inv.get(k, 0) - v

        # 汇总库存使用
        total_inv = {}
        for inv in drawer_inv:
            for k, v in inv.items():
                total_inv[k] = total_inv.get(k, 0) + v

        # 格子数量一致性检查
        all_cells_consistent = True
        for i, r in enumerate(batch_results):
            original_tiles = r['scheme']['tiles']
            optimized_tiles = result['schemes'][i]['tiles']
            consistent, _, _ = check_cell_count_consistency(original_tiles, optimized_tiles)
            all_cells_consistent = all_cells_consistent and consistent

        assert result['cost'] < no_inv_cost, "总成本应降低"
        assert total_inv.get('8x8', 0) <= inventory['8x8'], "8x8库存不超限"
        assert total_inv.get('6x7', 0) <= inventory['6x7'], "6x7库存不超限"
        assert all(c > 0 for c in drawer_costs), "所有抽屉都有打印成本"
        assert all_cells_consistent, "格子数量应一致"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
