"""工具函数测试"""

import pytest
from conftest import (
    get_max_stacks,
    get_grid_dimensions,
    MIN_TILE,
)


class TestGetMaxStacks:
    """get_max_stacks 函数测试"""

    def test_basic(self):
        # 325 // 7.2 = 45
        assert get_max_stacks() == 45


class TestGetGridDimensions:
    """get_grid_dimensions 函数测试"""

    def test_standard_size(self):
        # 400mm / 28 = 14.28 -> 14
        x, y = get_grid_dimensions(400, 400)
        assert x == 14
        assert y == 14

    def test_exact_division(self):
        # 280mm / 28 = 10 exact
        x, y = get_grid_dimensions(280, 280)
        assert x == 10
        assert y == 10

    def test_remainder(self):
        # 485mm / 28 = 17.32 -> 17
        x, y = get_grid_dimensions(485, 425)
        assert x == 17
        assert y == 15

    def test_small_size(self):
        # 小于 TILE_SIZE 的尺寸
        x, y = get_grid_dimensions(50, 50)
        assert x == 1
        assert y == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
