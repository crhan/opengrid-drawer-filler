import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from split_calc import calculate_print_cost, calculate_filament_and_time, get_grid_dimensions


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
