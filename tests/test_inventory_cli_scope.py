"""测试 opengrid.py inventory CLI 项目级配置"""

import os
import sys
import json
import pytest
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class TestInventoryCLIScope:
    """测试 opengrid.py inventory CLI 项目级配置"""

    def test_add_to_project(self, tmp_path):
        """测试添加库存到项目"""
        # 创建项目目录和配置
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"),
             "inventory", "add", "8x8:5", "test reason"],
             capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证添加成功
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("8x8") == 5

    def test_add_creates_log_entry(self, tmp_path):
        """测试添加库存记录日志"""
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({"inventory": {}, "log": []}))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"),
             "inventory", "add", "7x7:3", "test log"],
             capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证日志记录
        data = json.loads(project_inv.read_text())
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"
        assert data["log"][0]["reason"] == "test log"

    def test_deduct_inventory(self, tmp_path):
        """测试扣减库存"""
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({
            "inventory": {"10x5": 8},
            "log": []
        }))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 扣减库存
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"),
             "inventory", "deduct", "10x5:3", "test deduct"],
             capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证扣减成功
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("10x5") == 5

    def test_undo_operation(self, tmp_path):
        """测试撤销操作"""
        project_inv = tmp_path / "inventory.json"
        project_inv.write_text(json.dumps({
            "inventory": {},
            "log": []
        }))

        config_file = tmp_path / "opengrid_config.yaml"
        config_file.write_text(f"inventory_path: inventory.json")

        # 添加库存
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"),
             "inventory", "add", "5x5:2", "undo test"],
             capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 撤销
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"),
             "inventory", "undo"],
             capture_output=True,
            text=True,
            cwd=tmp_path
        )

        # 验证已撤销
        data = json.loads(project_inv.read_text())
        assert data["inventory"].get("5x5") is None or data["inventory"].get("5x5") == 0
