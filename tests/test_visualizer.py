import pytest
from scripts.visualizer import Visualizer, get_tile_color


def test_get_tile_color():
    """测试颜色映射函数"""
    # 单一尺寸应该返回固定颜色
    color = get_tile_color(100, [100])
    assert color is not None

    # 最小尺寸应该是蓝色
    color_min = get_tile_color(50, [50, 100])
    assert "240" in color_min  # 蓝色 hue

    # 最大尺寸应该是红色
    color_max = get_tile_color(100, [50, 100])
    assert "0" in color_max or "0," in color_max  # 红色 hue


def test_visualizer_init():
    """测试可视化器初始化"""
    v = Visualizer()
    assert v is not None
