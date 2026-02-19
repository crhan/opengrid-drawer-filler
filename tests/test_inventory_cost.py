import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from split_calc import calculate_print_cost, calculate_filament_and_time, get_grid_dimensions, find_best_scheme


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
