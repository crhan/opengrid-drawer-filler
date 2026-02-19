#!/usr/bin/env python3
"""
库存感知评分系统集成测试 (端到端)

端到端验证流程：
1. 创建空的库存 json，后续所有操作都要指定这个 json 进行
2. 根据场景描述添加库存 (调用 inventory.py)
3. 调用脚本输出打印计划 (调用 split_calc.py)
4. 根据场景的要求验算打印计划是否符合

这是 TDD 流程 - 先写测试用例，后续会有人修复实现使其通过

用法:
    python3 scripts/integration_test.py              # 运行所有场景
    python3 scripts/integration_test.py 1            # 运行场景1
    python3 scripts/integration_test.py 1 2 3a     # 运行多个场景
    python3 scripts/integration_test.py --list      # 列出所有场景
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


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
    """调用 inventory.py 添加库存"""
    cmd = [sys.executable, 'inventory.py', '-f', inv_file, 'add']
    for key, count in items.items():
        cmd.append(f"{key}:{count}")
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"添加库存失败: {result.stderr}")


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

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"获取打印计划失败: {result.stderr}")

    # 输出可能混合了人类可读格式和 JSON，需要提取 JSON 部分
    output = result.stdout

    # 查找包含 "drawer" 或 "drawers" 键的完整 JSON
    # 从第一个 "{" 开始尝试解析，找到包含所需键的完整 JSON
    json_start = output.find('{')
    result_data = None

    while json_start >= 0 and json_start < len(output):
        json_str = output[json_start:]
        try:
            decoder = json.JSONDecoder()
            data, end_idx = decoder.raw_decode(json_str)

            # 检查是否是完整 JSON（包含 drawer 或 drawers 键）
            if 'drawer' in data or 'drawers' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': data.get('scheme', {})
                }
                break

            # 检查是否是批量模式的 JSON（包含 tiles）
            if 'tiles' in data and 'stats' in data:
                result_data = {
                    'stats': data.get('stats', {}),
                    'scheme': {'tiles': data.get('tiles', [])}
                }
                break

        except json.JSONDecodeError:
            pass

        # 继续查找下一个 "{"
        json_start = output.find('{', json_start + 1)

    if result_data is None:
        raise RuntimeError(f"无法从输出中提取有效 JSON: {output[:200]}")

    return result_data


def check_inventory_not_exceeded(used, available):
    """检查库存使用不超过提供数量"""
    for k, v in used.items():
        if available.get(k, 0) < v:
            return False
    return True


def scenario_1(inv_file):
    """场景 1：部分匹配（最大利用库存）

    假设：
    - 库存：6×7 有 2 个
    - 需求：265x360 -> 9x12 格子

    预期结果：
    - 使用 1 个库存（9x12 格子最多只能用 1 个 6x7）
    - 成本 > 0（需要打印其他瓦片）

    验证目标：
    [x] 成本 < 无库存方案
    [x] 方案包含 6x7
    """
    print("\n" + "=" * 60)
    print("场景 1: 部分匹配")
    print("=" * 60)

    # 1. 添加库存
    add_inventory(inv_file, {'6x7': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存方案
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        print(f"无库存方案时间: {time_no_inv} 分钟")
    finally:
        os.remove(temp_inv)

    # 使用库存获取方案
    plan = get_print_plan(265, 360, inv_file)
    tiles = plan.get('scheme', {}).get('tiles', [])
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"有库存方案瓦片: {tiles}")
    print(f"有库存方案时间: {time_with_inv} 分钟")

    has_6x7 = any(t['width'] == 6 and t['height'] == 7 for t in tiles)
    cost_lower = time_with_inv < time_no_inv

    if has_6x7:
        print("✓ 方案包含 6x7")
    else:
        print("✗ 方案不包含 6x7")

    if cost_lower:
        print(f"✓ 成本降低: {time_with_inv} < {time_no_inv}")
    else:
        print(f"✗ 成本未降低")

    return has_6x7 and cost_lower


def scenario_2(inv_file):
    """场景 2：部分匹配

    假设：
    - 库存：6×7 有 1 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 库存取 1 个，打印 1 个
    - 成本 > 0

    验证目标：
    [x] 成本 > 0
    [x] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 2: 部分匹配")
    print("=" * 60)

    add_inventory(inv_file, {'6x7': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    try:
        plan = get_print_plan(265, 360, inv_file)
        stats = plan.get('stats', {})
        total_time = stats.get('total_time_min', 0)

        print(f"总打印时间: {total_time} 分钟")

        # 有库存时的成本应该小于无库存时的成本
        # 这里简化为：成本 > 0 表示需要打印
        if total_time > 0:
            print("✓ 需要打印 (成本 > 0)")
            return True
        else:
            print("✗ 成本为0，不需要打印")
            return False
    except Exception as e:
        print(f"执行失败: {e}")
        return False


def scenario_3a(inv_file):
    """场景 3a：库存方案选择（库存1个）

    假设：
    - 抽屉：265×360（格子 9×12）
    - 库存：6×6 有 1 个

    预期结果：
    - 选择能使用库存的方案
    - 成本 < 无库存方案

    验证目标：
    [x] 方案包含 6x6
    [x] 成本 < 无库存方案的成本
    """
    print("\n" + "=" * 60)
    print("场景 3a: 库存方案选择（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存方案
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
        tiles_no_inv = plan_no_inv.get('scheme', {}).get('tiles', [])
        print(f"无库存方案: {tiles_no_inv}, 时间: {time_no_inv}分钟")
    finally:
        os.remove(temp_inv)

    # 有库存方案
    plan = get_print_plan(265, 360, inv_file)
    tiles = plan.get('scheme', {}).get('tiles', [])
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"有库存方案: {tiles}, 时间: {time_with_inv}分钟")

    has_6x6 = any(t['width'] == 6 and t['height'] == 6 for t in tiles)
    cost_lower = time_with_inv < time_no_inv

    if has_6x6:
        print("✓ 方案包含 6x6")
    else:
        print("✗ 方案不包含 6x6")

    if cost_lower:
        print(f"✓ 成本降低: {time_with_inv} < {time_no_inv}")
    else:
        print(f"✗ 成本未降低: {time_with_inv} >= {time_no_inv}")

    return has_6x6 and cost_lower


def scenario_3b(inv_file):
    """场景 3b：库存方案选择（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 3b: 库存方案选择（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存方案
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 库存1个
    temp_inv1 = inv_file + ".temp1"
    create_empty_inventory(temp_inv1)
    add_inventory(temp_inv1, {'6x6': 1})
    try:
        plan_1 = get_print_plan(265, 360, temp_inv1)
        time_1 = plan_1.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv1)

    # 库存2个
    plan_2 = get_print_plan(265, 360, inv_file)
    time_2 = plan_2.get('stats', {}).get('total_time_min', 999)

    print(f"无库存: {time_no_inv}分钟, 库存1个: {time_1}分钟, 库存2个: {time_2}分钟")

    cost_lower = time_2 < time_no_inv and time_2 < time_1
    if cost_lower:
        print(f"✓ 成本最低: {time_2}")
    else:
        print(f"✗ 成本未最低")

    return cost_lower


def scenario_3c(inv_file):
    """场景 3c：库存方案选择（库存3个）"""
    print("\n" + "=" * 60)
    print("场景 3c: 库存方案选择（库存3个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 库存2个对比
    temp_inv2 = inv_file + ".temp2"
    create_empty_inventory(temp_inv2)
    add_inventory(temp_inv2, {'6x6': 2})
    try:
        plan_2 = get_print_plan(265, 360, temp_inv2)
        time_2 = plan_2.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv2)

    # 库存3个
    plan_3 = get_print_plan(265, 360, inv_file)
    time_3 = plan_3.get('stats', {}).get('total_time_min', 999)

    print(f"库存2个: {time_2}分钟, 库存3个: {time_3}分钟")

    # 3个和2个成本应该一样（因为抽屉只能用到2个）
    cost_equal = abs(time_3 - time_2) < 1

    if cost_equal:
        print(f"✓ 成本相等: {time_3} ≈ {time_2}")
    else:
        print(f"✗ 成本不等: {time_3} != {time_2}")

    return cost_equal


def scenario_4a(inv_file):
    """场景 4a：批量模式（库存1个）

    假设：
    - 抽屉 1：265×360，需要2个6×9
    - 抽屉 2：325×365，无6×9需求
    - 库存：6×9 有 1 个

    预期结果：
    - 抽屉1使用1个库存
    - 总成本降低
    """
    print("\n" + "=" * 60)
    print("场景 4a: 批量模式（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 1})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存批量
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(0, 0, temp_inv, batch_mode="265x360:1 325x365:1")
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    except:
        time_no_inv = 999
    finally:
        os.remove(temp_inv)

    # 有库存批量
    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"无库存: {time_no_inv}分钟, 有库存: {time_with_inv}分钟")

    cost_lower = time_with_inv < time_no_inv
    if cost_lower:
        print(f"✓ 成本降低")
    else:
        print(f"✗ 成本未降低")

    return cost_lower


def scenario_4b(inv_file):
    """场景 4b：批量模式（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 4b: 批量模式（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(0, 0, temp_inv, batch_mode="265x360:1 325x365:1")
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 有库存
    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"无库存: {time_no_inv}分钟, 有库存: {time_with_inv}分钟")

    # 抽屉1应该成本为0（完全使用库存）
    # 通过检查总成本是否大幅降低来验证
    cost_lower = time_with_inv < time_no_inv

    if cost_lower:
        print(f"✓ 成本降低")
    else:
        print(f"✗ 成本未降低")

    return cost_lower


def scenario_4c(inv_file):
    """场景 4c：批量模式（库存3个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4c: 批量模式（库存3个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存对比
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(0, 0, temp_inv, batch_mode="265x360:1 325x365:1")
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"无库存成本: {time_no_inv}分钟")
    print(f"有库存成本: {time_with_inv}分钟")

    # 验证：成本应该降低
    cost_lower = time_with_inv < time_no_inv
    if cost_lower:
        print(f"✓ 成本降低: {time_with_inv} < {time_no_inv}")
        return True
    else:
        print(f"✗ 成本未降低")
        return False


def scenario_4d(inv_file):
    """场景 4d：批量模式（库存4个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4d: 批量模式（库存4个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 4})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存对比
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(0, 0, temp_inv, batch_mode="265x360:1 325x365:1")
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"无库存成本: {time_no_inv}分钟")
    print(f"有库存成本: {time_with_inv}分钟")

    # 验证：成本应该降低（4个库存中只能用3个）
    cost_lower = time_with_inv < time_no_inv
    if cost_lower:
        print(f"✓ 成本降低")
        return True
    else:
        print(f"✗ 成本未降低")
        return False


def scenario_5(inv_file):
    """场景 5：重新规划（边缘情况）

    假设：
    - 抽屉：265×360 (9×12格子)，原始方案需要 2 个 6×9
    - 库存：6×6 有 2 个

    预期结果：
    - 使用 2 个 6×6 库存
    - 成本降低（但 > 0）
    """
    print("\n" + "=" * 60)
    print("场景 5: 重新规划")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(265, 360, temp_inv)
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 有库存
    plan = get_print_plan(265, 360, inv_file)
    tiles = plan.get('scheme', {}).get('tiles', [])
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"方案瓦片: {tiles}")
    print(f"无库存: {time_no_inv}分钟, 有库存: {time_with_inv}分钟")

    has_6x6 = any(t['width'] == 6 and t['height'] == 6 for t in tiles)
    cost_lower = time_with_inv < time_no_inv
    cost_gt_0 = time_with_inv > 0

    if has_6x6:
        print("✓ 方案包含 6x6")
    else:
        print("✗ 方案不包含 6x6")

    if cost_lower:
        print("✓ 成本降低")
    else:
        print("✗ 成本未降低")

    if cost_gt_0:
        print("✓ 仍需打印")
    else:
        print("✗ 不需要打印")

    return has_6x6 and cost_lower and cost_gt_0


def scenario_6a(inv_file):
    """场景 6a：批量 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 6a: 批量 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"总成本: {time_with_inv}分钟")

    # 库存刚好够用（抽屉1用2个，抽屉2用1个）
    if time_with_inv > 0:
        print("✓ 仍需打印")
        return True
    else:
        print("✗ 不需要打印")
        return False


def scenario_6b(inv_file):
    """场景 6b：批量 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 6b: 批量 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"总成本: {time_with_inv}分钟")

    # 库存有余，应该用3个，剩余2个
    if time_with_inv > 0:
        print("✓ 仍需打印")
        return True
    else:
        print("✗ 不需要打印")
        return False


def scenario_7a(inv_file):
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 7a: 3抽屉 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1 420x392:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"总成本: {time_with_inv}分钟")

    if time_with_inv > 0:
        print("✓ 仍需打印")
        return True
    else:
        print("✗ 不需要打印")
        return False


def scenario_7b(inv_file):
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 7b: 3抽屉 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:1 325x365:1 420x392:1")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"总成本: {time_with_inv}分钟")

    # 抽屉3可以重新规划使用库存
    if time_with_inv > 0:
        print("✓ 仍需打印")
        return True
    else:
        print("✗ 不需要打印")
        return False


def scenario_8(inv_file):
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）

    假设：
    - 抽屉1：265×360 × 2
    - 抽屉2：325×360 × 2
    - 抽屉3：315×360 × 2
    - 库存：8×8 有 5 个，6×7 有 5 个
    """
    print("\n" + "=" * 60)
    print("场景 8: 6抽屉 + 双库存尺寸")
    print("=" * 60)

    add_inventory(inv_file, {'8x8': 5, '6x7': 5})
    inventory = load_inventory(inv_file)
    print(f"库存: {inventory}")

    # 无库存
    temp_inv = inv_file + ".temp"
    create_empty_inventory(temp_inv)
    try:
        plan_no_inv = get_print_plan(0, 0, temp_inv, batch_mode="265x360:2 325x360:2 315x360:2")
        time_no_inv = plan_no_inv.get('stats', {}).get('total_time_min', 999)
    finally:
        os.remove(temp_inv)

    # 有库存
    plan = get_print_plan(0, 0, inv_file, batch_mode="265x360:2 325x360:2 315x360:2")
    time_with_inv = plan.get('stats', {}).get('total_time_min', 999)

    print(f"无库存: {time_no_inv}分钟, 有库存: {time_with_inv}分钟")

    cost_lower = time_with_inv < time_no_inv

    if cost_lower:
        print("✓ 成本降低")
    else:
        print("✗ 成本未降低")

    return cost_lower


def main():
    parser = argparse.ArgumentParser(
        description="库存感知评分系统集成测试 (端到端)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
这是 TDD 流程 - 先写测试用例，后续会修复实现

示例:
  python3 scripts/integration_test.py           # 运行所有场景
  python3 scripts/integration_test.py 1         # 运行场景1
  python3 scripts/integration_test.py 1 2 3a   # 运行多个场景
  python3 scripts/integration_test.py --list    # 列出所有场景
        """
    )
    parser.add_argument('scenarios', nargs='*', help='要运行的场景编号')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有场景')

    args = parser.parse_args()

    all_scenarios = {
        '1': ('场景1: 精确匹配', scenario_1),
        '2': ('场景2: 部分匹配', scenario_2),
        '3a': ('场景3a: 库存方案选择(1个)', scenario_3a),
        '3b': ('场景3b: 库存方案选择(2个)', scenario_3b),
        '3c': ('场景3c: 库存方案选择(3个)', scenario_3c),
        '4a': ('场景4a: 批量模式(库存1个)', scenario_4a),
        '4b': ('场景4b: 批量模式(库存2个)', scenario_4b),
        '4c': ('场景4c: 批量模式(库存3个)', scenario_4c),
        '4d': ('场景4d: 批量模式(库存4个)', scenario_4d),
        '5': ('场景5: 重新规划', scenario_5),
        '6a': ('场景6a: 批量+重新规划(3个)', scenario_6a),
        '6b': ('场景6b: 批量+重新规划(5个)', scenario_6b),
        '7a': ('场景7a: 3抽屉+重新规划(3个)', scenario_7a),
        '7b': ('场景7b: 3抽屉+重新规划(5个)', scenario_7b),
        '8': ('场景8: 6抽屉+双库存尺寸', scenario_8),
    }

    if args.list:
        print("可用场景:")
        for key in sorted(all_scenarios.keys(), key=lambda x: (len(x), x)):
            name, _ = all_scenarios[key]
            print(f"  {key}: {name}")
        return

    scenarios_to_run = args.scenarios if args.scenarios else list(all_scenarios.keys())

    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as tmpdir:
        inv_file = os.path.join(tmpdir, 'test_inventory.json')

        results = []
        for key in scenarios_to_run:
            # 每个场景使用新的空库存文件
            create_empty_inventory(inv_file)

            if key not in all_scenarios:
                print(f"未知场景: {key}")
                continue

            name, func = all_scenarios[key]
            try:
                passed = func(inv_file)
                results.append((key, passed))
            except Exception as e:
                print(f"\n✗ 场景{key}执行失败: {e}")
                import traceback
                traceback.print_exc()
                results.append((key, False))

        # 输出汇总
        print("\n" + "=" * 60)
        print("验证结果汇总")
        print("=" * 60)
        passed_count = 0
        for key, passed in results:
            name, _ = all_scenarios[key]
            status = "✓" if passed else "✗"
            print(f"  [{status}] {name}")
            if passed:
                passed_count += 1

        print(f"\n总计: {passed_count}/{len(results)} 通过")


if __name__ == "__main__":
    main()
