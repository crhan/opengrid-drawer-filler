"""方案查找测试"""

import pytest
from conftest import (
    find_best_scheme,
    find_all_schemes,
    validate_tile,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
