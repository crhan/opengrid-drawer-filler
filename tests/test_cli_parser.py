import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.split_calc import parse_dimensions, parse_preset

class TestParseDimensions:
    """测试尺寸参数解析"""

    def test_single_dimension(self):
        """测试单个尺寸解析"""
        result = parse_dimensions(['485x425'])
        assert result == [(485, 425, 1)]

    def test_dimension_with_copies(self):
        """测试带份数的尺寸"""
        result = parse_dimensions(['265x365:2'])
        assert result == [(265, 365, 2)]

    def test_multiple_dimensions(self):
        """测试多个尺寸"""
        result = parse_dimensions(['485x425', '265x365:2', '325x365'])
        assert result == [(485, 425, 1), (265, 365, 2), (325, 365, 1)]

    def test_empty_input(self):
        """测试空输入"""
        result = parse_dimensions([])
        assert result == []

    def test_invalid_format_ignored(self):
        """测试无效格式被忽略"""
        result = parse_dimensions(['invalid', '485x425'])
        assert result == [(485, 425, 1)]

    def test_preset_klean(self):
        """测试预设解析"""
        result = parse_preset('klean')
        assert result == [(270, 170, 1)]

    def test_preset_with_copies(self):
        """测试预设带份数"""
        result = parse_preset('klean', copies=3)
        assert result == [(270, 170, 3)]
