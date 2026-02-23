"""批量输入解析测试"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from opengrid.cli.utils import parse_batch_input


class TestParseBatchInput:
    """parse_batch_input 函数测试"""

    def test_parse_wxd_copies_format(self):
        """测试 '宽x深:份数' 格式"""
        result = parse_batch_input("265x365:2")
        assert len(result) == 1
        assert result[0] == (265, 365, 2)

    def test_parse_wxd_copies_no_colon(self):
        """测试 '宽x深份数' 格式 (无冒号)"""
        result = parse_batch_input("265x365x2")
        assert len(result) == 1
        assert result[0] == (265, 365, 2)

    def test_parse_multiple_items(self):
        """测试多个尺寸解析"""
        result = parse_batch_input("265x365:2 325x365:2 315x365:2")
        assert len(result) == 3
        assert result[0] == (265, 365, 2)
        assert result[1] == (325, 365, 2)
        assert result[2] == (315, 365, 2)

    def test_parse_default_copies(self):
        """测试默认份数为1"""
        result = parse_batch_input("265x365")
        assert len(result) == 1
        assert result[0] == (265, 365, 1)

    def test_parse_space_separated(self):
        """测试空格分隔格式 '宽 深 份数'"""
        result = parse_batch_input("265 365 2")
        assert len(result) == 1
        assert result[0] == (265, 365, 2)

    def test_parse_empty_input(self):
        """测试空输入"""
        result = parse_batch_input("")
        assert result == []

    def test_parse_single_number(self):
        """测试单个数字 (无有效解析)"""
        result = parse_batch_input("265")
        assert result == []

    def test_parse_invalid_format(self):
        """测试无效格式"""
        result = parse_batch_input("abcxdef")
        assert result == []

    def test_parse_mixed_valid_invalid(self):
        """测试混合有效和无效输入"""
        result = parse_batch_input("265x365:2 invalid 325x365")
        assert len(result) == 2
        assert result[0] == (265, 365, 2)
        assert result[1] == (325, 365, 1)

    def test_parse_unicode_multiply(self):
        """测试 Unicode 乘号 (×)"""
        result = parse_batch_input("265×365:2")
        assert len(result) == 1
        assert result[0] == (265, 365, 2)
