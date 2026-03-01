"""边界条件测试"""

import pytest

from opengrid.core import (
    get_grid_dimensions,
    TILE_SIZE,
    MIN_TILE,
)
from conftest import (
    MAX_X,
    MAX_Y,
    validate_tile,
    find_best_scheme,
    TEST_GRID_CONFIG,
)

from opengrid.cli.commands.split import calculate_single


class TestBoundaryConditions:
    """边界条件测试"""

    def test_min_tile_size(self):
        """测试最小瓦片尺寸 (MIN_TILE = 2)"""
        # 最小 2 格 = 56mm
        x, y = get_grid_dimensions(56, 56)
        assert x >= MIN_TILE
        assert y >= MIN_TILE
        assert validate_tile(x, y)

    def test_min_drawer_size(self):
        """测试最小抽屉尺寸"""
        # 小于 MIN_TILE * TILE_SIZE 应该返回 None
        result = calculate_single(50, 50)
        assert result is None

    def test_max_tile_dimensions(self):
        """测试最大瓦片尺寸 (MAX_X=10, MAX_Y=11)"""
        # 10x11 是最大有效瓦片
        assert validate_tile(10, 11)
        # 10x10 也在范围内
        assert validate_tile(10, 10)

    def test_exceeds_max_tile(self):
        """测试超过最大尺寸"""
        # 11x11 应该无效
        assert not validate_tile(11, 11)
        assert not validate_tile(10, 12)

    def test_max_drawer_dimensions(self):
        """测试最大抽屉尺寸"""
        # MAX_X * TILE_SIZE = 280mm, MAX_Y * TILE_SIZE = 308mm
        result = calculate_single(280, 308)
        assert result is not None
        assert 'scheme' in result

    def test_extreme_aspect_ratio_long(self):
        """测试极端长宽比 (窄长)"""
        result = calculate_single(100, 300)
        assert result is not None
        assert 'scheme' in result

    def test_extreme_aspect_ratio_wide(self):
        """测试极端长宽比 (宽扁)"""
        result = calculate_single(300, 100)
        assert result is not None
        assert 'scheme' in result

    def test_grid_remainder_handling(self):
        """测试网格余数处理"""
        # 100mm = 3 格余 16mm
        x, y = get_grid_dimensions(100, 100)
        assert x == 3
        assert y == 3

    def test_grid_exact_division(self):
        """测试整除情况"""
        # 56mm = 2 格整除
        x, y = get_grid_dimensions(56, 56)
        assert x == 2
        assert y == 2


class TestErrorHandling:
    """错误处理测试"""

    def test_zero_dimension(self):
        """测试零尺寸"""
        result = calculate_single(0, 100)
        assert result is None

    def test_negative_dimension(self):
        """测试负尺寸"""
        result = calculate_single(-100, 100)
        assert result is None

    def test_very_small_dimension(self):
        """测试超小尺寸"""
        # 小于最小有效尺寸 (MIN_TILE * TILE_SIZE = 56mm)
        result = calculate_single(10, 10)
        assert result is None

    def test_none_input(self):
        """测试 None 输入"""
        with pytest.raises(Exception):
            get_grid_dimensions(None, 100)

    def test_string_input(self):
        """测试字符串输入"""
        with pytest.raises(Exception):
            get_grid_dimensions("100", 100)

    def test_very_large_dimension(self):
        """测试超大尺寸"""
        # 测试超过 MAX_X * TILE_SIZE 很多的情况
        result = calculate_single(1000, 1000)
        assert result is not None


class TestEdgeCases:
    """边缘案例测试"""

    def test_square_drawer(self):
        """测试正方形抽屉"""
        result = calculate_single(280, 280)
        assert result is not None
        scheme = result['scheme']
        assert scheme['x_parts'] == scheme['y_parts']

    def test_near_square_drawer(self):
        """测试接近正方形"""
        result = calculate_single(280, 300)
        assert result is not None

    def test_single_tile_exact_fit(self):
        """测试恰好一个瓦片"""
        # 10x11 恰好是最大瓦片
        scheme = find_best_scheme(10, 11)
        assert scheme['tile_count'] == 1
        assert scheme['x_parts'] == 1
        assert scheme['y_parts'] == 1

    def test_two_by_one_split(self):
        """测试 2x1 分割"""
        scheme = find_best_scheme(20, 10)
        assert scheme is not None
        # 20x10 可以分成 2 个 10x10
        assert scheme['tile_count'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
