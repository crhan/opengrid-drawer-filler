"""常量测试"""

import pytest
from conftest import (
    TILE_SIZE,
    MAX_X,
    MAX_Y,
    MIN_TILE,
    FULL_THICKNESS,
    MAX_Z,
)


class TestConstants:
    """常量测试"""

    def test_tile_size(self):
        assert TILE_SIZE == 28

    def test_max_dimensions(self):
        assert MAX_X == 10
        assert MAX_Y == 11

    def test_min_tile(self):
        assert MIN_TILE == 2

    def test_full_thickness(self):
        assert FULL_THICKNESS == 7.2  # 6.8 + 0.4

    def test_max_z(self):
        assert MAX_Z == 325


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
