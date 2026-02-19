"""均衡度计算测试"""

import pytest
from conftest import (
    calc_balance,
    calc_scheme_balance,
)


class TestCalcBalance:
    """calc_balance 函数测试"""

    def test_perfect_balance(self):
        # 完全均衡
        assert calc_balance([5, 5, 5]) == 1.0

    def test_slight_imbalance(self):
        # 轻微不均衡
        result = calc_balance([5, 6])
        assert result == 6 / 5  # 1.2

    def test_severe_imbalance(self):
        # 严重不均衡
        result = calc_balance([2, 10])
        assert result == 10 / 2  # 5.0

    def test_empty(self):
        assert calc_balance([]) == 1

    def test_zero_in_splits(self):
        assert calc_balance([0, 5]) == 1


class TestCalcSchemeBalance:
    """calc_scheme_balance 函数测试"""

    def test_both_balanced(self):
        assert calc_scheme_balance([5, 5], [3, 3]) == 1.0

    def test_x_imbalanced(self):
        # x 不均衡，y 均衡
        result = calc_scheme_balance([2, 8], [5, 5])
        assert result == 8 / 2  # 4.0

    def test_y_imbalanced(self):
        # x 均衡，y 不均衡
        result = calc_scheme_balance([5, 5], [2, 8])
        assert result == 8 / 2  # 4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
