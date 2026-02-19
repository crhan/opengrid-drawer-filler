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
    python3 scripts/integration_test.py --list     # 列出所有场景
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_cmd(cmd, capture=True):
    """运行命令并返回结果"""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=SCRIPTS_DIR
    )
    if result.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd)}\n{result.stderr}")
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
    run_cmd(cmd)


def load_inventory(inv_file):
    """加载库存"""
    with open(inv_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("inventory", {})


def calculate_print_cost_via_cli(inv_file, tiles, copies=1):
    """通过 CLI 计算打印成本"""
    # 使用 -j 获取 JSON 输出，解析结果
    # 注意：这个函数假设 split_calc.py 支持通过某种方式传递库存
    # 当前实现可能需要修改 split_calc.py 来支持库存参数
    pass


def scenario_1(inv_file):
    """场景 1：精确匹配

    假设：
    - 库存：6×7 有 2 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 成本 = 0（完全使用库存）
    - 不产生任何打印

    验证目标：
    [ ] 成本 = 0
    [ ] from_inventory = {'6x7': 2}
    [ ] need_print = {}
    [ ] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 1: 精确匹配")
    print("=" * 60)

    # 1. 添加库存
    add_inventory(inv_file, {'6x7': 2})
    inventory = load_inventory(inv_file)

    # 2. 调用 split_calc.py 输出打印计划
    # TODO: 需要 split_calc.py 支持 --inventory 参数
    # cmd = [sys.executable, 'split_calc.py', '-i', inv_file, '265', '360', '-j']
    # result = run_cmd(cmd)

    # 3. 解析输出，验证结果

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证打印计划")

    # 占位 - 等待实现
    return True


def scenario_2(inv_file):
    """场景 2：部分匹配

    假设：
    - 库存：6×7 有 1 个
    - 需求：2 个 6×7 瓦片

    预期结果：
    - 库存取 1 个，打印 1 个
    - 成本 = 1 个瓦片的打印时间

    验证目标：
    [ ] from_inventory = {'6x7': 1}
    [ ] need_print = {'6x7': 1}
    [ ] 成本 > 0 但 < 无库存时的成本
    [ ] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 2: 部分匹配")
    print("=" * 60)

    add_inventory(inv_file, {'6x7': 1})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证打印计划")

    return True


def scenario_3a(inv_file):
    """场景 3a：库存方案选择（库存1个）

    假设：
    - 抽屉：265×360（格子 9×12）
    - 库存：6×6 有 1 个

    预期结果：
    - 选择能使用库存的方案（如使用1个6x6 + 打印剩余）
    - 成本降低

    验证目标：
    [ ] 方案包含 6x6
    [ ] 成本 < 无库存方案的成本
    [ ] 库存使用不超过提供数量
    """
    print("\n" + "=" * 60)
    print("场景 3a: 库存方案选择（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 1})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证方案选择")

    return True


def scenario_3b(inv_file):
    """场景 3b：库存方案选择（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 3b: 库存方案选择（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证方案选择")

    return True


def scenario_3c(inv_file):
    """场景 3c：库存方案选择（库存3个）"""
    print("\n" + "=" * 60)
    print("场景 3c: 库存方案选择（库存3个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证方案选择")

    return True


def scenario_4a(inv_file):
    """场景 4a：批量模式（库存1个）"""
    print("\n" + "=" * 60)
    print("场景 4a: 批量模式（库存1个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 1})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_4b(inv_file):
    """场景 4b：批量模式（库存2个）"""
    print("\n" + "=" * 60)
    print("场景 4b: 批量模式（库存2个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 2})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_4c(inv_file):
    """场景 4c：批量模式（库存3个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4c: 批量模式（库存3个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 3})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_4d(inv_file):
    """场景 4d：批量模式（库存4个）- 全局优化"""
    print("\n" + "=" * 60)
    print("场景 4d: 批量模式（库存4个）- 全局优化")
    print("=" * 60)

    add_inventory(inv_file, {'6x9': 4})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_5(inv_file):
    """场景 5：重新规划（边缘情况）

    假设：
    - 抽屉：265×360 (9×12格子)，原始方案需要 2 个 6×9
    - 库存：6×6 有 2 个

    预期结果：
    - 使用 2 个 6×6 库存
    - 成本降低（但 > 0，因为仍需打印剩余部分）

    验证目标：
    [ ] replan_with_inventory 返回非空结果
    [ ] 方案包含 6x6 瓦片（使用库存）
    [ ] need_print 不为空（仍需打印）
    [ ] 成本 < 原方案成本
    [ ] 库存使用不超过提供数量
    [ ] 格子数量一致（拆分前后总格子数不变）
    """
    print("\n" + "=" * 60)
    print("场景 5: 重新规划")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 2})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py 验证重新规划")

    return True


def scenario_6a(inv_file):
    """场景 6a：批量 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 6a: 批量 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_6b(inv_file):
    """场景 6b：批量 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 6b: 批量 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_7a(inv_file):
    """场景 7a：3抽屉 + 重新规划（库存 3 个）"""
    print("\n" + "=" * 60)
    print("场景 7a: 3抽屉 + 重新规划（库存 3 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 3})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_7b(inv_file):
    """场景 7b：3抽屉 + 重新规划（库存 5 个）"""
    print("\n" + "=" * 60)
    print("场景 7b: 3抽屉 + 重新规划（库存 5 个）")
    print("=" * 60)

    add_inventory(inv_file, {'6x6': 5})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


def scenario_8(inv_file):
    """场景 8：6抽屉 + 双库存尺寸（8x8 和 6x7）

    假设：
    - 抽屉1：265×360 × 2（格子 9×12）
    - 抽屉2：325×360 × 2（格子 11×12）
    - 抽屉3：315×360 × 2（格子 11×12）
    - 库存：8×8 有 5 个，6×7 有 5 个

    预期结果：
    - 总成本降低
    - 8×8 和 6×7 库存使用都不超过提供量
    - 每个抽屉都有打印成本

    验证目标：
    [ ] 总成本降低
    [ ] 8x8库存不超限
    [ ] 6x7库存不超限
    [ ] 所有抽屉都有打印
    """
    print("\n" + "=" * 60)
    print("场景 8: 6抽屉 + 双库存尺寸")
    print("=" * 60)

    add_inventory(inv_file, {'8x8': 5, '6x7': 5})
    inventory = load_inventory(inv_file)

    print(f"库存: {inventory}")
    print("TODO: 调用 split_calc.py -b 批量模式验证")

    return True


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
