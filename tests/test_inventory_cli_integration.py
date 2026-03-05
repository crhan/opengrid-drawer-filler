"""Inventory CLI 集成测试 - 完整环境测试

测试在隔离的临时环境中执行，模拟真实用户操作流程：
1. 创建临时项目目录
2. 初始化配置文件
3. 执行所有 CLI 操作并验证 inventory.json
"""
import json
import os
import subprocess
import sys
import pytest
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def tmp_project_dir(tmp_path):
    """创建临时项目目录并初始化配置"""
    # 创建项目目录结构
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # 创建 inventory.json（初始为空）
    inv_file = project_dir / "inventory.json"
    inv_file.write_text(json.dumps({"inventory": {}, "log": []}))

    # 创建配置文件
    config_file = project_dir / "opengrid_config.yaml"
    config_file.write_text("""initialized: true
inventory_path: inventory.json
printer:
  model: p1p
""")

    return project_dir


def run_inventory_cli(args, cwd):
    """运行 opengrid.py inventory CLI 并返回结果"""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "opengrid.py"), "inventory"] + args,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    return result


def read_inventory_json(project_dir):
    """读取 inventory.json"""
    inv_file = project_dir / "inventory.json"
    return json.loads(inv_file.read_text())


class TestInventoryCLIIntegration:
    """Inventory CLI 完整集成测试"""

    def test_list_empty_inventory(self, tmp_project_dir):
        """测试 list 命令 - 空库存"""
        result = run_inventory_cli(["list"], tmp_project_dir)

        assert result.returncode == 0
        # 空库存应该显示 "库存为空" 或类似信息
        assert "为空" in result.stdout or "empty" in result.stdout.lower()

    def test_add_new_items(self, tmp_project_dir):
        """测试 add 命令 - 添加新物品"""
        # 执行添加
        result = run_inventory_cli(
            ["add", "8x8:5", "6x7:3", "--reason", "测试入库"],
            tmp_project_dir
        )

        assert result.returncode == 0

        # 检查 inventory.json
        data = read_inventory_json(tmp_project_dir)

        assert data["inventory"].get("8x8") == 5
        assert data["inventory"].get("6x7") == 3

        # 检查日志
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"
        assert data["log"][0]["items"] == {"8x8": 5, "6x7": 3}
        assert data["log"][0]["reason"] == "测试入库"

    def test_add_to_existing_inventory(self, tmp_project_dir):
        """测试 add 命令 - 追加到现有库存"""
        # 先添加一些库存
        run_inventory_cli(["add", "8x8:5", "--reason", "初始入库"], tmp_project_dir)

        # 再添加更多
        result = run_inventory_cli(
            ["add", "8x8:3", "6x7:2", "--reason", "追加入库"],
            tmp_project_dir
        )

        assert result.returncode == 0

        # 检查 inventory.json
        data = read_inventory_json(tmp_project_dir)

        assert data["inventory"].get("8x8") == 8  # 5 + 3
        assert data["inventory"].get("6x7") == 2
        assert len(data["log"]) == 2

    def test_deduct_items(self, tmp_project_dir):
        """测试 deduct 命令 - 扣减库存"""
        # 先添加库存
        run_inventory_cli(["add", "8x8:10", "--reason", "初始入库"], tmp_project_dir)

        # 扣减
        result = run_inventory_cli(
            ["deduct", "8x8:4", "--reason", "打印使用"],
            tmp_project_dir
        )

        assert result.returncode == 0

        # 检查 inventory.json
        data = read_inventory_json(tmp_project_dir)

        assert data["inventory"].get("8x8") == 6  # 10 - 4

        # 检查日志
        assert len(data["log"]) == 2
        assert data["log"][1]["action"] == "deduct"
        assert data["log"][1]["items"] == {"8x8": 4}
        assert data["log"][1]["reason"] == "打印使用"

    def test_deduct_exact_amount(self, tmp_project_dir):
        """测试 deduct 命令 - 扣减到零"""
        # 先添加库存
        run_inventory_cli(["add", "8x8:5", "--reason", "初始入库"], tmp_project_dir)

        # 扣减全部
        result = run_inventory_cli(
            ["deduct", "8x8:5", "--reason", "全部使用"],
            tmp_project_dir
        )

        assert result.returncode == 0

        # 检查 inventory.json - 数量为0的应该被移除
        data = read_inventory_json(tmp_project_dir)

        assert "8x8" not in data["inventory"] or data["inventory"].get("8x8") == 0

    def test_deduct_insufficient_raises_error(self, tmp_project_dir):
        """测试 deduct 命令 - 库存不足应报错"""
        # 先添加少量库存
        run_inventory_cli(["add", "8x8:2", "--reason", "初始入库"], tmp_project_dir)

        # 尝试扣减超过库存的数量
        result = run_inventory_cli(
            ["deduct", "8x8:5", "--reason", "超出库存"],
            tmp_project_dir
        )

        # 应该返回错误
        assert result.returncode != 0
        assert "不足" in result.stdout or "不足" in result.stderr

    def test_undo_add_operation(self, tmp_project_dir):
        """测试 undo 命令 - 撤销添加操作"""
        # 添加库存
        run_inventory_cli(["add", "8x8:5", "--reason", "测试入库"], tmp_project_dir)

        # 验证添加成功
        data = read_inventory_json(tmp_project_dir)
        assert data["inventory"].get("8x8") == 5

        # 撤销
        result = run_inventory_cli(["undo"], tmp_project_dir)

        assert result.returncode == 0

        # 检查 inventory.json - 应该被撤销
        data = read_inventory_json(tmp_project_dir)

        assert "8x8" not in data["inventory"] or data["inventory"].get("8x8") == 0

        # 检查日志 - 应该有 undo 记录
        # undo 会移除之前的 add 记录，但添加一条 undo 记录
        log_actions = [entry["action"] for entry in data["log"]]
        assert "undo" in log_actions

    def test_undo_deduct_operation(self, tmp_project_dir):
        """测试 undo 命令 - 撤销扣减操作"""
        # 先添加库存
        run_inventory_cli(["add", "8x8:10", "--reason", "初始入库"], tmp_project_dir)

        # 扣减库存
        run_inventory_cli(["deduct", "8x8:4", "--reason", "测试扣减"], tmp_project_dir)

        # 验证扣减后库存
        data = read_inventory_json(tmp_project_dir)
        assert data["inventory"].get("8x8") == 6

        # 撤销
        result = run_inventory_cli(["undo"], tmp_project_dir)

        assert result.returncode == 0

        # 检查 inventory.json - 应该恢复到扣减前
        data = read_inventory_json(tmp_project_dir)

        assert data["inventory"].get("8x8") == 10

    def test_undo_no_operation_raises_error(self, tmp_project_dir):
        """测试 undo 命令 - 没有操作时应该报错"""
        # 不执行任何操作直接撤销
        result = run_inventory_cli(["undo"], tmp_project_dir)

        # 应该返回错误
        assert result.returncode != 0
        assert "没有可撤销" in result.stdout or "没有可撤销" in result.stderr

    def test_multiple_operations_sequence(self, tmp_project_dir):
        """测试多步操作序列"""
        # 1. 添加库存
        run_inventory_cli(["add", "8x8:10", "6x7:5", "--reason", "初始入库"], tmp_project_dir)

        # 2. 添加更多
        run_inventory_cli(["add", "8x8:2", "--reason", "追加入库"], tmp_project_dir)

        # 3. 扣减
        run_inventory_cli(["deduct", "8x8:5", "--reason", "打印使用"], tmp_project_dir)

        # 4. 再次扣减
        run_inventory_cli(["deduct", "6x7:3", "--reason", "用于测试"], tmp_project_dir)

        # 检查最终状态
        data = read_inventory_json(tmp_project_dir)

        # 8x8: 10 + 2 - 5 = 7
        assert data["inventory"].get("8x8") == 7
        # 6x7: 5 - 3 = 2
        assert data["inventory"].get("6x7") == 2

        # 应该有多条日志
        assert len(data["log"]) == 4

    def test_list_with_items(self, tmp_project_dir):
        """测试 list 命令 - 有库存时"""
        # 添加库存
        run_inventory_cli(["add", "8x8:5", "6x7:3", "--reason", "测试入库"], tmp_project_dir)

        # 列出库存
        result = run_inventory_cli(["list"], tmp_project_dir)

        assert result.returncode == 0
        # 应该显示库存信息
        assert "8×8" in result.stdout or "8x8" in result.stdout
        assert "6×7" in result.stdout or "6x7" in result.stdout

    def test_reason_is_optional_for_add(self, tmp_project_dir):
        """测试 add 命令 - reason 是可选的"""
        # 不提供 reason
        result = run_inventory_cli(["add", "8x8:5"], tmp_project_dir)

        assert result.returncode == 0

        # 检查 inventory.json
        data = read_inventory_json(tmp_project_dir)
        assert data["inventory"].get("8x8") == 5

        # 应该使用默认 reason
        assert data["log"][0]["reason"] != ""

    def test_reason_is_optional_for_deduct(self, tmp_project_dir):
        """测试 deduct 命令 - reason 是可选的"""
        # 先添加库存
        run_inventory_cli(["add", "8x8:5", "--reason", "初始"], tmp_project_dir)

        # 不提供 reason 扣减
        result = run_inventory_cli(["deduct", "8x8:2"], tmp_project_dir)

        assert result.returncode == 0

        # 检查 inventory.json
        data = read_inventory_json(tmp_project_dir)
        assert data["inventory"].get("8x8") == 3
