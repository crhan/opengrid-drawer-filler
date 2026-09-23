"""split 多抽屉路由 + 批量 JSON 契约（slicer_commands、库存份数一致性）

回归背景：`split 225x255:2 325x460` 曾只算第一只抽屉（dims[0]），第二只静默丢弃；
批量 JSON 没有 slicer_commands，每抽屉 need_print 没乘份数，跟顶层 inventory_usage 对不上。
"""
import json
import sys

from test_integration_cli import SCRIPTS_DIR, run_cmd, create_empty_inventory, add_inventory


def _split(tmp_path, *args):
    config_file = tmp_path / "config.yaml"
    result = run_cmd([sys.executable, 'opengrid.py', '-c', str(config_file), 'split', *args], cwd=SCRIPTS_DIR)
    return result


def _setup(tmp_path, inventory=None):
    inv_file = tmp_path / "inventory.json"
    create_empty_inventory(str(inv_file), tmp_path)
    if inventory:
        add_inventory(str(inv_file), inventory, tmp_path)
    return str(inv_file)


def test_multiple_positional_dims_plan_all_drawers(tmp_path):
    _setup(tmp_path)
    r = _split(tmp_path, '225x255:2', '325x460', '--json')
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert [d['name'] for d in data['drawers']] == ['抽屉A', '抽屉B']
    assert [(d['width'], d['depth'], d['copies']) for d in data['drawers']] == [(225, 255, 2), (325, 460, 1)]


def test_batch_json_has_slicer_commands_matching_to_print(tmp_path):
    _setup(tmp_path)
    data = json.loads(_split(tmp_path, '225x255:2', '325x460', '--json').stdout)
    assert data['slicer_commands'], "批量 JSON 必须带 slicer_commands"
    # 每条命令的层数加起来 == 每种瓦片的 to_print
    printed = {}
    for cmd in data['slicer_commands']:
        w, h, s = map(int, cmd.split()[-1].split('x'))
        printed[(w, h)] = printed.get((w, h), 0) + s
    expected = {(t['width'], t['height']): t['to_print'] for t in data['tiles'] if t['to_print']}
    assert printed == expected
    assert len(data['slicer_commands']) == data['stats']['total_prints']


def test_drawer_inventory_multiplies_copies_and_sums_to_top_level(tmp_path):
    inv = _setup(tmp_path, {'8x8': 2})
    data = json.loads(_split(tmp_path, '225x255:2', '325x460', '-i', inv, '--json').stdout)

    a = data['drawers'][0]['inventory']
    assert a['need_print'] == {'8x9': 2}, "抽屉A 两份，每份一块 8x9，应打印 2 块"

    agg_from, agg_need = {}, {}
    for d in data['drawers']:
        for k, v in d['inventory']['from_inventory'].items():
            agg_from[k] = agg_from.get(k, 0) + v
        for k, v in d['inventory']['need_print'].items():
            agg_need[k] = agg_need.get(k, 0) + v
    assert agg_from == data['inventory_usage']['from_inventory']
    assert agg_need == data['inventory_usage']['need_print']


def test_bare_number_pair_is_one_drawer(tmp_path):
    _setup(tmp_path)
    r = _split(tmp_path, '225', '255', '--json', '--no-inventory')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)['dimensions'] == {'width': 225, 'depth': 255, 'copies': 1}


def test_unrecognized_token_is_error_not_silently_dropped(tmp_path):
    _setup(tmp_path)
    r = _split(tmp_path, '225x255', 'abc', '--json')
    assert r.returncode == 1
    assert 'abc' in r.stderr


def test_too_small_drawer_in_batch_is_error(tmp_path):
    _setup(tmp_path)
    r = _split(tmp_path, '225x255', '30x30', '--json')
    assert r.returncode == 1
    assert '30×30' in r.stderr


def test_copies_flag_is_default_copies(tmp_path):
    _setup(tmp_path)
    data = json.loads(_split(tmp_path, '225x255', '325x460:3', '-c', '2', '--json', '--no-inventory').stdout)
    assert [d['copies'] for d in data['drawers']] == [2, 3]
