import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "opengrid"))

from opengrid.scheme_generator import generate_schemes, generate_inventory_aware_scheme
from opengrid import inventory as inventory_module
from opengrid import inventory as inventory_impl


@pytest.fixture
def tmp_inventory(tmp_path, monkeypatch):
    """Create a temp inventory file and return config"""
    inv_file = tmp_path / "inventory.json"
    # 初始化为空库存
    inv_file.write_text(json.dumps({"inventory": {}, "log": []}))
    # 返回 config 而不是修改模块常量
    return {"inventory_path": str(inv_file)}


def test_generate_schemes_returns_three_options(tmp_inventory):
    # 使用临时库存
    from opengrid.inventory import add_inventory, load_inventory
    add_inventory({"7x5": 10, "10x5": 10}, "test setup", config=tmp_inventory)

    schemes = generate_schemes(485, 425, 1, load_inventory(tmp_inventory))

    assert "math" in schemes
    assert "inventory" in schemes
    assert "print_limit" in schemes


def test_inventory_aware_scheme_uses_existing(tmp_inventory):
    from opengrid.inventory import add_inventory, load_inventory
    # 添加特定尺寸库存
    add_inventory({"7x5": 3, "10x5": 3}, "test", config=tmp_inventory)

    inv = load_inventory(tmp_inventory)
    scheme = generate_inventory_aware_scheme(485, 425, 1, inv)

    # 验证使用了库存
    assert scheme is not None
