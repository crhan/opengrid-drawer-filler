"""瓦片验证测试"""

import pytest
from conftest import (
    validate_tile,
    MIN_TILE,
)


class TestValidateTile:
    """validate_tile 函数测试"""

    def test_valid_min_tile(self):
        # 最小有效瓦片 2x2
        assert validate_tile(2, 2) is True

    def test_valid_max_tile(self):
        # 最大有效瓦片 10x11
        assert validate_tile(10, 11) is True

    def test_valid_typical(self):
        # 典型瓦片
        assert validate_tile(7, 5) is True
        assert validate_tile(10, 5) is True

    def test_invalid_too_small_x(self):
        assert validate_tile(1, 5) is False

    def test_invalid_too_small_y(self):
        assert validate_tile(5, 1) is False

    def test_invalid_too_large_x(self):
        assert validate_tile(11, 5) is False

    def test_invalid_too_large_y(self):
        assert validate_tile(5, 12) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
