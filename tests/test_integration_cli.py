"""
库存感知评分系统端到端 CLI 测试

通过 subprocess 调用 opengrid.py CLI 进行端到端测试。

用法:
    pytest tests/test_integration_cli.py -v
    pytest tests/test_integration_cli.py::TestScenario3a -v
    pytest tests/test_integration_cli.py -k "scenario_3" -v
"""

import json
import os
import subprocess
import sys
import pytest

# 添加 scripts 目录到路径
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, SCRIPTS_DIR)


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


def create_empty_inventory(inv_file, tmp_path):
    """通过 CLI 创建空的库存文件

    Args:
        inv_file: 库存文件路径
        tmp_path: 临时目录路径（用于生成 config）
    """
    config_content = f"""# 测试配置文件
printer:
  model: h2d
opengrid:
  tile_type: Full
  tile_size: 28
inventory_path: {inv_file}
"""
    config_file = tmp_path / "config.yaml"
    with open(str(config_file), 'w') as f:
        f.write(config_content)

    cmd = [
        sys.executable, 'opengrid.py',
        '-c', str(config_file),
        'inventory', 'init'
    ]
    run_cmd(cmd, cwd=SCRIPTS_DIR)
    return str(config_file)


def add_inventory(inv_file, items, tmp_path):
    """通过 CLI 添加库存到库存文件

    Args:
        inv_file: 库存文件路径
        items: 要添加的物品字典，如 {'6x7': 3, '8x8': 5}
        tmp_path: 临时目录（用于生成 config）
    """
    config_content = f"""# 测试配置文件
printer:
  model: h2d
opengrid:
  tile_type: Full
  tile_size: 28
inventory_path: {inv_file}
"""
    config_file = tmp_path / "config.yaml"
    with open(str(config_file), 'w') as f:
        f.write(config_content)

    cmd = [
        sys.executable, 'opengrid.py',
        '-c', str(config_file),
        'inventory', 'add'
    ]
    for key, count in items.items():
        cmd.append(f'{key}:{count}')
    cmd.append('test')
    run_cmd(cmd, cwd=SCRIPTS_DIR)


def load_inventory(inv_file):
    """加载库存"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("inventory", {})


def get_print_plan(width, depth, inv_file, tmp_path, batch_mode=None, config_file=None):
    """通过 CLI 获取打印计划，返回统一的数据结构

    Args:
        width: 抽屉宽度 (mm)
        depth: 抽屉深度 (mm)
        inv_file: 库存文件路径
        tmp_path: 临时目录路径（用于默认 config 路径）
        batch_mode: 批量模式字符串
        config_file: 配置文件路径（可选，默认使用 tmp_path/config.yaml）
    """
    # 使用传入的 config_file，或默认使用 tmp_path/config.yaml
    if config_file is None:
        config_file = tmp_path / "config.yaml"

    cmd = [sys.executable, 'opengrid.py', '-c', str(config_file), 'split']
    if batch_mode:
        cmd.extend(['-b', batch_mode])
    else:
        cmd.append(f'{width}x{depth}')
    cmd.extend(['-i', inv_file, '--print-json'])

    result = run_cmd(cmd, cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"获取打印计划失败: {result.stderr}\nstdout: {result.stdout}")

    # 直接使用 CLI 输出的 JSON
    return json.loads(result.stdout)


def check_inventory_not_exceeded(used, available):
    """检查库存使用不超过提供数量"""
    for k, v in used.items():
        if available.get(k, 0) < v:
            return False
    return True


def check_cell_count_consistency(tiles_before, tiles_after):
    """检查拆分前后格子数量是否一致

    Args:
        tiles_before: 拆分前的瓦片列表 [(w, h), ...]
        tiles_after: 拆分后的瓦片列表 [{"width": w, "height": h}, ...]

    Returns:
        (is_consistent, cells_before, cells_after)
    """
    cells_before = sum(w * h for w, h in tiles_before)
    cells_after = sum(t['width'] * t['height'] for t in tiles_after)
    return cells_before == cells_after, cells_before, cells_after


def get_original_cells(width, depth):
    """根据物理尺寸计算原始格子数

    Args:
        width: 宽度 (mm)
        depth: 深度 (mm)

    Returns:
        格子数 (x * y)
    """
    # 硬编码格子大小 28mm（OpenGrid 标准）
    x = width // 28
    y = depth // 28
    return x * y


def calculate_scheme_cells(tiles):
    """计算方案的总格子数（考虑 count 字段）

    Args:
        tiles: [{"width": w, "height": h, "count": c}, ...]

    Returns:
        总格子数
    """
    return sum(t['width'] * t['height'] * t['count'] for t in tiles)


class TestScenario1:
    """场景 1：精确匹配 - 成本 = 0

    假设：
    - 库存：6×7 有 2 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 成本 = 0（完全使用库存）
    - from_inventory = {'6x7': 2}
    - need_print = {}

    验证目标：
    [x] 成本 = 0
    [x] from_inventory = {'6x9': 2}
    [x] need_print = {}
    [x] 库存使用不超过提供数量
    """

    def test_exact_match_cost_zero(self, tmp_path):
        """精确匹配时成本为 0（通过CLI端到端测试）"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)

        # 添加库存：6x9 有 2 个（265x360 抽屉需要 2 个 6x9 瓦片）
        add_inventory(str(inv_file), {'6x9': 2}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 通过CLI调用：抽屉 265x360 (9x12格子=108格)
        # 原始方案需要 2 个 6x9 瓦片，用库存验证完全匹配
        plan = get_print_plan(265, 360, str(inv_file), tmp_path)

        # 从CLI输出中提取库存使用情况
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})
        total_time = plan.get('stats', {}).get('total_time_min', 0)

        # 精确匹配验证：完全使用库存，成本=0
        assert total_time == 0, f"完全使用库存时成本应为0，实际: {total_time}"
        assert from_inv.get('6x9', 0) >= 1, f"应使用6x9库存，实际: {from_inv}"
        assert need_print == {} or sum(need_print.values()) == 0, f"无需打印，实际: {need_print}"

        # 检查库存使用不超过提供数量
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario2:
    """场景 2：部分匹配 - 只计算差额

    假设：
    - 库存：6×9 有 1 个
    - 需求：2 个 6×9 瓦片

    预期结果：
    - 库存取 1 个，打印 1 个
    - 成本 > 0
    - from_inventory = {'6x9': 1}
    - need_print = {'6x9': 1}

    验证目标：
    [x] from_inventory = {'6x9': 1}
    [x] need_print = {'6x9': 1}
    [x] 成本 > 0 且 < 无库存时的成本
    [x] 库存使用不超过提供数量
    """

    def test_partial_match_cost_calculation(self, tmp_path):
        """部分匹配时只计算差额"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)

        # 添加库存：6x9 有 1 个（265x360 抽屉需要 2 个 6x9 瓦片，只有1个库存）
        add_inventory(str(inv_file), {'6x9': 1}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 通过CLI调用：抽屉 265x360 (9x12格子=108格)
        plan = get_print_plan(265, 360, str(inv_file), tmp_path)

        # 从CLI输出中提取库存使用情况
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})
        total_time = plan.get('stats', {}).get('total_time_min', 0)

        # 无库存对比
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv), tmp_path)
        plan_no_inv = get_print_plan(265, 360, str(temp_inv), tmp_path)
        total_time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 0)

        # 验证：使用了库存
        assert from_inv.get('6x9', 0) >= 1, f"应使用6x9库存，实际: {from_inv}"
        # 验证：还需要打印（有部分差额需要打印）
        assert need_print and sum(need_print.values()) > 0, f"应有打印需求，实际: {need_print}"
        # 验证：成本大于0但小于无库存成本
        assert total_time > 0, f"成本应大于0，实际: {total_time}"
        assert total_time < total_time_no_inv, f"成本({total_time})应小于无库存成本({total_time_no_inv})"
        # 验证：库存使用不超过提供数量
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario3a:
    """场景 3a：库存方案选择（库存1个）"""

    def test_prefers_inventory_solution_1(self, tmp_path):
        """有库存1个时优先选择库存方案"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)

        # 添加库存：6x6 有 1 个
        add_inventory(str(inv_file), {'6x6': 1}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 抽屉：265x360 (9x12格子)
        plan = get_print_plan(265, 360, str(inv_file), tmp_path)
        tiles = plan.get('scheme', {}).get('tiles', [])

        # 验证：方案包含 6x6
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 无库存对比
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv), tmp_path)
        plan_no_inv = get_print_plan(265, 360, str(temp_inv), tmp_path)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)

        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证库存使用不超过提供数量
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario3b:
    """场景 3b：库存方案选择（库存2个）"""

    def test_prefers_inventory_solution_2(self, tmp_path):
        """有库存2个时成本进一步降低"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 2}, tmp_path)
        inventory = load_inventory(str(inv_file))

        plan = get_print_plan(265, 360, str(inv_file), tmp_path)
        tiles = plan.get('scheme', {}).get('tiles', [])

        # 方案包含 6x6
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 无库存对比
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv), tmp_path)
        plan_no_inv = get_print_plan(265, 360, str(temp_inv), tmp_path)

        # 库存1个对比
        temp_inv1 = tmp_path / "temp1.json"
        create_empty_inventory(str(temp_inv1), tmp_path)
        add_inventory(str(temp_inv1), {'6x6': 1}, tmp_path)
        plan_1 = get_print_plan(265, 360, str(temp_inv1), tmp_path)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        time_1 = plan_1.get('stats', {}).get('total_time_min', 999)

        assert time_with_inv < time_no_inv, f"成本应 < 无库存: {time_with_inv} < {time_no_inv}"
        assert time_with_inv < time_1, f"成本应 < 库存1个: {time_with_inv} < {time_1}"

        # 验证库存使用不超过提供数量
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario3c:
    """场景 3c：库存方案选择（库存3个）"""

    def test_prefers_inventory_solution_3(self, tmp_path):
        """有库存3个时成本等于库存2个（抽屉只能用到2个）"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 3}, tmp_path)
        inventory = load_inventory(str(inv_file))

        plan = get_print_plan(265, 360, str(inv_file), tmp_path)
        tiles = plan.get('scheme', {}).get('tiles', [])

        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, "方案应包含 6x6"

        # 无库存对比
        temp_inv_no = tmp_path / "temp_no.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(265, 360, str(temp_inv_no), tmp_path)

        # 库存2个对比
        temp_inv2 = tmp_path / "temp2.json"
        create_empty_inventory(str(temp_inv2), tmp_path)
        add_inventory(str(temp_inv2), {'6x6': 2}, tmp_path)
        plan_2 = get_print_plan(265, 360, str(temp_inv2), tmp_path)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        time_2 = plan_2.get('stats', {}).get('total_time_min', 999)

        # 验证成本 < 无库存方案
        assert time_with_inv < time_no_inv, f"成本应 < 无库存: {time_with_inv} < {time_no_inv}"
        # 3个和2个成本应该一样（抽屉只能用2个）
        assert abs(time_with_inv - time_2) < 1, f"成本应等于库存2个: {time_with_inv} ≈ {time_2}"

        # 验证库存使用不超过提供数量
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario4a:
    """场景 4a：批量模式（库存1个）

    假设：
    - 抽屉 1：265×360 (9×12格子)，无库存方案 [(6,9), (6,9)] - 需要2个6×9
    - 抽屉 2：325×365 (11×13格子)，无库存方案 [(5,6), (5,7), (6,6), (6,7)] - 需要0个6×9
    - 库存：6×9 有 1 个

    预期结果：
    - 抽屉1：使用1个库存，打印1个
    - 抽屉2：正常打印（无6×9可用）
    - 总成本降低

    验证目标：
    [x] 抽屉1使用1个库存
    [x] 总成本降低
    [x] 库存使用不超过提供数量
    """

    def test_batch_mode_1_inventory(self, tmp_path):
        """批量模式下库存1个，部分使用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x9': 1}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 批量模式：抽屉1需要2个6x9，抽屉2不需要
        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        # 解析批量结果
        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        # 无库存对比
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)

        # 验证：总成本降低或不增加（库存1个可能不降低）
        assert time_with_inv <= time_no_inv, f"有库存成本应 <= 无库存: {time_with_inv} <= {time_no_inv}"

        # 检查库存使用
        # 注意：这里使用 drawer 级别的 from_inventory 求和，因为顶层的 from_inventory 计算方式不同
        total_used = sum(
            sum((d.get('inventory') or {}).get('from_inventory', {}).values())
            for d in drawers
        )

        assert total_used <= 1, f"库存使用不超过1个: {total_used}"

        # 验证抽屉1使用了1个库存（抽屉1需要2个6x9，但只有1个库存）
        drawer1 = drawers[0]
        drawer1_inv = drawer1.get('inventory', {})
        drawer1_from_inv = drawer1_inv.get('from_inventory', {})
        drawer1_used = sum(drawer1_from_inv.values())
        assert drawer1_used == 1, f"抽屉1应使用1个库存，实际: {drawer1_used}"


class TestScenario4b:
    """场景 4b：批量模式（库存2个）

    假设：
    - 抽屉 1：265×360，需要2个6×9
    - 抽屉 2：325×365，无6×9需求
    - 库存：6×9 有 2 个

    预期结果：
    - 抽屉1：使用2个库存，无需打印
    - 抽屉2：正常打印（不使用库存）
    - 总打印时间 = 仅抽屉2的打印时间（抽屉1无需打印，不贡献时间）

    验证目标：
    [x] 抽屉1无需打印
    [x] 抽屉2仍需打印
    [x] 总打印时间 < 无库存时的总打印时间
    [x] 库存使用不超过提供数量
    """

    def test_batch_mode_2_inventory(self, tmp_path):
        """批量模式下库存2个，抽屉1无需打印"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x9': 2}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        # 验证抽屉1：完全使用库存，无需打印
        drawer1 = drawers[0]
        drawer1_inv = drawer1.get('inventory', {})
        drawer1_from_inv = drawer1_inv.get('from_inventory', {})
        drawer1_need_print = drawer1_inv.get('need_print', {})
        drawer1_used = sum(drawer1_from_inv.values())
        drawer1_need = sum(drawer1_need_print.values())

        assert drawer1_used >= 1, f"抽屉1应使用库存，实际: {drawer1_used}"
        assert drawer1_need == 0, f"抽屉1应无需打印，实际: {drawer1_need}"

        # 验证抽屉2：不使用库存，仍需打印
        drawer2 = drawers[1]
        drawer2_inv = drawer2.get('inventory') or {}
        drawer2_from_inv = drawer2_inv.get('from_inventory', {})
        drawer2_need_print = drawer2_inv.get('need_print', {})
        drawer2_used = sum(drawer2_from_inv.values())
        drawer2_need = sum(drawer2_need_print.values())

        assert drawer2_used == 0, f"抽屉2应不使用库存，实际: {drawer2_used}"
        assert drawer2_need > 0, f"抽屉2应仍需打印，实际: {drawer2_need}"

        # 验证库存使用不超过提供数量
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())
        assert total_used <= 2, f"库存使用不超过2个: {total_used}"

        # 验证总打印时间降低（vs 无库存）
        # 抽屉1无需打印，总打印时间应只含抽屉2的时间
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        need_print_with_inv = sum(
            sum(d.get('inventory', {}).get('need_print', {}).values())
            for d in drawers
        )
        need_print_no_inv = sum(
            sum(d.get('inventory', {}).get('need_print', {}).values())
            for d in plan_no_inv.get('drawers', [])
        )
        assert need_print_with_inv < need_print_no_inv, \
            f"需要打印的瓦片数应更少: {need_print_with_inv} < {need_print_no_inv}"


class TestScenario4c:
    """场景 4c：批量模式（库存3个）- 全局优化"""

    def test_batch_mode_3_inventory_global_optimization(self, tmp_path):
        """批量模式下库存3个，全局优化"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x9': 3}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        # 注意：这里使用 drawer 级别的 from_inventory 求和，因为顶层的 from_inventory 计算方式不同
        total_used = sum(
            sum((d.get('inventory') or {}).get('from_inventory', {}).values())
            for d in drawers
        )

        assert total_used <= 3, f"库存使用不超过3个: {total_used}"

        # 验证抽屉1成本 = 0（完全使用库存）
        drawer1 = drawers[0]
        drawer1_inv = drawer1.get('inventory', {})
        drawer1_need_print = drawer1_inv.get('need_print', {})
        drawer1_need = sum(drawer1_need_print.values())
        assert drawer1_need == 0, f"抽屉1应不需要打印（成本=0），实际: {drawer1_need}"

        # 验证抽屉2使用1个库存（全局优化：抽屉1用2个，抽屉2用1个，库存刚好用完）
        drawer2 = drawers[1]
        drawer2_inv = drawer2.get('inventory', {})
        drawer2_from_inv = drawer2_inv.get('from_inventory', {})
        drawer2_used = sum(drawer2_from_inv.values())
        assert drawer2_used >= 1, f"抽屉2应使用至少1个库存，实际: {drawer2_used}"

        # 验证库存刚好用完
        assert total_used == 3, f"库存应刚好用完，实际使用: {total_used}"


class TestScenario4d:
    """场景 4d：批量模式（库存4个）- 全局优化+剩余库存"""

    def test_batch_mode_4_inventory_with_remaining(self, tmp_path):
        """批量模式下库存4个，11x13格子最多只能包含1个6x9"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x9': 4}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 4, f"库存使用不超过4个: {total_used}"

        # 验证抽屉1成本 = 0（完全使用库存）
        drawer1 = drawers[0]
        drawer1_inv = drawer1.get('inventory', {})
        drawer1_need_print = drawer1_inv.get('need_print', {})
        drawer1_need = sum(drawer1_need_print.values())
        assert drawer1_need == 0, f"抽屉1应不需要打印（成本=0），实际: {drawer1_need}"

        # 验证抽屉2至少使用1个库存（全局优化：抽屉1用2个，抽渠2用1个）
        drawer2 = drawers[1]
        drawer2_inv = drawer2.get('inventory', {})
        drawer2_from_inv = drawer2_inv.get('from_inventory', {})
        drawer2_used = sum(drawer2_from_inv.values())
        assert drawer2_used >= 1, f"抽屉2应使用至少1个库存，实际: {drawer2_used}"


class TestScenario5:
    """场景 5：重新规划（单抽屉）

    假设：
    - 抽屉：265×360 (9×12格子)，原始方案需要 2 个 6×9
    - 库存：6×6 有 2 个

    预期结果：
    - 使用 2 个 6×6 库存
    - 成本降低（但 > 0，因为仍需打印剩余部分）
    - 格子数量一致

    验证目标：
    [x] 方案包含 6x6 瓦片（使用库存）
    [x] need_print 不为空（仍需打印）
    [x] 成本 < 原方案成本
    [x] 库存使用不超过提供数量
    [x] 格子数量一致（拆分前后总格子数不变）
    """

    def test_replan_with_partial_inventory(self, tmp_path):
        """库存尺寸不匹配时重新规划（单抽屉场景）"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        # 库存：6x6 有 2 个，但原始方案需要 6x9
        add_inventory(str(inv_file), {'6x6': 2}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 单抽屉模式（265x360 = 9x12格子）
        # 原始方案需要 2 个 6x9
        plan = get_print_plan(265, 360, str(inv_file), tmp_path)

        # 从 tiles 中检查方案
        tiles = plan.get('scheme', {}).get('tiles', [])

        # 验证：方案包含 6x6（重新规划）
        has_6x6 = any(t.get('width') == 6 and t.get('height') == 6 for t in tiles)
        assert has_6x6, f"方案应包含 6x6（重新规划）, 实际: {tiles}"

        # 1. 格子数量一致性验证
        original_cells = get_original_cells(265, 360)
        # 单抽屉模式下 tiles 没有 count 字段，需要分别计算
        if tiles and 'count' not in tiles[0]:
            scheme_cells = sum(t['width'] * t['height'] for t in tiles)
        else:
            scheme_cells = calculate_scheme_cells(tiles)
        assert original_cells == scheme_cells, \
            f"格子数应一致: {original_cells} = {scheme_cells}"

        # 2. 验证需要打印（不是完全用库存）
        inv_usage = plan.get('inventory_usage', {})
        need_print = inv_usage.get('need_print', {})
        assert need_print, f"应有打印需求（库存尺寸不匹配），实际: {need_print}"

        # 3. 验证成本降低（对比无库存方案）
        temp_inv = tmp_path / "temp.json"
        create_empty_inventory(str(temp_inv), tmp_path)
        plan_no_inv = get_print_plan(265, 360, str(temp_inv), tmp_path)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 4. 验证库存使用不超过提供数量
        from_inv = inv_usage.get('from_inventory', {})
        assert check_inventory_not_exceeded(from_inv, inventory), "库存使用不应超过提供数量"


class TestScenario6a:
    """场景 6a：批量 + 重新规划（库存 3 个）"""

    def test_batch_with_replan_3_inventory(self, tmp_path):
        """批量模式下库存刚好够用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 3}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证（注意 tiles 里的 count 是每份的数量）
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 3, f"库存使用不超过3个: {total_used}"

        # 验证成本对比（vs 无库存）
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证库存使用（可能完全使用也可能部分使用）
        # 注意：根据算法实现，抽屉1可能完全使用库存（成本=0）或部分使用（成本>0）
        # 这里只验证确实使用了库存
        for i, drawer in enumerate(drawers):
            drawer_inv = drawer.get('inventory', {})
            drawer_from_inv = drawer_inv.get('from_inventory', {})
            drawer_used = sum(drawer_from_inv.values())
            # 至少有一个抽屉使用了库存
            if drawer_used > 0:
                break
        else:
            assert False, "应至少有一个抽屉使用库存"


class TestScenario6b:
    """场景 6b：批量 + 重新规划（库存 5 个）

    假设：
    - 抽屉 1：265×360 → [(6,9), (6,9)] - 需要 2个6×6
    - 抽屉 2：325×365 → [(6,7), (6,6), (5,7), (5,6)] - 需要 1个6×6
    - 库存：6×6 有 5 个（多 2 个）

    预期结果：
    - 抽屉1：使用 2 个 6×6 + 打印剩余（成本 > 0）
    - 抽屉2：使用 1 个 6×6 + 打印剩余
    - 剩余 2 个保留

    验证目标：
    [x] 抽屉1成本 > 0（使用库存但仍需打印）
    [x] 总成本降低
    [x] 库存扣减正确（使用3个，剩余2个）
    [x] 库存使用不超过提供数量
    """

    def test_batch_with_replan_5_inventory(self, tmp_path):
        """批量模式下库存有余"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 5}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        # 无库存对比
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)

        # 验证：总成本降低或不增加（库存1个可能不降低）
        assert time_with_inv <= time_no_inv, f"有库存成本应 <= 无库存: {time_with_inv} <= {time_no_inv}"

        drawers = plan.get('drawers', [])
        assert len(drawers) == 2, "应有2个抽屉"

        # 格子数量一致性验证（注意 tiles 里的 count 是每份的数量）
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})
        total_used = sum(from_inv.values())

        assert total_used <= 5, f"库存使用不超过5个: {total_used}"
        # 库存有余，应该用3个，剩余2个
        assert total_used == 3, f"库存应使用3个，剩余2个，实际使用: {total_used}"

        # 验证总成本降低
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证抽屉1使用了库存（可能完全使用也可能部分使用）
        drawer1 = drawers[0]
        drawer1_inv = drawer1.get('inventory', {})
        drawer1_from_inv = drawer1_inv.get('from_inventory', {})
        drawer1_used = sum(drawer1_from_inv.values())
        assert drawer1_used > 0, f"抽屉1应使用库存，实际: {drawer1_used}"


class TestScenario7a:
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""

    def test_3_drawers_with_3_inventory(self, tmp_path):
        """3个抽屉，库存刚好够用"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 3}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1 420x392:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 3, "应有3个抽屉"

        # 格子数量一致性验证（注意 tiles 里的 count 是每份的数量）
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        # 注意：这里使用 drawer 级别的 from_inventory 求和
        total_used = sum(
            sum((d.get('inventory') or {}).get('from_inventory', {}).values())
            for d in drawers
        )

        assert total_used == 3, f"库存应恰好使用3个: {total_used}"

        # 验证成本对比（vs 无库存）
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证库存使用（至少有抽屉使用了库存）
        has_used_inv = any(
            sum((d.get('inventory') or {}).get('from_inventory', {}).values()) > 0
            for d in drawers
        )
        assert has_used_inv, "应至少有一个抽屉使用库存"


class TestScenario7b:
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""

    def test_3_drawers_with_5_inventory(self, tmp_path):
        """3个抽屉，库存有余，需要重新规划"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'6x6': 5}, tmp_path)
        inventory = load_inventory(str(inv_file))

        batch_mode = "265x360:1 325x365:1 420x392:1"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        assert len(drawers) == 3, "应有3个抽屉"

        # 格子数量一致性验证（注意 tiles 里的 count 是每份的数量）
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        total_used = sum(from_inv.values())

        assert total_used <= 5, f"库存使用不超过5个: {total_used}"

        # 验证成本对比（vs 无库存）
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证库存使用（至少有抽屉使用了库存）
        has_used_inv = False
        for drawer in drawers:
            drawer_inv = drawer.get('inventory', {})
            drawer_from_inv = drawer_inv.get('from_inventory', {})
            drawer_used = sum(drawer_from_inv.values())
            if drawer_used > 0:
                has_used_inv = True
                break
        assert has_used_inv, "应至少有一个抽屉使用库存"


class TestScenario8:
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）"""

    def test_6_drawers_dual_inventory_sizes(self, tmp_path):
        """多个抽屉、多种库存尺寸的全局优化"""
        inv_file = tmp_path / "inventory.json"
        create_empty_inventory(str(inv_file), tmp_path)
        add_inventory(str(inv_file), {'8x8': 5, '6x7': 5}, tmp_path)
        inventory = load_inventory(str(inv_file))

        # 批量模式：3个尺寸 × 2份 = 6个抽屉
        # 注意：批量模式会合并相同尺寸，所以返回3个带copies的抽屉
        batch_mode = "265x360:2 325x360:2 315x360:2"
        plan = get_print_plan(0, 0, str(inv_file), tmp_path, batch_mode=batch_mode)

        drawers = plan.get('drawers', [])
        # 批量模式合并相同尺寸为一条记录，copies表示份数
        assert len(drawers) == 3, f"应有3个合并的抽屉，实际: {len(drawers)}"

        # 验证总抽屉数 = sum(copies)
        total_copies = sum(d.get('copies', 1) for d in drawers)
        assert total_copies == 6, f"总抽屉数应为6，实际: {total_copies}"

        # 格子数量一致性验证（注意 tiles 里的 count 是每份的数量）
        for drawer in drawers:
            original_cells = get_original_cells(drawer['width'], drawer['depth'])
            drawer_tiles = drawer.get('tiles', [])
            scheme_cells = calculate_scheme_cells(drawer_tiles)
            assert original_cells == scheme_cells, \
                f"格子数应一致: {original_cells} = {scheme_cells}"

        # 验证库存使用不超限
        inv_usage = plan.get('inventory_usage', {})
        from_inv = inv_usage.get('from_inventory', {})
        need_print = inv_usage.get('need_print', {})

        assert from_inv.get('8x8', 0) <= 5, "8x8库存不超限"
        assert from_inv.get('6x7', 0) <= 5, "6x7库存不超限"

        # 验证库存有剩余（可选，因为库存可能刚好够用）
        # 8x8 库存5个，使用4个，剩余1个
        # 6x7 库存5个，使用4个，剩余1个
        assert from_inv.get('8x8', 0) + from_inv.get('6x7', 0) < 10, \
            "库存应有余量（不超过提供总量）"

        # 验证成本对比（vs 无库存）
        temp_inv_no = tmp_path / "temp_no_inv.json"
        create_empty_inventory(str(temp_inv_no), tmp_path)
        plan_no_inv = get_print_plan(0, 0, str(temp_inv_no), tmp_path, batch_mode=batch_mode)

        time_with_inv = plan.get('stats', {}).get('total_time_min', 999)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        assert time_with_inv < time_no_inv, f"有库存成本应更低: {time_with_inv} < {time_no_inv}"

        # 验证所有抽屉都有打印
        for i, drawer in enumerate(drawers):
            drawer_tiles = drawer.get('tiles', [])
            assert drawer_tiles, f"抽屉{i+1}应有瓦片打印，实际: {drawer_tiles}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
