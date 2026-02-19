"""统计函数测试"""

import pytest
from conftest import (
    calculate_filament_and_time,
    format_time,
)


class TestCalculateFilamentAndTime:
    """calculate_filament_and_time 函数测试"""

    def test_single_stack(self):
        # 10x5 = 50 格，1 stack
        main, support, time_min = calculate_filament_and_time(50, 1)
        assert main == pytest.approx(50 * 1.13, rel=0.01)
        assert support == pytest.approx(50 * 0.06, rel=0.01)
        assert time_min == pytest.approx(50 * 3.1, rel=0.01)

    def test_multiple_stacks(self):
        # 10x5 = 50 格，3 stacks
        main, support, time_min = calculate_filament_and_time(50, 3)
        assert main == pytest.approx(50 * 1.13 * 3, rel=0.01)
        assert support == pytest.approx(50 * 0.06 * 3, rel=0.01)
        assert time_min == pytest.approx(50 * 3.1 * 3, rel=0.01)


class TestFormatTime:
    """format_time 函数测试"""

    def test_minutes_only(self):
        assert format_time(30) == "30m"

    def test_exact_hour(self):
        assert format_time(60) == "1h0m"

    def test_hours_and_minutes(self):
        assert format_time(90) == "1h30m"

    def test_large_hours(self):
        assert format_time(150) == "2h30m"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
