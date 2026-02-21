"""测试配置和库存的全局/项目级分离"""

import os
import sys
import pytest
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
