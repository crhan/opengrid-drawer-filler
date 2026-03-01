"""分割算法测试"""

import pytest
from conftest import (
    split_with_limit,
    calc_scheme_balance,
    MIN_TILE,
    MAX_X,
)


class TestSplitWithLimit:
    """split_with_limit 函数测试"""

    def test_single_part(self):
        # n=5, parts=1, max=10 -> [5]
        result = split_with_limit(5, 1, 10)
        assert result == [[5]]

    def test_single_part_exceeds_max(self):
        # n=15, parts=1, max=10 -> []
        result = split_with_limit(15, 1, 10)
        assert result == []

    def test_two_parts(self):
        # n=10, parts=2, max=10 -> [[2,8], [3,7], [4,6], [5,5], [6,4], [7,3], [8,2]]
        result = split_with_limit(10, 2, 10)
        # 验证结果存在且每个部分都有效
        assert len(result) > 0
        for split in result:
            assert len(split) == 2
            assert sum(split) == 10
            assert all(MIN_TILE <= x <= 10 for x in split)

    def test_three_parts(self):
        result = split_with_limit(15, 3, 10)
        assert len(result) > 0
        for split in result:
            assert len(split) == 3
            assert sum(split) == 15

    def test_impossible_split(self):
        # n=3, parts=3, min=2 -> impossible (需要 3*2=6)
        result = split_with_limit(3, 3, 10)
        assert result == []

    def test_exceeds_max(self):
        # n=30, parts=2, max=10 -> impossible
        result = split_with_limit(30, 2, 10)
        assert result == []

    def test_max_results_early_termination(self):
        """测试 max_results 提前终止"""
        # 10 分成 2 部分，结果会有 7 个，限制 max_results=1
        result = split_with_limit(10, 2, 10, max_results=1)
        # 应该只返回最多 1 个结果
        assert len(result) == 1


class TestCalcSchemeBalance:
    """calc_scheme_balance 函数测试"""

    def test_empty_x_splits(self):
        """x_splits 为空时返回 1.0"""
        result = calc_scheme_balance([], [5, 5])
        assert result == 1.0

    def test_empty_y_splits(self):
        """y_splits 为空时返回 1.0"""
        result = calc_scheme_balance([5, 5], [])
        assert result == 1.0

    def test_both_empty(self):
        """都为空时返回 1.0"""
        result = calc_scheme_balance([], [])
        assert result == 1.0

    def test_normal_case(self):
        """正常情况"""
        # x: [5, 10] -> balance = 10/5 = 2.0
        # y: [5, 5] -> balance = 5/5 = 1.0
        result = calc_scheme_balance([5, 10], [5, 5])
        assert result == 2.0  # max(2.0, 1.0) = 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
