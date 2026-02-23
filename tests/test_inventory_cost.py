import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from opengrid.core import calculate_print_cost, get_grid_dimensions, find_best_scheme, replan_with_inventory
from opengrid.core.stats import calculate_filament_and_time
from opengrid.cli.commands.split import optimize_batch_global


class TestCalculatePrintCost:
    """测试打印成本计算"""

    def test_exact_match_cost_zero(self):
        """精确匹配：成本为 0"""
        # 265x360 -> 9x12 格, 瓦片 6x9
        tiles = [(6, 9)]
        inventory = {'6x9': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert cost == 0, f"Expected 0, got {cost}"
        assert from_inv == {'6x9': 1}
        assert need_print == {}

    def test_partial_match(self):
        """部分匹配：只计算差额"""
        tiles = [(6, 7), (6, 7)]  # 需要 2 个 6x7
        inventory = {'6x7': 1}     # 只有 1 个
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert from_inv['6x7'] == 1
        assert need_print['6x7'] == 1
        assert cost > 0  # 需要打印 1 个

    def test_no_match(self):
        """无匹配：全部计算成本"""
        tiles = [(6, 9)]
        inventory = {'6x7': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert cost > 0
        assert need_print['6x9'] == 1

    def test_copies_multiplication(self):
        """多份打印：需求翻倍"""
        tiles = [(6, 7)]
        inventory = {'6x7': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=2)
        # 需要 2 个，只有 1 个，差额 1 个
        assert from_inv['6x7'] == 1
        assert need_print['6x7'] == 1


class TestFindBestSchemeWithInventory:
    """测试带库存的 find_best_scheme"""

    def test_prefers_inventory_solution(self):
        """有库存时优先选择库存成本低的方案"""
        # 265x360 -> 9x12 格子
        # 原始最优方案是 [(6,9), (6,9)]
        # 添加 6x9 库存使得该方案成本为 0
        inventory = {'6x9': 5}  # 6x9 库存充足

        result = find_best_scheme(9, 12, inventory=inventory, verbose=False)

        # 验证返回结果包含成本信息
        assert 'cost' in result, "Result should contain 'cost' key"
        assert 'from_inventory' in result, "Result should contain 'from_inventory' key"
        assert 'need_print' in result, "Result should contain 'need_print' key"
        # 验证成本为 0（完全使用库存）
        assert result['cost'] == 0, f"Expected cost 0 when inventory matches, got {result['cost']}"
        # 验证使用的是 6x9 瓦片
        assert result['tiles'] == [(6, 9), (6, 9)], f"Expected 6x9 tiles, got {result['tiles']}"

    def test_no_inventory_uses_original_logic(self):
        """无库存时使用原始评分逻辑"""
        result = find_best_scheme(9, 12, inventory=None, verbose=False)
        # 不应该崩溃，返回正常方案
        assert 'tiles' in result
        assert 'x_splits' in result
        assert 'y_splits' in result
        # 不应该有库存相关键（因为没有库存）
        assert 'cost' not in result, "Should not have cost key when inventory is None"

    def test_with_partial_inventory(self):
        """部分库存：优先选择能使用库存的方案"""
        # 6x9 库存只有 1 个，不够用 2 个
        inventory = {'6x9': 1}

        result = find_best_scheme(9, 12, inventory=inventory, verbose=False)

        # 应该返回有成本信息的方案
        assert 'cost' in result
        # 成本应该大于 0（因为库存不足）
        assert result['cost'] > 0


class TestReplanWithInventory:
    """测试边缘情况5：需求与库存不匹配时的重新规划"""

    def test_replan_uses_partial_inventory(self):
        """当库存尺寸不完全匹配时，拆分方案使用部分库存"""
        # 需求: 9x12 格子，抽屉可以分割成 2个6x9
        # 库存: 6x6 有 2 个
        # 方案: 使用 2 个 6x6 库存，剩余空间打印 3x6
        tiles = [(6, 9), (6, 9)]
        inventory = {'6x6': 2}
        # 需要传入grid参数才能正确重新规划
        grid = (9, 12)

        result = replan_with_inventory(tiles, inventory, grid=grid)

        # 应该返回重新规划后的方案
        assert result is not None, "Should replan when partial inventory available"
        assert 'tiles' in result
        # 至少使用 1 个 6x6 库存
        assert result['from_inventory'].get('6x6', 0) >= 1

    def test_no_replan_needed_when_exact_match(self):
        """精确匹配时不需要重新规划"""
        tiles = [(6, 7)]
        inventory = {'6x7': 1}

        # 精确匹配时不需要重新规划
        result = replan_with_inventory(tiles, inventory)
        # 返回 None 表示不需要重新规划
        assert result is None

    def test_replan_improves_cost(self):
        """重新规划应该降低打印成本"""
        # 原始方案: 6x9 (成本高)
        # 重新规划: 使用 6x6 库存 + 打印剩余
        tiles = [(6, 9)]
        inventory = {'6x6': 1}

        # 重新规划后成本应该降低
        result = replan_with_inventory(tiles, inventory)

        if result:
            # 如果成功重新规划，比较成本
            original_cost, _, _ = calculate_print_cost(tiles, {}, copies=1)
            assert result['cost'] < original_cost, "Replanned cost should be lower"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestBatchOptimizationWithInventory:
    """测试批量优化与库存集成"""

    def test_optimize_batch_with_inventory(self):
        """批量优化时考虑库存成本"""
        # 模拟两个抽屉的结果
        batch_results = [
            {'grid': (9, 12), 'scheme': {'tiles': [(6, 9)], 'tile_count': 1}, 'copies': 1},
            {'grid': (11, 13), 'scheme': {'tiles': [(6, 11)], 'tile_count': 1}, 'copies': 1},
        ]

        # 有库存时，应该使用库存成本进行优化
        inventory = {'6x9': 1, '6x11': 1}

        result = optimize_batch_global(batch_results, inventory=inventory)

        assert result is not None
        assert 'schemes' in result
        assert 'cost' in result  # 应该有成本信息

    def test_optimize_batch_without_inventory(self):
        """无库存时使用原始逻辑"""
        batch_results = [
            {'grid': (9, 12), 'scheme': {'tiles': [(6, 9)], 'tile_count': 1}, 'copies': 1},
            {'grid': (11, 13), 'scheme': {'tiles': [(6, 11)], 'tile_count': 1}, 'copies': 1},
        ]

        result = optimize_batch_global(batch_results)  # 无 inventory

        assert result is not None
        assert 'schemes' in result
        assert 'total_prints' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
