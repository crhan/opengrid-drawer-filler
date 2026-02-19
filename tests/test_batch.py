"""批量模式测试"""

import pytest
from conftest import (
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    optimize_batch_global,
)


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
        from conftest import validate_tile
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


class TestCalculateTotalPrints:
    """calculate_total_prints 函数测试"""

    def test_calculate_total_prints_basic(self):
        """测试 calculate_total_prints 基本功能"""
        # 模拟两个抽屉，各一个瓦片
        batch_results = [
            {'width': 400, 'depth': 400, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
        ]
        schemes = [batch_results[0]['scheme']]

        total, details = calculate_total_prints(batch_results, schemes)
        assert total >= 1
        assert 'prints' in details or len(details) > 0

    def test_calculate_total_prints_multiple(self):
        """测试多个抽屉的打印次数计算"""
        # 两个抽屉共享瓦片尺寸
        batch_results = [
            {'width': 400, 'depth': 400, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
            {'width': 280, 'depth': 280, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
        ]
        schemes = [r['scheme'] for r in batch_results]

        total, details = calculate_total_prints(batch_results, schemes)
        # 共享瓦片应该只打印一次
        assert (10, 10) in details
        assert details[(10, 10)]['print_count'] == 1


class TestOptimizeBatchGlobal:
    """optimize_batch_global 函数测试"""

    def test_basic_functionality(self):
        """测试 optimize_batch_global 基本功能"""
        results = [
            calculate_single(265, 365, copies=1),
            calculate_single(325, 365, copies=1),
        ]
        optimized = optimize_batch_global(results)
        assert optimized is not None
        assert 'schemes' in optimized
        assert 'total_prints' in optimized

    def test_print_count_reduced_or_equal(self):
        """测试优化后的打印次数应该 <= 优化前"""
        results = [
            calculate_single(265, 365, copies=2),
            calculate_single(325, 365, copies=2),
            calculate_single(315, 365, copies=2),
        ]

        # 计算优化前的打印次数
        _, before_details = calculate_total_prints(
            results,
            [r['scheme'] for r in results]
        )
        before_total = sum(d['print_count'] for d in before_details.values())

        # 优化后
        optimized = optimize_batch_global(results)
        after_total = optimized['total_prints']

        assert after_total <= before_total

    def test_same_as_original_when_already_optimal(self):
        """测试如果独立最优就是全局最优，应该返回相同方案"""
        results = [calculate_single(400, 400, copies=1)]

        optimized = optimize_batch_global(results)
        assert optimized['total_prints'] == 1

    def test_empty_batch(self):
        """测试空批次"""
        result = optimize_batch_global([])
        assert result is None

    def test_single_drawer(self):
        """测试单个抽屉"""
        results = [calculate_single(400, 400, copies=1)]
        optimized = optimize_batch_global(results)
        assert optimized['total_prints'] == 1

    def test_performance_small_batch(self):
        """测试小批次性能"""
        import time
        results = [
            calculate_single(265, 365, copies=1),
            calculate_single(325, 365, copies=1),
            calculate_single(315, 365, copies=1),
        ]
        start = time.time()
        optimize_batch_global(results)
        elapsed = time.time() - start
        assert elapsed < 1.0  # 应该在1秒内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
