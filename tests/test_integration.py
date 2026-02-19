"""集成测试"""

import pytest
from conftest import (
    get_grid_dimensions,
    find_best_scheme,
    validate_tile,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
