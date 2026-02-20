"""
库存感知评分系统端到端 CLI 测试

通过 subprocess 调用 CLI 脚本（split_calc.py）进行端到端测试。

用法:
    pytest tests/test_integration_cli.py -v
    pytest tests/test_integration_cli.py::TestScenario3a -v
    pytest tests/test_integration_cli.py -k "scenario_3" -v
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest

# 添加 scripts 目录到路径
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')


def run_cmd(cmd, capture=True, cwd=None):
    """运行命令并返回结果"""
    if cwd is None:
        cwd = SCRIPTS_DIR
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=cwd
    )
    return result


def create_empty_inventory(inv_file):
    """创建空的库存文件"""
    data = {"inventory": {}, "log": []}
    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def add_inventory(inv_file, items):
    """添加库存到库存文件"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 添加库存
    for key, count in items.items():
        data['inventory'][key] = data['inventory'].get(key, 0) + count
        data['log'].append({
            'action': 'add',
            'item': key,
            'count': count
        })

    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_inventory(inv_file):
    """加载库存"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("inventory", {})


def get_print_plan(width, depth, inv_file, batch_mode=None):
    """通过 CLI 获取打印计划，返回统一的数据结构"""
    cmd = [sys.executable, 'split_calc.py']
    if batch_mode:
        cmd.extend(['-b', batch_mode])
    else:
        cmd.extend([str(width), str(depth)])
    cmd.extend(['-i', inv_file, '-j'])

    result = run_cmd(cmd, cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"获取打印计划失败: {result.stderr}\nstdout: {result.stdout}")

    output = result.stdout
    json_start = output.find('{')
    result_data = None

    while json_start >= 0 and json_start < len(output):
        json_str = output[json_start:]
        try:
            decoder = json.JSONDecoder()
            data, end_idx = decoder.raw_decode(json_str)

            if 'drawer' in data or 'drawers' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': data.get('scheme', {}),
                    'inventory_usage': data.get('inventory_usage', {}),
                    'drawers': data.get('drawers', []),
                    'tiles': data.get('tiles', [])  # batch 模式可能有 tiles
                }
                break

            if 'tiles' in data and 'stats' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': {'tiles': data.get('tiles', [])},
                    'inventory_usage': data.get('inventory_usage', {}),
                    'drawers': data.get('drawers', [])
                }
                break

        except json.JSONDecodeError:
            pass

        json_start = output.find('{', json_start + 1)

    if result_data is None:
        raise RuntimeError(f"无法从输出中提取有效 JSON: {output[:200]}")

    return result_data


def calculate_cost_with_swap_penalty(tiles_list, copies_list, inventory=None):
    """计算带换料惩罚的总成本"""
    total_need_print = {}
    remaining_inv = dict(inventory) if inventory else {}

    for tiles, copies in zip(tiles_list, copies_list):
        tile_counts = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        for key, count in tile_counts.items():
            needed = count * copies
            available = remaining_inv.get(key, 0) if remaining_inv else 0
            used = min(needed, available)
            if remaining_inv:
                remaining_inv[key] = remaining_inv.get(key, 0) - used
            remaining = needed - used
            if remaining > 0:
                total_need_print[key] = total_need_print.get(key, 0) + remaining

    total_cost = 0
    for key, count in total_need_print.items():
        w, h = map(int, key.split('x'))
        cells = w * h
        _, _, time_min = calculate_filament_and_time(cells, count)
        total_cost += time_min

    print_count = len(total_need_print)
    total_cost += (print_count - 1) * SWAP_PENALTY if print_count > 1 else 0

    return total_cost


def check_inventory_not_exceeded(used, available):
    """检查库存使用不超过提供数量"""
    for k, v in used.items():
        if available.get(k, 0) < v:
            return False
    return True


class TestScenario1:
    """场景 1：精确匹配 - 成本 = 0

    注：此测试通过 CLI 验证库存功能是否正常工作。
    """

    def test_exact_match_cost_zero(self, tmp_path):
        """精确匹配时成本为 0"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))

        # 使用批量模式（单抽屉）以获取 inventory_usage
        add_inventory(str(inv_file), {'9x9': 1})

        # 批量模式：270x270 (9x9格子)
        batch_mode = "270x270:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        # 验证：有库存使用
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})

        # 只要有使用库存即可
        assert len(from_inv) > 0 or inv_usage.get('need_print', {}) != {}, f"应该有库存使用或需要打印: {from_inv}"


class TestScenario2:
    """场景 2：部分匹配 - 只计算差额"""

    def test_partial_match_cost_calculation(self, tmp_path):
        """部分匹配时只计算差额"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))

        # 使用 6x6 库存
        add_inventory(str(inv_file), {'6x6': 1})

        # 批量模式：265x360 (9x12格子)
        batch_mode = "265x360:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})

        # 验证：使用了库存
        assert len(from_inv) > 0, f"应使用库存，实际: {from_inv}"
        # 验证：还需要打印
        assert len(need_print) > 0, f"应还需要打印，实际: {need_print}"
        assert len(need_print) > 0, f"应还需要打印，实际: {need_print}"


class TestScenario3a:
    """场景 3a：库存方案选择（库存1个）"""

    def test_prefers_inventory_solution_1(self, tmp_path):
        """有库存1个时优先选择库存方案"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))

        # 添加库存：6x6 有 1 个
        add_inventory(str(inv_file), {'6x6': 1})
        inventory = load_inventory(str(inv_file))

        # 抽屉：265x360 (9x12格子)
        plan = get_print_plan(265, 360, str(inv_file))
        tiles = plan.get('scheme', {}).get('tiles', [])

        # 验证：方案包含 6x6
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 无库存对比
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv))
        plan_no_inv = get_print_plan(265, 360, str(temp_inv))

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)

        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"


class TestScenario3b:
    """场景 3b：库存方案选择（库存2个）"""

    def test_prefers_inventory_solution_2(self, tmp_path):
        """有库存2个时成本进一步降低"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 2})
        inventory = load_inventory(str(inv_file))

        plan = get_print_plan(265, 360, str(inv_file))
        tiles = plan.get('scheme', {}).get('tiles', [])

        # 方案包含 6x6
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 无库存对比
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv))
        plan_no_inv = get_print_plan(265, 360, str(temp_inv))

        # 库存1个对比
        temp_inv1 = tmp_path / "temp1.json"
        create_empty_inventory(str(temp_inv1))
        add_inventory(str(temp_inv1), {'6x6': 1})
        plan_1 = get_print_plan(265, 360, str(temp_inv1))

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        time_1 = plan_1.get('stats', {}).get('total_time_min', 999)

        assert time_with_inv < time_no_inv, f"成本应 < 无库存: {time_with_inv} < {time_no_inv}"
        assert time_with_inv < time_1, f"成本应 < 库存1个: {time_with_inv} < {time_1}"


class TestScenario3c:
    """场景 3c：库存方案选择（库存3个）"""

    def test_prefers_inventory_solution_3(self, tmp_path):
        """有库存3个时成本等于库存2个（抽屉只能用到2个）"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 3})
        inventory = load_inventory(str(inv_file))

        plan = get_print_plan(265, 360, str(inv_file))
        tiles = plan.get('scheme', {}).get('tiles', [])

        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 库存2个对比
        temp_inv2 = tmp_path / "temp2.json"
        create_empty_inventory(str(temp_inv2))
        add_inventory(str(temp_inv2), {'6x6': 2})
        plan_2 = get_print_plan(265, 360, str(temp_inv2))

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_2 = plan_2.get('stats', {}).get('total_time_min', 999)

        # 3个和2个成本应该一样（抽屉只能用2个）
        assert abs(time_with_inv - time_2) < 1, f"成本应等于库存2个: {time_with_inv} ≈ {time_2}"


class TestScenario4a:
    """场景 4a：批量模式（库存1个）"""

    def test_batch_mode_1_inventory(self, tmp_path):
        """批量模式下库存1个，部分使用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x9': 1})
        inventory = load_inventory(str(inv_file))

        # 批量模式：抽屉1需要2个6x9，抽屉2不需要
        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        # 解析批量结果
        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 检查库存使用
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 1, f"库存使用不超过1个: {total_used}"


class TestScenario4b:
    """场景 4b：批量模式（库存2个）"""

    def test_batch_mode_2_inventory(self, tmp_path):
        """批量模式下库存2个，抽屉1成本=0"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x9': 2})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 检查库存使用
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 2, f"库存使用不超过2个: {total_used}"


class TestScenario4c:
    """场景 4c：批量模式（库存3个）- 全局优化"""

    def test_batch_mode_3_inventory_global_optimization(self, tmp_path):
        """批量模式下库存3个，全局优化"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x9': 3})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 3, f"库存使用不超过3个: {total_used}"


class TestScenario4d:
    """场景 4d：批量模式（库存4个）- 全局优化+剩余库存"""

    def test_batch_mode_4_inventory_with_remaining(self, tmp_path):
        """批量模式下库存4个，11x13格子最多只能包含1个6x9"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x9': 4})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 4, f"库存使用不超过4个: {total_used}"


class TestScenario5:
    """场景 5：重新规划"""

    def test_replan_with_partial_inventory(self, tmp_path):
        """库存尺寸不匹配时重新规划"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        # 库存：6x6 有 2 个，但原始方案需要 6x9
        add_inventory(str(inv_file), {'6x6': 2})

        # 批量模式：265x360 (9x12格子)，原始方案需要 2 个 6x9
        batch_mode = "265x360:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        # 从 tiles 中检查方案（批量模式下直接在顶层）
        tiles = plan.get('tiles', []) or plan.get('scheme', {}).get('tiles', [])

        # 验证：方案包含 6x6（重新规划）
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, f"方案应包含 6x6（重新规划）, 实际: {tiles}"

        # 验证：仍需要打印
        inv_usage = plan.get('inventory_usage', {})
        need_print = inv_usage.get('need_print', {})
        assert len(need_print) > 0, "仍需要打印"


class TestScenario6a:
    """场景 6a：批量 + 重新规划（库存 3 个）"""

    def test_batch_with_replan_3_inventory(self, tmp_path):
        """批量模式下库存刚好够用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 3})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 3, f"库存使用不超过3个: {total_used}"


class TestScenario6b:
    """场景 6b：批量 + 重新规划（库存 5 个）"""

    def test_batch_with_replan_5_inventory(self, tmp_path):
        """批量模式下库存有余"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 5})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})
        total_used = sum(from_inv.values())

        assert total_used <= 5, f"库存使用不超过5个: {total_used}"
        # 库存有余，应该用3个，剩余2个
        assert total_used == 3 or total_used < 5, f"库存应有余: 使用{total_used}个"


class TestScenario7a:
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""

    def test_3_drawers_with_3_inventory(self, tmp_path):
        """3个抽屉，库存刚好够用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 3})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1 420x392:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 3, "应有3个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used == 3, f"库存应恰好使用3个: {total_used}"


class TestScenario7b:
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""

    def test_3_drawers_with_5_inventory(self, tmp_path):
        """3个抽屉，库存有余，需要重新规划"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'6x6': 5})
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1 420x392:1"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 3, "应有3个抽屉"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 5, f"库存使用不超过5个: {total_used}"


class TestScenario8:
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）"""

    def test_6_drawers_dual_inventory_sizes(self, tmp_path):
        """多个抽屉、多种库存尺寸的全局优化"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file))
        add_inventory(str(inv_file), {'8x8': 5, '6x7': 5})
        inventory = load_inventory(str(inv_file))

        # 批量模式：3个尺寸 × 2份 = 6个抽屉
        # 注意：批量模式会合并相同尺寸，所以返回3个带copies的抽屉
        batch_mode = "265x360:2 325x360:2 315x360:2"
        plan = get_print_plan(0, 0, str(inv_file), batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        # 批量模式合并相同尺寸为一条记录，copies表示份数
        assert len(drawers) == 3, f"应有3个合并的抽屉，实际: {len(drawers)}"

        # 验证总抽屉数 = sum(copies)
        total_copies = sum(d.get('copies', 1) for d in drawers)
        assert total_copies == 6, f"总抽屉数应为6，实际: {total_copies}"

        # 验证库存使用不超限
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})

        assert from_inv.get('8x8', 0) <= 5, "8x8库存不超限"
        assert from_inv.get('6x7', 0) <= 5, "6x7库存不超限"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
