"""分割算法测试"""

import pytest
from conftest import (
    split_with_limit,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
