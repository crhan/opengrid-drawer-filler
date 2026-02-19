"""tests/test_inventory.py - inventory module tests"""
import pytest
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import inventory


@pytest.fixture
def tmp_inventory(tmp_path, monkeypatch):
    """Create a temp inventory file and patch INVENTORY_FILE"""
    inv_file = tmp_path / "inventory.json"
    monkeypatch.setattr(inventory, 'INVENTORY_FILE', str(inv_file))
    return inv_file


class TestLoadSave:
    def test_load_empty_when_no_file(self, tmp_inventory):
        result = inventory.load_inventory()
        assert result == {}

    def test_load_existing(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6, "10x5": 3},
            "log": []
        }))
        result = inventory.load_inventory()
        assert result == {"7x5": 6, "10x5": 3}

    def test_save_creates_file(self, tmp_inventory):
        inventory.save_inventory(
            {"7x5": 6},
            {"action": "add", "items": {"7x5": 6}, "reason": "test"}
        )
        data = json.loads(tmp_inventory.read_text())
        assert data["inventory"] == {"7x5": 6}
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"

    def test_save_appends_log(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": [{"action": "add", "items": {"7x5": 3}, "reason": "first"}]
        }))
        inventory.save_inventory(
            {"7x5": 6},
            {"action": "add", "items": {"7x5": 3}, "reason": "second"}
        )
        data = json.loads(tmp_inventory.read_text())
        assert len(data["log"]) == 2


class TestAddInventory:
    def test_add_new_items(self, tmp_inventory):
        result = inventory.add_inventory({"7x5": 6, "10x5": 3}, reason="打印完成")
        assert result == {"7x5": 6, "10x5": 3}

    def test_add_to_existing(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": []
        }))
        result = inventory.add_inventory({"7x5": 3}, reason="追加")
        assert result == {"7x5": 6}

    def test_add_logs_operation(self, tmp_inventory):
        inventory.add_inventory({"7x5": 6}, reason="test add")
        data = json.loads(tmp_inventory.read_text())
        assert data["log"][-1]["action"] == "add"
        assert data["log"][-1]["items"] == {"7x5": 6}


class TestDeductInventory:
    def test_deduct_basic(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6, "10x5": 3},
            "log": []
        }))
        result = inventory.deduct_inventory({"7x5": 3}, reason="用于抽屉")
        assert result == {"7x5": 3, "10x5": 3}

    def test_deduct_exact(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": []
        }))
        result = inventory.deduct_inventory({"7x5": 3}, reason="全部用完")
        assert result == {}  # 0 的 key 应被移除

    def test_deduct_insufficient_raises(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 2},
            "log": []
        }))
        with pytest.raises(ValueError, match="库存不足"):
            inventory.deduct_inventory({"7x5": 5}, reason="超出")

    def test_deduct_missing_key_raises(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {},
            "log": []
        }))
        with pytest.raises(ValueError, match="库存不足"):
            inventory.deduct_inventory({"7x5": 1}, reason="不存在")
