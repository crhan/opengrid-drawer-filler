"""测试配置和库存的项目级分离"""

import os
import sys
import json
import pytest
import tempfile
from pathlib import Path

# 确保可以导入 opengrid 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opengrid'))


class TestConfigScope:
    """测试配置 scope 功能"""

    def test_config_scope_detection(self):
        """测试 scope 检测功能（仅支持项目级）"""
        from opengrid.config import get_config_path

        # 由于 config.py 已简化，不再支持全局配置
        # 只测试 get_config_path 在无配置文件时抛出异常
        with pytest.raises(FileNotFoundError):
            get_config_path()


class TestInventoryPath:
    """测试库存路径功能"""

    def test_custom_inventory_path(self):
        """测试自定义库存路径"""
        from opengrid.inventory import get_inventory_path

        # 模拟项目配置中指定了自定义路径
        config = {"inventory_path": "/tmp/test_inventory.json"}
        path = get_inventory_path(config)
        assert str(path) == "/tmp/test_inventory.json"

    def test_relative_inventory_path(self):
        """测试相对库存路径"""
        from opengrid.inventory import get_inventory_path

        # 模拟项目配置中指定了相对路径
        config = {"inventory_path": "inventory.json"}
        path = get_inventory_path(config)
        # 相对路径应该相对于当前工作目录
        assert path.name == "inventory.json"


class TestInventoryOperationsWithConfig:
    """测试库存操作使用正确的配置驱动路径"""

    def test_add_inventory_with_config(self, tmp_path):
        """测试库存添加"""
        from opengrid.inventory import add_inventory, load_inventory

        # 创建临时库存文件
        inv_file = tmp_path / "test_inventory.json"
        inv_file.write_text(json.dumps({"inventory": {}, "log": []}))

        # 使用配置
        config = {"inventory_path": str(inv_file)}

        # 添加库存
        add_inventory({"7x5": 5}, reason="test", config=config)

        # 验证库存已添加
        inv = load_inventory(config)
        assert inv.get("7x5") == 5

    def test_deduct_inventory_with_config(self, tmp_path):
        """测试库存扣减使用配置驱动路径"""
        from opengrid.inventory import add_inventory, deduct_inventory, load_inventory

        # 创建库存文件
        inv_file = tmp_path / "deduct_test.json"
        inv_file.write_text(json.dumps({"inventory": {"7x5": 10}, "log": []}))

        config = {"inventory_path": str(inv_file)}

        # 扣减库存
        deduct_inventory({"7x5": 3}, reason="test deduct", config=config)

        # 验证扣减成功
        inv = load_inventory(config)
        assert inv.get("7x5") == 7

    def test_undo_with_config(self, tmp_path):
        """测试撤销操作使用配置驱动路径"""
        from opengrid.inventory import add_inventory, undo_last, load_inventory

        # 创建库存文件
        inv_file = tmp_path / "undo_test.json"
        inv_file.write_text(json.dumps({"inventory": {}, "log": []}))

        config = {"inventory_path": str(inv_file)}

        # 添加库存
        add_inventory({"5x5": 5}, reason="test undo", config=config)

        # 撤销
        undo_last(config=config)

        # 验证已撤销
        inv = load_inventory(config)
        assert inv.get("5x5") is None or inv.get("5x5") == 0

    def test_separate_inventory_files(self, tmp_path):
        """测试两个库存文件完全独立"""
        from opengrid.inventory import add_inventory, load_inventory

        # 创建两个独立的库存文件
        inv1 = tmp_path / "inv1.json"
        inv2 = tmp_path / "inv2.json"

        inv1.write_text(json.dumps({"inventory": {}, "log": []}))
        inv2.write_text(json.dumps({"inventory": {}, "log": []}))

        # 配置1添加库存
        config1 = {"inventory_path": str(inv1)}
        add_inventory({"7x5": 10}, reason="test1", config=config1)

        # 配置2添加库存
        config2 = {"inventory_path": str(inv2)}
        add_inventory({"10x5": 5}, reason="test2", config=config2)

        # 验证两者完全独立
        inv1_data = load_inventory(config1)
        inv2_data = load_inventory(config2)

        assert inv1_data.get("7x5") == 10
        assert inv1_data.get("10x5") is None

        assert inv2_data.get("10x5") == 5
        assert inv2_data.get("7x5") is None
