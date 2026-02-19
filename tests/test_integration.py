"""集成测试"""

import pytest
from conftest import (
    get_grid_dimensions,
    find_best_scheme,
    validate_tile,
    calculate_single,
)


class TestIntegration:
    """集成测试"""

    def test_standard_drawer_400x400(self):
        """标准 400x400 抽屉"""
        x, y = get_grid_dimensions(400, 400)
        assert x == 14
        assert y == 14

        scheme = find_best_scheme(x, y)
        assert scheme is not None
        assert scheme['unique_sizes'] >= 1
        assert scheme['tile_count'] > 0

        # 验证瓦片总数等于格子总数
        total_cells = sum(w * h for w, h in scheme['tiles'])
        assert total_cells == x * y

    def test_ikea_alex_drawer(self):
        """IKEA Alex 抽屉 360x500"""
        x, y = get_grid_dimensions(360, 500)
        assert x == 12
        assert y == 17

        scheme = find_best_scheme(x, y)
        assert scheme is not None

        total_cells = sum(w * h for w, h in scheme['tiles'])
        assert total_cells == x * y

    def test_small_drawer(self):
        """小抽屉 270x170 (Klean件盒)"""
        x, y = get_grid_dimensions(270, 170)
        assert x == 9
        assert y == 6

        scheme = find_best_scheme(x, y)
        assert scheme is not None

    def test_large_drawer(self):
        """大抽屉 500x500"""
        x, y = get_grid_dimensions(500, 500)
        assert x == 17
        assert y == 17

        scheme = find_best_scheme(x, y)
        assert scheme is not None

    def test_ikea_alex_drawer_360(self):
        """测试 IKEA Alex 360 深抽屉"""
        result = calculate_single(360, 360)
        assert result is not None
        assert result['grid'][0] > 0
        assert result['grid'][1] > 0

    def test_standard_kitchen_drawer(self):
        """测试标准厨房抽屉"""
        result = calculate_single(450, 500)
        assert result is not None

    def test_small_cabinet_drawer(self):
        """测试小柜子抽屉"""
        result = calculate_single(200, 300)
        assert result is not None

    def test_deep_drawer(self):
        """测试深抽屉"""
        result = calculate_single(300, 500)
        assert result is not None

    def test_wide_shallow_drawer(self):
        """测试宽浅抽屉"""
        result = calculate_single(600, 200)
        assert result is not None

    def test_bamboo_cutboard_drawer(self):
        """测试竹制砧板抽屉 (常见尺寸)"""
        result = calculate_single(400, 450)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
