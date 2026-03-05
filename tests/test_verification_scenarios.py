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
)

from conftest import find_best_scheme

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


class TestScenario13aBasicTileSharing:
    """场景 13a：批量模式瓦片共享基础验证

    A=504×308(18×11格子,copies=1) 独立最优 {9×11:2}
    B=336×308(12×11格子,copies=1) 独立最优 {6×11:2}
    optimize_batch_global 应把 A 切换为 {6×11:3}，total_prints 从 2 降至 1
    """

    def test_batch_unifies_tile_sizes_to_reduce_plates(self):
        """两抽屉各自最优 tile 不同时，批量优化统一到同种 tile 减少打印次数"""
        from opengrid.cli.commands.split import calculate_single, calculate_total_prints

        result_A = calculate_single(504, 308, copies=1)
        result_B = calculate_single(336, 308, copies=1)
        batch_results = [result_A, result_B]

        opt = optimize_batch_global(batch_results, inventory=None)

        assert opt['improved'] is True
        assert opt['initial_prints'] == 2, f"优化前应为 2 plates，实际: {opt['initial_prints']}"
        assert opt['total_prints'] == 1, f"优化后应为 1 plate，实际: {opt['total_prints']}"

        scheme_A_tiles = set(opt['schemes'][0]['tiles'])
        assert (6, 11) in scheme_A_tiles, f"A 优化后应有 (6,11)，实际: {scheme_A_tiles}"
        assert (9, 11) not in scheme_A_tiles, f"A 优化后不应有 (9,11)，实际: {scheme_A_tiles}"

        _, details = calculate_total_prints(batch_results, opt['schemes'])
        assert details.get((6, 11), {}).get('stacks', 0) == 5, (
            f"6×11 总 stacks 应为 5(3+2)，实际: {details}"
        )


class TestScenario13bTileSharingInventoryAmplification:
    """场景 13b：瓦片共享 × 库存命中率倍增

    在 13a 基础上引入库存 {6x11: 5}。
    独立计算时 A({9×11})无法命中，批量优化后 A+B 共用 6×11，库存恰好全部用尽，cost=0。
    """

    def test_tile_sharing_enables_full_inventory_coverage(self):
        """切换到 6×11 后，库存 5 个恰好覆盖 A(3个)+B(2个)，总成本降至 0"""
        from opengrid.cli.commands.split import calculate_single

        inventory = {'6x11': 5}
        result_A = calculate_single(504, 308, copies=1)
        result_B = calculate_single(336, 308, copies=1)
        batch_results = [result_A, result_B]

        opt = optimize_batch_global(batch_results, inventory=inventory)

        assert opt['improved'] is True, "库存命中率提升，应标记为 improved"
        assert opt['cost'] == 0.0, f"5 个库存恰好覆盖，总成本应为 0，实际: {opt['cost']}"


class TestScenario13cThreeDrawersPartialSharing:
    """场景 13c：3 抽屉部分共享

    A=504×308(18×11) 独立最优 {9×11:2}，可切换为 {6×11:3}
    B=336×308(12×11) 独立最优 {6×11:2}
    C=392×308(14×11) 独立最优 {7×11:2}，14 不能被 6 整除，无法纯切换为 6×11
    预期：A+B 共享 6×11，C 保持 7×11，unique sizes 从 3 降至 2，total_prints 从 3 降至 2
    """

    def test_partial_sharing_reduces_unique_sizes_to_two(self):
        """A+B 可共享 6×11，C 无法整除，unique sizes 3→2，total_prints 3→2"""
        from opengrid.cli.commands.split import calculate_single, calculate_total_prints

        result_A = calculate_single(504, 308, copies=1)
        result_B = calculate_single(336, 308, copies=1)
        result_C = calculate_single(392, 308, copies=1)
        batch_results = [result_A, result_B, result_C]

        opt = optimize_batch_global(batch_results, inventory=None)

        assert opt['improved'] is True, "A 切换为 6×11 可减少 plates，应标记为 improved"
        assert opt['initial_prints'] == 3, f"优化前应为 3 plates，实际: {opt['initial_prints']}"
        assert opt['total_prints'] == 2, f"优化后应为 2 plates，实际: {opt['total_prints']}"

        scheme_A_tiles = set(opt['schemes'][0]['tiles'])
        assert (6, 11) in scheme_A_tiles, f"A 应切换为 6×11，实际: {scheme_A_tiles}"
        assert (9, 11) not in scheme_A_tiles, f"A 不应保留 9×11，实际: {scheme_A_tiles}"

        scheme_C_tiles = set(opt['schemes'][2]['tiles'])
        assert (7, 11) in scheme_C_tiles, f"C 应保持 7×11，实际: {scheme_C_tiles}"
        assert (6, 11) not in scheme_C_tiles, f"C 不应被切换为 6×11，实际: {scheme_C_tiles}"

        _, details = calculate_total_prints(batch_results, opt['schemes'])
        assert len(details) == 2, f"应有 2 种独立 tile，实际: {list(details.keys())}"
        assert (6, 11) in details, "6×11 应在合并结果中"
        assert (7, 11) in details, "7×11 应在合并结果中"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
