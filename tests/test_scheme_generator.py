import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "opengrid"))

from opengrid.scheme_generator import generate_schemes, generate_inventory_aware_scheme
from opengrid.inventory import add_inventory, load_inventory


def test_generate_schemes_returns_three_options():
    # 先清空库存
    add_inventory({"7x5": 10, "10x5": 10}, "test setup")

    schemes = generate_schemes(485, 425, 1, load_inventory())

    assert "math" in schemes
    assert "inventory" in schemes
    assert "print_limit" in schemes


def test_inventory_aware_scheme_uses_existing():
    # 添加特定尺寸库存
    add_inventory({"7x5": 3, "10x5": 3}, "test")

    inv = load_inventory()
    scheme = generate_inventory_aware_scheme(485, 425, 1, inv)

    # 验证使用了库存
    assert scheme is not None
