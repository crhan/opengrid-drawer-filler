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
        # Full 裸厚 6.8 + 层隙 0.4：(325 + 0.4) / (6.8 + 0.4) = 45.2 → 45
        from opengrid.core.split_result import PrinterConfig
        printer = PrinterConfig(max_z=325, bed_x=300, bed_y=320, tile_thickness=6.8,
                                max_cells_x=10, max_cells_y=11)
        assert get_max_stacks(printer) == 45

    def test_height_never_exceeds_max_z(self):
        # 回归：旧公式 max_z // thickness = 47 层，实际高度 47×6.8 + 46×0.4 = 338mm > 325
        from opengrid.core.grid import max_layers_per_stack
        from opengrid.core.constants import STACK_GAP_MM
        n = max_layers_per_stack(325, 6.8)
        assert n * 6.8 + (n - 1) * STACK_GAP_MM <= 325
        assert (n + 1) * 6.8 + n * STACK_GAP_MM > 325


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
