"""compare 对比页：单抽屉 / 多抽屉两种 split --json 输出都要能渲染出真实数字

回归背景：喂多抽屉 JSON 时页面显示 "0×0 抽屉 / 0g / 0 种"。
"""
import json
import sys

import pytest

from opengrid.ui.presenter import generate_comparison_html
from test_integration_cli import SCRIPTS_DIR, run_cmd, create_empty_inventory, add_inventory


def _split_json(tmp_path, *args):
    r = run_cmd([sys.executable, 'opengrid.py', '-c', str(tmp_path / "config.yaml"), 'split', *args, '--json'],
                cwd=SCRIPTS_DIR)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.fixture
def inv(tmp_path):
    inv_file = tmp_path / "inventory.json"
    create_empty_inventory(str(inv_file), tmp_path)
    add_inventory(str(inv_file), {'8x8': 2}, tmp_path)
    return str(inv_file)


def test_batch_comparison_shows_real_numbers(tmp_path, inv):
    a = _split_json(tmp_path, '225x255:2', '325x460', '--no-inventory')
    b = _split_json(tmp_path, '225x255:2', '325x460', '-i', inv)
    html = generate_comparison_html(a, b)

    assert '2 只抽屉' in html
    assert '抽屉A' in html and '抽屉B' in html
    assert '0×0' not in html
    assert f"{round(a['stats']['total_time_min'], 1)} min" in html
    assert f"{round(b['stats']['total_filament_g'], 1)}g" in html
    assert '8×8 ×2（库存）' in html


def test_single_comparison_counts_copies(tmp_path, inv):
    a = _split_json(tmp_path, '225x255:2', '--no-inventory')
    b = _split_json(tmp_path, '225x255:2', '-i', inv)
    html = generate_comparison_html(a, b)
    assert '225×255 抽屉' in html
    assert '8×9 ×2' in html, "两份抽屉，每份 1 块 8x9，清单应显示 ×2"


def test_mixed_single_and_batch_rejected(tmp_path, inv):
    a = _split_json(tmp_path, '225x255:2', '--no-inventory')
    b = _split_json(tmp_path, '225x255:2', '325x460', '-i', inv)
    with pytest.raises(ValueError):
        generate_comparison_html(a, b)
