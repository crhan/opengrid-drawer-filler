import pytest
from opengrid.visualizer import Visualizer, get_tile_color

def test_generate_assembly_image():
    """测试拼接图生成"""
    v = Visualizer()

    # 模拟方案数据
    scheme_data = {
        "x_splits": [9, 8],
        "y_splits": [15],
        "tiles": [
            {"width": 9, "height": 15, "count": 1},
            {"width": 8, "height": 15, "count": 1}
        ]
    }

    # 生成图片
    image = v.generate_assembly_image(scheme_data)

    # 验证图片属性
    assert image is not None
    assert image.width > 0
    assert image.height > 0

def test_adaptive_size():
    """测试自适应尺寸"""
    v = Visualizer()

    # 大尺寸抽屉
    large_scheme = {"x_splits": [10], "y_splits": [11], "tiles": [{"width": 10, "height": 11}]}
    large_img = v.generate_assembly_image(large_scheme)

    # 小尺寸抽屉
    small_scheme = {"x_splits": [3], "y_splits": [3], "tiles": [{"width": 3, "height": 3}]}
    small_img = v.generate_assembly_image(small_scheme)

    # 大图应该比小图大
    assert large_img.width > small_img.width
    assert large_img.height > small_img.height
