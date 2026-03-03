"""方案查找测试"""

import pytest
from conftest import (
    find_best_scheme,
    find_all_schemes,
    validate_tile,
    normalize_tiles,
    MAX_X,
    MAX_Y,
    calc_scheme_balance,
)


class TestFindBestScheme:
    """find_best_scheme 函数测试"""

    def test_no_split_needed(self):
        # 小于最大瓦片尺寸，不需要分割
        scheme = find_best_scheme(5, 5)
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

    def test_15x15_square(self):
        """测试 15x15 正方形"""
        scheme = find_best_scheme(15, 15)
        assert scheme is not None
        assert scheme['tile_count'] > 0

    def test_18x20_rectangle(self):
        """测试 18x20 长方形"""
        scheme = find_best_scheme(18, 20)
        assert scheme is not None

    def test_8x9_small(self):
        """测试 8x9 小尺寸"""
        scheme = find_best_scheme(8, 9)
        assert scheme is not None

    def test_all_tiles_valid_for_scheme(self):
        """验证所有方案返回的瓦片都有效"""
        test_sizes = [(10, 10), (15, 15), (17, 20), (20, 18), (8, 12)]
        for x, y in test_sizes:
            scheme = find_best_scheme(x, y)
            for w, h in scheme['tiles']:
                assert validate_tile(w, h)

    def test_balance_prefers_balanced_splits(self):
        """验证当多个方案的 unique_sizes 和 tile_count 相同时，选择均衡度更好的方案

        10x13 可以分割为:
        - [6, 7]: unique=2, tile_count=2, balance=1.167
        - [5, 8]: unique=2, tile_count=2, balance=1.600
        - [4, 9]: unique=2, tile_count=2, balance=2.250

        应该选择 [6, 7]，因为 balance 最低（最均衡）
        """
        scheme = find_best_scheme(10, 13)
        assert scheme is not None

        # 验证选择了均衡度最好的 [6, 7] 方案
        assert scheme['y_splits'] == [6, 7] or scheme['y_splits'] == [7, 6]
        # 验证均衡度是所有方案中最低的
        balance = scheme['balance']
        assert balance == pytest.approx(1.167, abs=0.01)

    def test_balance_prefers_perfect_balance(self):
        """验证完全均衡的方案优先于非完全均衡的方案

        10x14 可以分割为:
        - [7, 7]: unique=1 (完全均衡, balance=1.0)
        - [6, 8]: unique=2 (非均衡, balance=1.333)

        应该选择 [7, 7]，因为 unique=1 更优先
        """
        scheme = find_best_scheme(10, 14)
        assert scheme is not None

        # 验证选择了完全均衡的 [7, 7] 方案
        assert scheme['y_splits'] == [7, 7]
        assert scheme['unique_sizes'] == 1
        assert scheme['balance'] == 1.0

    def test_balance_prefers_even_3way(self):
        """验证 3 向分割时的均衡度选择

        10x23 (y=23) 可以分割为:
        - [7, 8, 8]: balance = 8/7 = 1.143
        - [6, 8, 9]: balance = 9/6 = 1.500

        应该选择 [7, 8, 8]，因为更均衡
        """
        scheme = find_best_scheme(10, 23)
        assert scheme is not None

        # 验证选择了均衡度更好的方案
        y_splits = scheme['y_splits']
        # [7,8,8] 或 [8,7,8] 或 [8,8,7] 都可以
        assert sorted(y_splits) == [7, 8, 8]
        # 验证均衡度
        balance = calc_scheme_balance(scheme['x_splits'], scheme['y_splits'])
        assert balance == pytest.approx(1.143, abs=0.01)


class TestFindAllSchemes:
    """find_all_schemes 函数测试"""

    def test_returns_list(self):
        schemes = find_all_schemes(17, 15)
        assert isinstance(schemes, list)
        assert len(schemes) > 0

    def test_all_schemes_valid(self):
        schemes = find_all_schemes(17, 15)
        for scheme in schemes:
            for w, h in scheme['tiles']:
                assert validate_tile(w, h)

    def test_no_split_needed(self):
        # 10x10 不需要分割
        schemes = find_all_schemes(10, 10)
        assert isinstance(schemes, list)
        assert len(schemes) >= 1
        # 至少包含原始方案
        assert any(s['x_parts'] == 1 and s['y_parts'] == 1 for s in schemes)


class TestNormalizeTiles:
    """normalize_tiles 函数测试"""

    def test_no_rotation_needed(self):
        """正常尺寸不需要旋转"""
        tiles = [(5, 5), (8, 10), (3, 7)]
        result = normalize_tiles(tiles)
        assert result == [(5, 5), (8, 10), (3, 7)]

    def test_rotation_needed(self):
        """宽度超过 MAX_X 但高度在范围内时需要旋转"""
        # (11, 5): 宽度 11 > MAX_X(10)，高度 5 <= MAX_Y(11)，应该旋转为 (5, 11)
        tiles = [(11, 5), (5, 5)]
        result = normalize_tiles(tiles)
        assert result == [(5, 11), (5, 5)]

    def test_rotation_needed_both_directions(self):
        """混合场景：部分需要旋转，部分不需要"""
        # Use GridConfig for 280x308 bed (max_x=10, max_y=11)
        from opengrid.core import GridConfig
        grid_config = GridConfig(max_cells_x=10, max_cells_y=11)
        tiles = [(5, 5), (11, 5), (8, 10), (12, 3)]
        result = normalize_tiles(tiles, grid_config)
        # (5,5) -> (5,5) valid, (11,5) -> (5,11) rotated valid,
        # (8,10) -> (8,10) valid, (12,3) -> (12,3) invalid both orientations
        assert result == [(5, 5), (5, 11), (8, 10), (12, 3)]

    def test_both_exceed_max(self):
        """宽度和高度都超过限制时不旋转"""
        tiles = [(12, 12)]
        result = normalize_tiles(tiles)
        # 两者都超过，不旋转
        assert result == [(12, 12)]


class TestFindAllSchemesEmpty:
    """find_all_schemes 返回空列表的边界情况"""

    def test_undersized_dimensions_return_none(self):
        """小于最小瓦片尺寸应返回 None"""
        # 1x1 低于 MIN_TILE(2)，所有分割方案都会无效
        scheme = find_best_scheme(1, 1)
        # find_best_scheme 在无方案时应返回 None
        assert scheme is None

    def test_find_all_schemes_empty_for_undersized(self):
        """小于最小尺寸 find_all_schemes 返回空列表"""
        schemes = find_all_schemes(1, 1)
        assert schemes == []

    def test_undersized_x_dimension(self):
        """x 维度小于 MIN_TILE"""
        scheme = find_best_scheme(1, 10)
        assert scheme is None
        schemes = find_all_schemes(1, 10)
        assert schemes == []

    def test_undersized_y_dimension(self):
        """y 维度小于 MIN_TILE"""
        scheme = find_best_scheme(10, 1)
        assert scheme is None
        schemes = find_all_schemes(10, 1)
        assert schemes == []


class TestFindAllSchemesInvalidSplit:
    """find_all_schemes 中跳过无效分割的边界情况"""

    def test_skips_invalid_tile_splits(self):
        """算法应跳过产生无效瓦片的分割方案"""
        # 30x30 尝试多种分割，但有些分割会产生无效瓦片
        # 测试确保最终结果只包含有效瓦片
        schemes = find_all_schemes(30, 30)
        # 至少应该有一些有效方案
        assert len(schemes) > 0
        # 验证所有方案中的瓦片都是有效的
        for scheme in schemes:
            for w, h in scheme['tiles']:
                assert validate_tile(w, h)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
