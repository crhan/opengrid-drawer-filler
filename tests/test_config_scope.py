"""测试配置和库存的全局/项目级分离"""

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

    def test_get_config_path_global(self):
        """测试获取全局配置路径"""
        from opengrid.config import get_config_path, reload_config
        reload_config("global")
        path = get_config_path("global")
        assert str(path).endswith("config.yaml")

    def test_get_config_path_auto_returns_global_when_no_project_config(self):
        """测试项目配置不存在时返回全局"""
        from opengrid.config import get_config_path, reload_config
        reload_config("auto")
        path = get_config_path("auto")
        # 应该返回全局配置（因为当前目录没有 opengrid_config.yaml）
        assert str(path).endswith("config.yaml")

    def test_config_scope_detection(self):
        """测试 scope 检测功能"""
        from opengrid.config import get_config_scope, reload_config
        reload_config("global")
        scope = get_config_scope()
        assert scope in ["global", "project"]


class TestInventoryPath:
    """测试库存路径功能"""

    def test_default_inventory_path(self):
        """测试默认库存路径"""
        from opengrid.config import load_config, reload_config
        from opengrid.inventory import get_inventory_path

        reload_config("global")
        config = load_config("global")
        path = get_inventory_path(config)
        assert str(path).endswith("inventory.json")

    def test_custom_inventory_path(self):
        """测试自定义库存路径"""
        from opengrid.inventory import get_inventory_path

        # 模拟项目配置中指定了自定义路径
        config = {"inventory_path": "/tmp/test_inventory.json"}
        path = get_inventory_path(config)
        assert str(path) == "/tmp/test_inventory.json"


class TestInventoryOperationsWithConfig:
    """测试库存操作使用正确的配置驱动路径"""

    def test_add_inventory_with_global_config(self, tmp_path):
        """测试全局配置下的库存添加"""
        from opengrid.inventory import add_inventory, load_inventory

        # 创建临时全局库存文件
        global_inv = tmp_path / "global_inventory.json"
        global_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        # 使用全局配置
        config = {"inventory_path": str(global_inv)}

        # 添加库存
        add_inventory({"7x5": 5}, reason="test", config=config)

        # 验证库存已添加
        inv = load_inventory(config)
        assert inv.get("7x5") == 5

    def test_add_inventory_with_project_config(self, tmp_path):
        """测试项目配置下的库存添加"""
        from opengrid.inventory import add_inventory, load_inventory

        # 创建临时项目库存文件
        project_inv = tmp_path / "project_inventory.json"
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        # 使用项目配置
        config = {"inventory_path": str(project_inv)}

        # 添加库存
        add_inventory({"10x5": 3, "8x8": 2}, reason="project test", config=config)

        # 验证库存已添加到项目文件
        inv = load_inventory(config)
        assert inv.get("10x5") == 3
        assert inv.get("8x8") == 2

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

    def test_separate_global_and_project_inventory(self, tmp_path):
        """测试全局和项目库存完全分离"""
        from opengrid.inventory import add_inventory, load_inventory

        # 创建两个独立的库存文件
        global_inv = tmp_path / "global.json"
        project_inv = tmp_path / "project.json"

        global_inv.write_text(json.dumps({"inventory": {}, "log": []}))
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        # 全局配置添加库存
        global_config = {"inventory_path": str(global_inv)}
        add_inventory({"7x5": 10}, reason="global", config=global_config)

        # 项目配置添加库存
        project_config = {"inventory_path": str(project_inv)}
        add_inventory({"10x5": 5}, reason="project", config=project_config)

        # 验证两者完全独立
        global_inv_data = load_inventory(global_config)
        project_inv_data = load_inventory(project_config)

        assert global_inv_data.get("7x5") == 10
        assert global_inv_data.get("10x5") is None

        assert project_inv_data.get("10x5") == 5
        assert project_inv_data.get("7x5") is None
