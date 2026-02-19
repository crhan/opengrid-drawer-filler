"""openGrid 分割计算器测试"""

import pytest
import sys
import os

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from split_calc import (
    get_max_stacks,
    get_grid_dimensions,
    validate_tile,
    split_with_limit,
    calc_balance,
    calc_scheme_balance,
    find_best_scheme,
    calculate_single,
    merge_and_optimize,
    calculate_filament_and_time,
    format_time,
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


class TestCalcBalance:
    """calc_balance 函数测试"""

    def test_perfect_balance(self):
        # 完全均衡
        assert calc_balance([5, 5, 5]) == 1.0

    def test_slight_imbalance(self):
        # 轻微不均衡
        result = calc_balance([5, 6])
        assert result == 6 / 5  # 1.2

    def test_severe_imbalance(self):
        # 严重不均衡
        result = calc_balance([2, 10])
        assert result == 10 / 2  # 5.0

    def test_empty(self):
        assert calc_balance([]) == 1

    def test_zero_in_splits(self):
        assert calc_balance([0, 5]) == 1


class TestCalcSchemeBalance:
    """calc_scheme_balance 函数测试"""

    def test_both_balanced(self):
        assert calc_scheme_balance([5, 5], [3, 3]) == 1.0

    def test_x_imbalanced(self):
        # x 不均衡，y 均衡
        result = calc_scheme_balance([2, 8], [5, 5])
        assert result == 8 / 2  # 4.0

    def test_y_imbalanced(self):
        # x 均衡，y 不均衡
        result = calc_scheme_balance([5, 5], [2, 8])
        assert result == 8 / 2  # 4.0


class TestFindBestScheme:
    """find_best_scheme 函数测试"""

    def test_no_split_needed(self):
        # 小于最大瓦片尺寸，不需要分割
        scheme = find_best_scheme(5, 5)
        assert scheme is not None
        assert scheme['x_parts'] == 1
        assert scheme['y_parts'] == 1
        assert scheme['x_splits'] == [5]
        assert scheme['y_splits'] == [5]
        assert scheme['unique_sizes'] == 1
        assert scheme['tile_count'] == 1

    def test_single_size_solution(self):
        # 10x10 本身是有效瓦片(10x10 <= 10x11)，所以不需要分割
        # 验证算法正确处理了这种情况
        scheme = find_best_scheme(10, 10)
        assert scheme is not None
        # 10x10 在限制范围内，所以不分割
        assert scheme['unique_sizes'] == 1
        assert scheme['tile_count'] == 1

    def test_split_needed_solution(self):
        # 20x20 需要分割成多块
        # 20x20 可以分成 4 个 10x10 (单一尺寸)
        scheme = find_best_scheme(20, 20)
        assert scheme is not None
        assert scheme['unique_sizes'] == 1
        assert scheme['tile_count'] == 4
        assert scheme['x_splits'] == [10, 10]
        assert scheme['y_splits'] == [10, 10]

    def test_two_size_solution(self):
        # 17x15 应该找到 2 种尺寸的解
        scheme = find_best_scheme(17, 15)
        assert scheme is not None
        assert scheme['unique_sizes'] == 2
        # 算法选择了 [8, 9] 而非 [7, 10]，因为更均衡

    def test_xy_rotation_symmetry(self):
        """测试 XY 旋转对称性: 11x13 和 13x11 应该得到相同结果"""
        scheme_11x13 = find_best_scheme(11, 13)
        scheme_13x11 = find_best_scheme(13, 11)

        assert scheme_11x13 is not None
        assert scheme_13x11 is not None

        # 独特尺寸数量应该相同
        assert scheme_11x13['unique_sizes'] == scheme_13x11['unique_sizes']

        # 瓦片数量应该相同
        assert scheme_11x13['tile_count'] == scheme_13x11['tile_count']

        # 旋转后的分割方案应该等价
        # 11x13 的 x_splits 应该是 13x11 的 y_splits
        assert scheme_11x13['x_splits'] == scheme_13x11['y_splits']
        assert scheme_11x13['y_splits'] == scheme_13x11['x_splits']

    def test_rotation_symmetry_17x15(self):
        """测试 17x15 和 15x17 的旋转对称性"""
        scheme_17x15 = find_best_scheme(17, 15)
        scheme_15x17 = find_best_scheme(15, 17)

        assert scheme_17x15 is not None
        assert scheme_15x17 is not None

        # 独特尺寸数量应该相同
        assert scheme_17x15['unique_sizes'] == scheme_15x17['unique_sizes']

        # 瓦片数量应该相同
        assert scheme_17x15['tile_count'] == scheme_15x17['tile_count']

        # 旋转后的分割方案应该等价
        assert scheme_17x15['x_splits'] == scheme_15x17['y_splits']
        assert scheme_17x15['y_splits'] == scheme_15x17['x_splits']

    def test_returns_valid_tiles(self):
        # 验证返回的瓦片都是合法的
        scheme = find_best_scheme(17, 15)
        for w, h in scheme['tiles']:
            assert validate_tile(w, h)

    def test_tile_count_consistency(self):
        # 瓦片数量 = x_parts * y_parts
        scheme = find_best_scheme(17, 15)
        expected = scheme['x_parts'] * scheme['y_parts']
        assert scheme['tile_count'] == expected


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


class TestBatchMode:
    """批量计算相关函数测试"""

    def test_calculate_single_basic(self):
        """测试 calculate_single 基本功能"""
        result = calculate_single(400, 400, copies=1)
        assert result is not None
        assert result['width'] == 400
        assert result['depth'] == 400
        assert result['copies'] == 1
        assert 'scheme' in result
        assert 'grid' in result

    def test_calculate_single_with_copies(self):
        """测试 calculate_single 带份数"""
        result = calculate_single(400, 400, copies=3)
        assert result is not None
        assert result['copies'] == 3

    def test_calculate_single_small_drawer(self):
        """测试小尺寸抽屉"""
        result = calculate_single(100, 100)
        # 100mm = 3 格，应该返回有效结果
        assert result is not None

    def test_merge_and_optimize_single(self):
        """测试单个尺寸的合并优化"""
        result = calculate_single(400, 400, copies=1)
        merged = merge_and_optimize([result])

        # 应该返回瓦片统计
        assert len(merged) > 0

        # 验证合并后的数据结构
        for (w, h), info in merged.items():
            assert 'total' in info
            assert 'by_drawer' in info
            assert info['total'] > 0

    def test_merge_and_optimize_multiple(self):
        """测试多个尺寸的合并优化"""
        results = [
            calculate_single(265, 365, copies=2),
            calculate_single(325, 365, copies=2),
            calculate_single(315, 365, copies=2),
        ]

        merged = merge_and_optimize(results)

        # 应该合并共同尺寸的瓦片
        assert len(merged) > 0

        # 验证总数正确
        for (w, h), info in merged.items():
            expected_total = sum(item['total'] for item in info['by_drawer'])
            assert info['total'] == expected_total

    def test_merge_and_optimize_same_size(self):
        """测试相同尺寸不同份数的合并"""
        result1 = calculate_single(400, 400, copies=1)
        result2 = calculate_single(400, 400, copies=2)

        merged = merge_and_optimize([result1, result2])

        # 相同瓦片尺寸应该合并
        assert len(merged) > 0

    def test_merge_and_optimize_empty(self):
        """测试空输入"""
        merged = merge_and_optimize([])
        assert merged == {}

    def test_merge_and_optimize_with_none(self):
        """测试包含 None 的输入"""
        result = calculate_single(400, 400, copies=1)
        merged = merge_and_optimize([result, None])
        assert len(merged) > 0

    def test_tile_sharing_optimization(self):
        """测试瓦片共享优化：多个抽屉使用相同瓦片尺寸时应合并"""
        # 325x365 和 315x365 都会产生 6x7 的瓦片
        result1 = calculate_single(325, 365, copies=1)
        result2 = calculate_single(315, 365, copies=1)

        merged = merge_and_optimize([result1, result2])

        # 找到 6x7 或类似的共享瓦片
        shared_tiles = [(k, v) for k, v in merged.items() if len(v['by_drawer']) > 1]
        # 如果有共享瓦片，验证它们被正确合并
        for (w, h), info in merged.items():
            # 验证 total = 所有 by_drawer 的 total 之和
            calculated_total = sum(item['total'] for item in info['by_drawer'])
            assert info['total'] == calculated_total

    def test_print_count_with_multiple_copies(self):
        """测试多份数时的打印次数计算"""
        # 假设一个瓦片需要 3 stack，1 份 = 3 stacks
        # 2 份 = 6 stacks
        result1 = calculate_single(400, 400, copies=2)
        merged = merge_and_optimize([result1])

        # 验证份数正确应用
        for (w, h), info in merged.items():
            # 每份的瓦片数 * 份数 = total
            tiles_per_copy = sum(item['tiles_per_copy'] for item in info['by_drawer'])
            copies = info['by_drawer'][0]['copies']
            assert info['total'] == tiles_per_copy * copies

    def test_merge_result_tile_dimensions(self):
        """测试合并结果的瓦片尺寸正确性"""
        results = [
            calculate_single(265, 365, copies=1),
            calculate_single(325, 365, copies=1),
            calculate_single(315, 365, copies=1),
        ]

        merged = merge_and_optimize(results)

        # 验证所有瓦片尺寸都是有效的
        for (w, h), info in merged.items():
            assert validate_tile(w, h), f"Invalid tile size: {w}x{h}"

    def test_all_drawers_included(self):
        """测试所有抽屉都被包含在合并结果中"""
        results = [
            calculate_single(265, 365, copies=2),
            calculate_single(325, 365, copies=3),
            calculate_single(315, 365, copies=1),
        ]

        merged = merge_and_optimize(results)

        # 统计所有来源抽屉
        all_drawers = set()
        for (w, h), info in merged.items():
            for drawer_info in info['by_drawer']:
                all_drawers.add(drawer_info['size'])

        # 应该包含所有 3 个抽屉尺寸
        assert len(all_drawers) == 3
        assert "265×365" in all_drawers
        assert "325×365" in all_drawers
        assert "315×365" in all_drawers

    def test_no_solution_for_too_small(self):
        """测试太小尺寸无法生成方案"""
        # 50mm = 1 格，小于最小瓦片 2x2
        result = calculate_single(50, 50)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
