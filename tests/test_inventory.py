"""tests/test_inventory.py - inventory module tests"""
import pytest
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opengrid'))

from opengrid import inventory as inventory_module
from opengrid import inventory as inventory_impl


@pytest.fixture
def tmp_inventory(tmp_path, monkeypatch):
    """Create a temp inventory file and return config"""
    inv_file = tmp_path / "inventory.json"
    inv_file.write_text(json.dumps({"inventory": {}, "log": []}))
    # 返回 config 而不是修改模块常量
    return {"inventory_path": str(inv_file)}


class TestLoadSave:
    def test_load_empty_when_no_file(self, tmp_inventory):
        result = inventory_module.load_inventory(tmp_inventory)
        assert result == {}

    def test_load_existing(self, tmp_inventory):
        inv_file = tmp_path = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 6, "5x10": 3}, "log": []}, f)
        result = inventory_module.load_inventory(tmp_inventory)
        assert result == {"5x7": 6, "5x10": 3}

    def test_save_creates_file(self, tmp_inventory):
        inventory_impl.save_inventory(
            {"5x7": 6},
            {"action": "add", "items": {"5x7": 6}, "reason": "test"},
            tmp_inventory
        )
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file) as f:
            data = json.load(f)
        assert data["inventory"] == {"5x7": 6}
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"

    def test_save_appends_log(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({
                "inventory": {"5x7": 3},
                "log": [{"action": "add", "items": {"5x7": 3}, "reason": "first"}]
            }, f)
        inventory_impl.save_inventory(
            {"5x7": 6},
            {"action": "add", "items": {"5x7": 3}, "reason": "second"},
            tmp_inventory
        )
        with open(inv_file) as f:
            data = json.load(f)
        assert len(data["log"]) == 2


class TestAddInventory:
    def test_add_new_items(self, tmp_inventory):
        result = inventory_module.add_inventory({"5x7": 6, "5x10": 3}, reason="打印完成", config=tmp_inventory)
        assert result == {"5x7": 6, "5x10": 3}

    def test_add_to_existing(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 3}, "log": []}, f)
        result = inventory_module.add_inventory({"5x7": 3}, reason="追加", config=tmp_inventory)
        assert result == {"5x7": 6}

    def test_add_logs_operation(self, tmp_inventory):
        inventory_module.add_inventory({"5x7": 6}, reason="test add", config=tmp_inventory)
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file) as f:
            data = json.load(f)
        assert data["log"][-1]["action"] == "add"
        assert data["log"][-1]["items"] == {"5x7": 6}


class TestDeductInventory:
    def test_deduct_basic(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 6, "5x10": 3}, "log": []}, f)
        result = inventory_module.deduct_inventory({"5x7": 3}, reason="用于抽屉", config=tmp_inventory)
        assert result == {"5x7": 3, "5x10": 3}

    def test_deduct_exact(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 3}, "log": []}, f)
        result = inventory_module.deduct_inventory({"5x7": 3}, reason="全部用完", config=tmp_inventory)
        assert result == {}  # 0 的 key 应被移除

    def test_deduct_insufficient_raises(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 2}, "log": []}, f)
        with pytest.raises(ValueError, match="库存不足"):
            inventory_module.deduct_inventory({"5x7": 5}, reason="超出", config=tmp_inventory)

    def test_deduct_missing_key_raises(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {}, "log": []}, f)
        with pytest.raises(ValueError, match="库存不足"):
            inventory_module.deduct_inventory({"5x7": 1}, reason="不存在", config=tmp_inventory)


class TestUndoLast:
    def test_undo_add(self, tmp_inventory):
        inventory_module.add_inventory({"5x7": 6}, reason="打印", config=tmp_inventory)
        result = inventory_module.undo_last(tmp_inventory)
        assert result == {}

    def test_undo_deduct(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 6}, "log": []}, f)
        inventory_module.deduct_inventory({"5x7": 3}, reason="用于抽屉", config=tmp_inventory)
        result = inventory_module.undo_last(tmp_inventory)
        assert result == {"5x7": 6}

    def test_undo_empty_log_raises(self, tmp_inventory):
        with pytest.raises(ValueError, match="没有可撤销的操作"):
            inventory_module.undo_last(tmp_inventory)

    def test_undo_already_undone_raises(self, tmp_inventory):
        inventory_module.add_inventory({"5x7": 6}, reason="打印", config=tmp_inventory)
        inventory_module.undo_last(tmp_inventory)
        with pytest.raises(ValueError, match="没有可撤销的操作"):
            inventory_module.undo_last(tmp_inventory)


class TestGetInventoryMatch:
    def test_full_match(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 6}, "log": []}, f)
        inv = inventory_module.load_inventory(tmp_inventory)
        # scheme has 3 tiles of 7x5, copies=2 -> need 6 total
        result = inventory_module.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5)],
            copies=2,
            inv=inv
        )
        assert result["from_inventory"] == {"5x7": 6}
        assert result["need_print"] == {}
        assert result["match_score"] == 6

    def test_partial_match(self, tmp_inventory):
        inv_file = tmp_inventory["inventory_path"]
        with open(inv_file, 'w') as f:
            json.dump({"inventory": {"5x7": 2}, "log": []}, f)
        inv = inventory_module.load_inventory(tmp_inventory)
        # need 3 tiles of 7x5 (copies=1)
        result = inventory_module.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5)],
            copies=1,
            inv=inv
        )
        assert result["from_inventory"] == {"5x7": 2}
        assert result["need_print"] == {"5x7": 1}
        assert result["match_score"] == 2

    def test_no_match(self, tmp_inventory):
        inv = {}
        result = inventory_module.get_inventory_match(
            tiles=[(7, 5), (10, 5)],
            copies=1,
            inv=inv
        )
        assert result["from_inventory"] == {}
        assert result["need_print"] == {"5x7": 1, "5x10": 1}
        assert result["match_score"] == 0

    def test_mixed_sizes(self, tmp_inventory):
        inv = {"5x7": 10, "5x10": 1}
        # tiles: 3x 7x5, 3x 10x5, copies=2 -> need 6x 7x5, 6x 10x5
        result = inventory_module.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5), (10, 5), (10, 5), (10, 5)],
            copies=2,
            inv=inv
        )
        assert result["from_inventory"] == {"5x7": 6, "5x10": 1}
        assert result["need_print"] == {"5x10": 5}
        assert result["match_score"] == 7


class TestOrientationIndependentKeys:
    """库存 key 与方向无关：7x6 和 6x7 是同一块瓦片（旋转 90°）"""

    def test_match_inventory_accepts_large_side_first_key(self):
        from opengrid.core.cost import _match_inventory
        from_inv, need = _match_inventory([(6, 7), (6, 7)], {"7x6": 3}, copies=2)
        assert from_inv == {"6x7": 3}
        assert need == {"6x7": 1}

    def test_load_inventory_normalizes_and_merges(self, tmp_path):
        inv_file = tmp_path / "inventory.json"
        inv_file.write_text(json.dumps({"inventory": {"7x6": 3, "6x7": 1}, "log": []}))
        assert inventory_impl.load_inventory({"inventory_path": str(inv_file)}) == {"6x7": 4}

    def test_deduct_with_either_orientation(self, tmp_path):
        inv_file = tmp_path / "inventory.json"
        inv_file.write_text(json.dumps({"inventory": {"7x6": 3}, "log": []}))
        config = {"inventory_path": str(inv_file)}
        assert inventory_impl.deduct_inventory({"6x7": 1}, "t", config) == {"6x7": 2}
        assert inventory_impl.undo_last(config) == {"6x7": 3}
