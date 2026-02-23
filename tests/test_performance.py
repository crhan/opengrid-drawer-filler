"""性能测试"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from opengrid.core import find_best_scheme, get_grid_dimensions
from opengrid.cli.commands.split import calculate_single


class TestPerformance:
    """性能测试"""

    def test_2800x2800_no_inventory(self):
        """测试 2800x2800 不带库存的性能"""
        start = time.time()
        result = calculate_single(2800, 2800)
        elapsed = time.time() - start

        assert result is not None, "应该返回有效结果"
        assert elapsed < 5.0, f"应该在 5s 内完成，实际耗时 {elapsed:.2f}s"

        scheme = result['scheme']
        print(f"\n  2800x2800 不带库存: {elapsed:.2f}s, 瓦片数: {scheme['tile_count']}, 独特尺寸: {scheme['unique_sizes']}")

    def test_2800x2800_with_inventory(self):
        """测试 2800x2800 带库存的性能"""
        x, y = get_grid_dimensions(2800, 2800)
        inventory = {"10x10": 100, "8x8": 100}

        start = time.time()
        scheme = find_best_scheme(x, y, inventory=inventory)
        elapsed = time.time() - start

        assert scheme is not None, "应该返回有效结果"
        assert elapsed < 5.0, f"应该在 5s 内完成，实际耗时 {elapsed:.2f}s"
        print(f"\n  2800x2800 带库存: {elapsed:.2f}s, 瓦片数: {scheme['tile_count']}, 独特尺寸: {scheme['unique_sizes']}, 成本: {scheme.get('cost', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
