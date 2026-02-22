"""测试 scripts/inventory.py CLI 支持全局/项目级配置"""

import os
import sys
import json
import pytest
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class TestInventoryCLIScope:
    """测试 inventory.py CLI 支持 -l/--level 参数"""

    def test_inventory_help_shows_level_option(self):
        """测试帮助信息包含 -l/--level 选项"""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"), "--help"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        assert "-l" in result.stdout or "--level" in result.stdout

    def test_list_with_global_level(self, tmp_path):
        """测试使用项目级别（带全局配置）查看库存"""
        # 使用项目级别并通过配置文件指定全局库存
        global_inv = tmp_path / "global.json"
        global_inv.write_text(json.dumps({
            "inventory": {"7x5": 10},
            "log": []
        }))

        # 使用项目配置指向全局库存
        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: {global_inv}")

        # 在 tmp_path 运行，使用项目配置（自动检测）
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"), "-l", "project", "list"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证输出包含库存
        assert "7×5" in result.stdout or "7x5" in result.stdout

    def test_add_with_project_level(self, tmp_path):
        """测试使用项目级别添加库存"""
        # 创建项目目录和配置
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"),
             "-l", "project", "add", "8x8:5", "test reason"],
             capture_output=True,
             text=True,
             cwd=tmp_path
        )

        # 验证添加成功
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("8x8") == 5

    def test_add_to_global_creates_log_entry(self, tmp_path):
        """测试添加库存到项目并记录日志"""
        # 使用项目级别
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"),
             "-l", "project", "add", "7x7:3", "test log"],
             capture_output=True,
             text=True,
             cwd=tmp_path
        )

        # 验证日志记录
        data = json.loads(project_inv.read_text())
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"
        assert data["log"][0]["reason"] == "test log"

    def test_deduct_inventory_with_level(self, tmp_path):
        """测试使用级别参数扣减库存"""
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({
            "inventory": {"10x5": 8},
            "log": []
        }))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 扣减库存
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"),
             "-l", "project", "deduct", "10x5:3", "test deduct"],
             capture_output=True,
             text=True,
             cwd=tmp_path
        )

        # 验证扣减成功
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("10x5") == 5

    def test_undo_with_level(self, tmp_path):
        """测试使用级别参数撤销操作"""
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({
            "inventory": {},
            "log": []
        }))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"),
             "-l", "project", "add", "5x5:2", "undo test"],
             capture_output=True,
             text=True,
             cwd=tmp_path
        )

        # 撤销
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"),
             "-l", "project", "undo"],
             capture_output=True,
             text=True,
             cwd=tmp_path
        )

        # 验证已撤销
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("5x5") is None or data["inventory"].get("5x5") == 0


class TestInventoryCLIDefaultScope:
    """测试 inventory.py CLI 默认 scope 行为"""

    def test_default_scope_auto_detect(self, tmp_path):
        """测试默认使用自动检测"""
        # 无配置文件时，应使用全局
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"), "list"],
            capture_output=True,
            text=True,
            cwd=tmp_path  # tmp_path 没有 opengrid_config.yaml
        )

        # 应该能正常执行（使用全局库存）
        assert result.returncode == 0 or "inventory" in result.stdout.lower()

    def test_project_config_auto_detected(self, tmp_path):
        """测试项目配置自动检测"""
        # 创建项目配置
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({
            "inventory": {"9x9": 99},
            "log": []
        }))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 不指定 level，应该自动检测到项目配置
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py"), "list"],
            capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证输出包含项目库存
        assert "9×9" in result.stdout or "9x9" in result.stdout
