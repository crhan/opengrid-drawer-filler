#!/usr/bin/env python3
"""
openGrid 抽屉分割计算器 - 优化版
验证分割方案的合法性，输出最优分割
支持预设、JSON 输出、自动生成 STL
"""

import argparse
import json
import os
import sys

# 导入配置模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config, get_printer_config

# 加载配置
_config = load_config()
_printer = get_printer_config()

# 瓦片厚度定义
TILE_THICKNESS = {
    "Full": 6.8,
    "Lite": 4.0,
    "Heavy": 13.8
}

# 从配置获取参数
TILE_SIZE = _config["opengrid"].get("tile_size", 28)
MAX_Z = _printer["max_z"]
MAX_X = _printer["bed_x"] // TILE_SIZE
MAX_Y = _printer["bed_y"] // TILE_SIZE
MIN_TILE = 2

# 计算每层厚度
tile_type = _config["opengrid"].get("tile_type", "Full")
interface_separation = _config["opengrid"].get("interface_separation", 0.2)
stacking_method = _config["opengrid"].get("stacking_method", "Ironing")

if stacking_method == "Ironing":
    FULL_THICKNESS = TILE_THICKNESS.get(tile_type, 6.8) + 2 * interface_separation
else:
    # Interface Layer: tile_thickness + interface_thickness + 2 * interface_separation
    FULL_THICKNESS = TILE_THICKNESS.get(tile_type, 6.8) + 0.4 + 2 * interface_separation

# 耗材和打印时间估算常量（基于实测数据）
FILAMENT_MAIN_PER_CELL = 1.13     # 主耗材: g/格/层
FILAMENT_SUPPORT_PER_CELL = 0.06  # 支撑耗材: g/格/层 (约主耗材的5.4%)
PRINT_TIME_PER_CELL = 3.1        # 打印时间: 分钟/格/层

# 预设抽屉尺寸
PRESETS = {
    "klean": (270, 170, "Klean件盒"),
    "ikea-sunda": (360, 500, "IKEA Sunda"),
    "ikea-kal": (360, 500, "IKEA KAL"),
    "ikea-alex": (360, 500, "IKEA Alex"),
    "standard": (400, 400, "标准抽屉"),
    "small": (300, 300, "小抽屉"),
    "medium": (400, 400, "中抽屉"),
    "large": (500, 500, "大抽屉"),
}


def get_max_stacks():
    """计算最大stack数量"""
    return int(MAX_Z // FULL_THICKNESS)


def get_grid_dimensions(width_mm, depth_mm):
    """计算可用格子数"""
    x = width_mm // TILE_SIZE
    y = depth_mm // TILE_SIZE
    return x, y


def validate_tile(w, h):
    """验证单块瓦片是否合法"""
    return MIN_TILE <= w <= MAX_X and MIN_TILE <= h <= MAX_Y


def split_with_limit(n, parts, max_val):
    """将数字n分割为parts个部分，每个部分不超过max_val"""
    if parts == 1:
        return [[n]] if n <= max_val else []

    results = []

    def recurse(remaining, current):
        if len(current) == parts - 1:
            if MIN_TILE <= remaining <= max_val:
                current.append(remaining)
                results.append(current[:])
                current.pop()
            return

        # 剪枝：如果剩余值太少无法分配给剩余部分，提前退出
        min_needed = MIN_TILE * (parts - len(current) - 1)
        if remaining < min_needed:
            return

        # 剪枝：如果剩余值太多无法分配给剩余部分，提前退出
        max_allowed = max_val * (parts - len(current) - 1)
        if remaining > max_allowed + max_val:
            return

        for i in range(MIN_TILE, min(max_val, remaining - min_needed) + 1):
            current.append(i)
            recurse(remaining - i, current)
            current.pop()

    recurse(n, [])
    return results


def calc_balance(splits):
    """计算分割的均衡度，返回最大值/最小值的比例（越小越均衡）"""
    if not splits or min(splits) == 0:
        return 1
    return max(splits) / min(splits)


def calc_scheme_balance(xs, ys):
    """计算方案的均衡度：取x方向和y方向均衡度的最大值"""
    x_balance = calc_balance(xs)
    y_balance = calc_balance(ys)
    return max(x_balance, y_balance)


# 方案排序键：成本 -> 独特尺寸 -> 瓦片数 -> 均衡度
SCHEME_SORT_KEY = lambda s: (s['cost'], s['unique_sizes'], s['total_tiles'], s['balance'])


def normalize_tiles(tiles):
    """规范化瓦片：如果瓦片宽度超过 MAX_X 但高度在范围内，则旋转该瓦片

    Args:
        tiles: 瓦片列表 [(w, h), ...]

    Returns:
        规范化后的瓦片列表
    """
    normalized = []
    for w, h in tiles:
        if w > MAX_X and h <= MAX_Y:
            normalized.append((h, w))
        else:
            normalized.append((w, h))
    return normalized


def validate_tiles(tiles):
    """验证所有瓦片是否合法

    Args:
        tiles: 瓦片列表 [(w, h), ...]

    Returns:
        True 如果所有瓦片都合法
    """
    return all(validate_tile(w, h) for w, h in tiles)


def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
    """直接寻找最优方案，找到1种尺寸就停止

    Args:
        x, y: 格子数
        verbose: 是否打印详细信息
        inventory: 库存字典 {"6x7": 3, ...}，None 表示不使用库存
        copies: 打印份数
    """
    # 首先检查是否需要分割
    if validate_tile(x, y):
        return {
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
            'unique_sizes': 1,
            'tile_count': 1,
            # 添加库存信息
            'cost': 0,
            'from_inventory': {},
            'need_print': {} if inventory is None else {f"{x}x{y}": 1}
        }

    # 如果有库存，收集所有方案并评分
    if inventory:
        all_schemes = find_all_schemes(x, y)
        scored_schemes = []

        for scheme in all_schemes:
            cost, from_inv, need_print = calculate_print_cost(
                scheme['tiles'], inventory, copies
            )

            # 计算独特尺寸和瓦片数
            unique_sizes = len(set(scheme['tiles']))
            total_tiles = len(scheme['tiles'])

            # 计算均衡度
            balance = calc_scheme_balance(scheme['x_splits'], scheme['y_splits'])

            scored_schemes.append({
                'scheme': scheme,
                'cost': cost,
                'from_inventory': from_inv,
                'need_print': need_print,
                'unique_sizes': unique_sizes,
                'total_tiles': total_tiles,
                'balance': balance
            })

        # 多维度排序：成本 -> 独特尺寸 -> 瓦片数 -> 均衡度
        scored_schemes.sort(key=SCHEME_SORT_KEY)

        best_scored = scored_schemes[0]

        # 计算最佳无库存方案作为基准（包括旋转）
        baseline_cost = float('inf')
        baseline_scheme = None
        for scheme in all_schemes:
            cost_no_inv, _, _ = calculate_print_cost(scheme['tiles'], {}, copies)
            if cost_no_inv < baseline_cost:
                baseline_cost = cost_no_inv
                baseline_scheme = scheme

        # 也检查旋转后的方案
        if x != y:
            rotated_schemes = find_all_schemes(y, x)
            for scheme in rotated_schemes:
                normalized = normalize_tiles(scheme['tiles'])
                if not validate_tiles(normalized):
                    continue
                cost_no_inv, _, _ = calculate_print_cost(normalized, {}, copies)
                if cost_no_inv < baseline_cost:
                    baseline_cost = cost_no_inv
                    baseline_scheme = scheme
                    # 保存旋转后的瓦片
                    baseline_normalized = normalized

        # 如果使用库存后的成本高于基准成本，选择不使用库存的方案
        if best_scored['cost'] > baseline_cost:
            # 使用基准方案
            if baseline_scheme:
                # 检查是否是旋转后的方案
                if 'baseline_normalized' in dir() and baseline_scheme == rotated_schemes[-1]:
                    tiles = baseline_normalized
                else:
                    tiles = baseline_scheme['tiles']

                tile_counts = {}
                for w, h in tiles:
                    key = f"{w}x{h}"
                    tile_counts[key] = tile_counts.get(key, 0) + 1

                best = {
                    'x_parts': baseline_scheme.get('y_parts', 1) if 'baseline_normalized' in dir() else baseline_scheme.get('x_parts', 1),
                    'y_parts': baseline_scheme.get('x_parts', 1) if 'baseline_normalized' in dir() else baseline_scheme.get('y_parts', 1),
                    'x_splits': baseline_scheme.get('y_splits', tiles) if 'baseline_normalized' in dir() else baseline_scheme.get('x_splits', []),
                    'y_splits': baseline_scheme.get('x_splits', []) if 'baseline_normalized' in dir() else baseline_scheme.get('y_splits', []),
                    'tiles': tiles,
                    'cost': baseline_cost,
                    'from_inventory': {},
                    'need_print': tile_counts,
                    'unique_sizes': len(set(tiles)),
                    'tile_count': len(tiles),
                    'balance': calc_scheme_balance(baseline_scheme.get('y_splits', []), baseline_scheme.get('x_splits', [])) if 'baseline_normalized' not in dir() else calc_scheme_balance(baseline_scheme.get('x_splits', []), baseline_scheme.get('y_splits', []))
                }
            else:
                best = best_scored['scheme'].copy()
                best['cost'] = best_scored['cost']
                best['from_inventory'] = best_scored['from_inventory']
                best['need_print'] = best_scored['need_print']
                best['unique_sizes'] = best_scored['unique_sizes']
                best['tile_count'] = best_scored['total_tiles']
                best['balance'] = best_scored['balance']
        else:
            best = best_scored['scheme'].copy()
            best['cost'] = best_scored['cost']
            best['from_inventory'] = best_scored['from_inventory']
            best['need_print'] = best_scored['need_print']
            best['unique_sizes'] = best_scored['unique_sizes']
            best['tile_count'] = best_scored['total_tiles']
            best['balance'] = best_scored['balance']

        # 旋转对称检查：当有库存时也需要考虑旋转
        if x != y:
            # 旋转输入，收集旋转后的所有方案
            rotated_schemes = find_all_schemes(y, x)
            scored_rotated = []

            for scheme in rotated_schemes:
                # 规范化瓦片
                normalized = normalize_tiles(scheme['tiles'])

                # 检查旋转后的瓦片是否有效
                if not validate_tiles(normalized):
                    continue

                cost, from_inv, need_print = calculate_print_cost(
                    normalized, inventory, copies
                )

                unique_sizes = len(set(normalized))
                total_tiles = len(normalized)
                balance = calc_scheme_balance(scheme['y_splits'], scheme['x_splits'])

                scored_rotated.append({
                    'scheme': scheme,
                    'rotated_tiles': normalized,
                    'cost': cost,
                    'from_inventory': from_inv,
                    'need_print': need_print,
                    'unique_sizes': unique_sizes,
                    'total_tiles': total_tiles,
                    'balance': balance
                })

            if scored_rotated:
                # 排序旋转后的方案
                scored_rotated.sort(key=SCHEME_SORT_KEY)

                best_rotated = scored_rotated[0]

                # 比较原方案和旋转方案
                if (best_rotated['cost'] < best['cost'] or
                    (best_rotated['cost'] == best['cost'] and best_rotated['unique_sizes'] < best['unique_sizes']) or
                    (best_rotated['cost'] == best['cost'] and best_rotated['unique_sizes'] == best['unique_sizes'] and best_rotated['total_tiles'] < best['tile_count']) or
                    (best_rotated['cost'] == best['cost'] and best_rotated['unique_sizes'] == best['unique_sizes'] and best_rotated['total_tiles'] == best['tile_count'] and best_rotated['balance'] < best['balance'])):

                    # 使用旋转后的方案
                    best = {
                        'x_parts': scheme['y_parts'],
                        'y_parts': scheme['x_parts'],
                        'x_splits': scheme['y_splits'],
                        'y_splits': scheme['x_splits'],
                        'tiles': best_rotated['rotated_tiles'],
                        'unique_sizes': best_rotated['unique_sizes'],
                        'tile_count': best_rotated['total_tiles'],
                        'balance': best_rotated['balance'],
                        'cost': best_rotated['cost'],
                        'from_inventory': best_rotated['from_inventory'],
                        'need_print': best_rotated['need_print']
                    }

        # 如果有库存但成本 > 0，尝试重新规划以使用更多库存
        if inventory and best.get('cost', 0) > 0:
            replanned = replan_with_inventory(
                best['tiles'], inventory, copies, grid=(x, y)
            )
            if replanned and replanned.get('cost', 999) < best.get('cost', 999):
                best.update({
                    'tiles': replanned['tiles'],
                    'cost': replanned['cost'],
                    'from_inventory': replanned['from_inventory'],
                    'need_print': replanned['need_print'],
                    'unique_sizes': len(set(replanned['tiles'])),
                    'tile_count': len(replanned['tiles'])
                })

        return best

    # 无库存时使用原始逻辑
    best = _find_best_scheme_impl(x, y, verbose)

    # 如果 x != y，搜索旋转后的方向并比较
    if x != y:
        rotated = _find_best_scheme_impl(y, x, verbose)
        if rotated is not None:
            # 规范化瓦片
            normalized_tiles = normalize_tiles(rotated['tiles'])

            rotated_swapped = {
                'x_parts': rotated['y_parts'],
                'y_parts': rotated['x_parts'],
                'x_splits': rotated['y_splits'],
                'y_splits': rotated['x_splits'],
                'tiles': normalized_tiles,
                'unique_sizes': rotated['unique_sizes'],
                'tile_count': rotated['tile_count'],
                'balance': rotated['balance']
            }

            # 验证规范化后的瓦片是否有效
            rotated_valid = validate_tiles(normalized_tiles)

            # 比较：只有当旋转结果更优且有效时才采用
            if rotated_valid and (best is None or \
               rotated_swapped['unique_sizes'] < best['unique_sizes'] or \
               (rotated_swapped['unique_sizes'] == best['unique_sizes'] and rotated_swapped['tile_count'] < best['tile_count']) or \
               (rotated_swapped['unique_sizes'] == best['unique_sizes'] and rotated_swapped['tile_count'] == best['tile_count'] and rotated_swapped['balance'] < best['balance'])):
                best = rotated_swapped

    return best


def _find_best_scheme_impl(x, y, verbose=False):
    """find_best_scheme 的实际实现"""
    best = None
    candidates_checked = 0

    # 从最少分割开始尝试
    for x_parts in range(2, 8):
        for y_parts in range(1, 5):
            total_tiles = x_parts * y_parts
            if total_tiles > 20:
                continue

            # 生成有效的 X 分割
            x_splits = split_with_limit(x, x_parts, MAX_X)
            if not x_splits:
                continue

            # 生成有效的 Y 分割
            y_splits = split_with_limit(y, y_parts, MAX_Y)
            if not y_splits:
                continue

            # 遍历所有组合，找最优
            for xs in x_splits:
                for ys in y_splits:
                    candidates_checked += 1

                    # 计算瓦片
                    tiles = []
                    unique = set()
                    valid = True

                    for xd in xs:
                        for yd in ys:
                            if not validate_tile(xd, yd):
                                valid = False
                                break
                            tiles.append((xd, yd))
                            unique.add((xd, yd))

                    if not valid:
                        continue

                    balance = calc_scheme_balance(xs, ys)

                    scheme = {
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': tiles,
                        'unique_sizes': len(unique),
                        'tile_count': len(tiles),
                        'balance': balance
                    }

                    # 优先级: 1)独特尺寸最少 2)瓦片数最少 3)均衡度最好
                    if best is None or \
                       (len(unique) < best['unique_sizes']) or \
                       (len(unique) == best['unique_sizes'] and len(tiles) < best['tile_count']) or \
                       (len(unique) == best['unique_sizes'] and len(tiles) == best['tile_count'] and balance < best['balance']):
                        best = scheme
                        if verbose:
                            print(f"  [DEBUG] New best: {len(unique)} sizes, {len(tiles)} tiles, balance={balance:.2f}")

                    # 找到最优解：1种尺寸，停止搜索
                    if len(unique) == 1:
                        if verbose:
                            print(f"  [DEBUG] Checked {candidates_checked} candidates")
                        return best

    if verbose:
        print(f"  [DEBUG] Checked {candidates_checked} candidates, no perfect solution")
    return best


def find_all_schemes(x, y):
    """生成某个抽屉的所有有效分割方案

    注意：旋转方案由 find_best_scheme 单独处理
    """
    # 先检查是否需要分割
    if validate_tile(x, y):
        return [{
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
        }]

    all_schemes = []

    # 遍历所有分割组合，包括 x_parts=1 和 y_parts=1 的情况
    for x_parts in range(1, 8):
        for y_parts in range(1, 5):
            total_tiles = x_parts * y_parts
            if total_tiles > 20:
                continue

            x_splits = split_with_limit(x, x_parts, MAX_X)
            if not x_splits:
                continue

            y_splits = split_with_limit(y, y_parts, MAX_Y)
            if not y_splits:
                continue

            for xs in x_splits:
                for ys in y_splits:
                    tiles = []
                    valid = True
                    for xd in xs:
                        for yd in ys:
                            if not validate_tile(xd, yd):
                                valid = False
                                break
                            tiles.append((xd, yd))

                    if not valid:
                        continue

                    all_schemes.append({
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': tiles,
                    })

    return all_schemes


def calculate_filament_and_time(cells, stacks):
    """计算耗材和打印时间"""
    main = cells * FILAMENT_MAIN_PER_CELL * stacks
    support = cells * FILAMENT_SUPPORT_PER_CELL * stacks
    time_min = cells * PRINT_TIME_PER_CELL * stacks
    return main, support, time_min


# 换料惩罚时间（分钟）
SWAP_PENALTY = 60


def calculate_print_cost(tiles: list[tuple[int, int]], inventory: dict[str, int], copies: int = 1) -> tuple[int, dict, dict]:
    """
    计算打印成本及库存匹配情况

    Args:
        tiles: 瓦片列表 [(w,h), ...]
        inventory: 库存字典 {"6x7": 3, ...}
        copies: 打印份数

    Returns: (cost, from_inventory, need_print)
        - cost: 总成本（分钟），0 表示完全使用库存
        - from_inventory: 从库存取的瓦片 {"6x7": 2, ...}
        - need_print: 需要新打印的瓦片 {"6x7": 1, ...}
    """
    # 统计每种尺寸的需求
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}

    # 计算库存匹配
    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    # 计算需打印部分的成本
    total_time = 0
    total_prints = len(need_print)  # 每个独特尺寸需要一次打印

    for key, count in need_print.items():
        if count > 0:
            w, h = map(int, key.split('x'))
            cells = w * h
            _, _, time_min = calculate_filament_and_time(cells, count)
            total_time += time_min

    # 加上换料惩罚（每次打印间隔惩罚）
    if total_prints > 1:
        total_time += (total_prints - 1) * SWAP_PENALTY

    return total_time, from_inventory, need_print


def replan_with_inventory(tiles: list[tuple[int, int]], inventory: dict[str, int], copies: int = 1, grid: tuple[int, int] = None):
    """
    边缘情况5：当库存尺寸不匹配时，重新规划方案以最大化利用库存

    Args:
        tiles: 原始瓦片需求
        inventory: 可用库存
        copies: 打印份数
        grid: 可选的网格尺寸 (width, height)，如果未提供则从tiles推断

    Returns:
        重新规划后的方案，包含:
        - tiles: 新的瓦片列表
        - from_inventory: 从库存取的瓦片
        - need_print: 需要新打印的瓦片
        - cost: 总成本
        或 None（如果不需要重新规划）
    """
    # 先尝试直接匹配
    direct_cost, from_inventory, need_print = calculate_print_cost(tiles, inventory, copies)

    # 如果直接匹配成本为 0，不需要重新规划
    if direct_cost == 0:
        return None

    # 如果 need_print 为空但 cost > 0，说明库存不足但无法拆分
    if not need_print:
        return None

    # 计算原始成本（无库存）
    original_cost, _, _ = calculate_print_cost(tiles, {}, copies)

    # 确定网格尺寸
    if grid is not None:
        max_w, max_h = grid
    else:
        # 从瓦片列表推断格子尺寸（假设瓦片正好填满抽屉）
        if not tiles:
            return None
        max_w = max(w for w, h in tiles)
        max_h = max(h for w, h in tiles)

    # 找到可用的库存尺寸
    available_sizes = {k: v for k, v in inventory.items() if v > 0}
    if not available_sizes:
        return None

    # 计算原始格子数量
    original_cells = sum(w * h for w, h in tiles)

    # 记录当前最佳方案（原始方案）
    best_plan = {
        'cost': direct_cost,
        'from_inventory': from_inventory,
        'need_print': need_print,
        'tiles': tiles,
    }

    # 遍历每种库存尺寸，尝试找到更好的方案
    for inv_key, inv_count in available_sizes.items():
        # 尝试使用库存瓦片作为约束，找到合适的分割方案
        # 思路：找到包含库存尺寸的方案，且成本更低
        all_schemes = find_all_schemes(max_w, max_h)

        for scheme in all_schemes:
            scheme_tiles = scheme['tiles']
            scheme_cells = sum(w * h for w, h in scheme_tiles)

            # 验证格子数量一致
            if scheme_cells != original_cells:
                continue

            # 计算使用库存的成本
            cost, from_inv, need_p = calculate_print_cost(
                scheme_tiles, inventory, copies
            )

            # 检查是否使用了库存
            if not from_inv:
                continue

            # 检查库存使用是否不超过提供数量
            if sum(from_inv.values()) > inv_count * copies:
                continue

            # 检查成本是否有改善
            if cost < best_plan['cost']:
                best_plan = {
                    'cost': cost,
                    'from_inventory': from_inv,
                    'need_print': need_p,
                    'tiles': scheme_tiles,
                }

    # 如果没有改进，返回 None
    if best_plan['cost'] >= original_cost:
        return None

    return best_plan


def format_time(minutes):
    """格式化打印时间"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h{mins}m"
    return f"{mins}m"


def print_plan(width, depth, scheme, copies=1, verbose=False, inventory=None):
    """打印分割方案

    Args:
        width: 抽屉宽度 (mm)
        depth: 抽屉深度 (mm)
        scheme: 分割方案字典
        copies: 打印份数
        verbose: 是否详细输出
        inventory: 库存字典 {"6x7": 3, ...}，可选
    """
    x, y = get_grid_dimensions(width, depth)

    print("=" * 60)
    print("openGrid 抽屉铺满打印计划")
    print("=" * 60)
    print(f"抽屉尺寸: {width}mm × {depth}mm")
    print(f"有效格子: {x} × {y} = {x * y}格")
    print(f"打印份数: {copies}套")
    print()

    print("--- 分割方案 ---")
    print(f"分割: {scheme['x_parts']}×{scheme['y_parts']}")
    print(f"X方向: {x} = {' + '.join(map(str, scheme['x_splits']))}")
    print(f"Y方向: {y} = {' + '.join(map(str, scheme['y_splits']))}")
    print()

    # 打印排布图
    print("排布:")
    for y_dim in scheme['y_splits']:
        row = ""
        for x_dim in scheme['x_splits']:
            row += f"{x_dim}×{y_dim} "
        print(row)

    print()
    print("--- 瓦片清单 ---")

    # 按尺寸分组统计
    tile_counts = {}
    for w, h in scheme['tiles']:
        key = f"{w}×{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    unique_count = len(tile_counts)
    max_stacks = get_max_stacks()

    # 累计统计
    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0

    for size, count in tile_counts.items():
        w, h = map(int, size.split('×'))
        cells = w * h
        total_stacks = count * copies

        # 检查是否需要分多次打印
        if total_stacks > max_stacks:
            # 分成多次打印
            num_prints = (total_stacks + max_stacks - 1) // max_stacks
            stacks_per_print = total_stacks // num_prints
            remainder = total_stacks % num_prints

            height = stacks_per_print * FULL_THICKNESS

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"{size}: {total_stacks} stack (分{num_prints}次打印: {stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                # 剩余部分
                extra_cells_time = remainder * PRINT_TIME_PER_CELL * cells
                extra_cells_main = remainder * FILAMENT_MAIN_PER_CELL * cells
                extra_cells_support = remainder * FILAMENT_SUPPORT_PER_CELL * cells
                total_time_this = time_per * (num_prints - 1) + extra_cells_time
                total_main_this = main_per * (num_prints - 1) + extra_cells_main
                total_support_this = support_per * (num_prints - 1) + extra_cells_support
                print(f"       耗材: {total_main_this:.1f}g, 时间: {format_time(total_time_this)} ({format_time(time_per)}/次 × {num_prints-1}次 + {format_time(extra_cells_time)})")
            else:
                total_time_this = time_per * num_prints
                print(f"{size}: {total_stacks} stack 分{num_prints}次打印 (每次{stacks_per_print} stack, {height:.0f}mm)")
                print(f"       耗材: {main_per * num_prints:.1f}g, 时间: {format_time(total_time_this)} ({format_time(time_per)}/次 × {num_prints}次)")

            # 累计
            total_main += main_per * num_prints
            total_support += support_per * num_prints
            total_time += time_per * num_prints
            total_prints += num_prints

            if remainder > 0:
                total_main += remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += remainder * FILAMENT_SUPPORT_PER_CELL * cells
                total_time += remainder * PRINT_TIME_PER_CELL * cells
        else:
            height = total_stacks * FULL_THICKNESS
            main_g, support_g, time_min = calculate_filament_and_time(cells, total_stacks)

            print(f"{size}: {total_stacks} stack ({height:.0f}mm)")
            print(f"       耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1

    print()
    print("--- 耗材估算 ---")
    print(f"主耗材: ~{total_main:.0f}g")
    print(f"支撑耗材: ~{total_support:.0f}g")
    print(f"总耗材: ~{total_main + total_support:.0f}g ({copies}份)")

    print()
    print("--- 打印时间估算 ---")
    print(f"预计总时间: ~{format_time(total_time)} ({total_prints}次打印)")

    # 如果有库存信息，显示库存利用情况
    if 'cost' in scheme and scheme['cost'] is not None:
        print()
        print("--- 库存利用 ---")

        # 显示从库存取的瓦片
        from_inv = scheme.get('from_inventory', {})
        if from_inv:
            parts = []
            for key in sorted(from_inv.keys()):
                w, h = key.split('x')
                count = from_inv[key]
                parts.append(f"{w}×{h} ×{count}")
            print(f"从库存: {', '.join(parts)}")

        # 显示需要打印的瓦片
        need_print = scheme.get('need_print', {})
        if need_print:
            parts = []
            for key in sorted(need_print.keys()):
                w, h = key.split('x')
                count = need_print[key]
                parts.append(f"{w}×{h} ×{count}")
            print(f"需打印: {', '.join(parts)} (成本: {format_time(scheme['cost'])})")
        else:
            print("需打印: 无 (成本: 0)")

    print()
    print("--- 安装说明 ---")
    print("1. 打印 STL")
    print("2. 使用连接件组装")
    print("3. 放入抽屉")

    # 如果有库存，重新计算实际打印成本
    actual_time = total_time
    if inventory and scheme.get('tiles'):
        tiles = scheme['tiles']
        actual_cost, from_inv, need_p = calculate_print_cost(tiles, inventory, copies)
        actual_time = actual_cost
        if actual_cost < total_time:
            print()
            print("--- 实际打印成本（已扣除库存） ---")
            print(f"全额打印: {format_time(total_time)}")
            print(f"实际打印: {format_time(actual_cost)} (节省: {format_time(total_time - actual_cost)})")

    return {
        'total_main': total_main,
        'total_support': total_support,
        'total_filament': total_main + total_support,
        'total_time': actual_time,
        'total_prints': total_prints,
        'full_time': total_time  # 全额打印时间（未扣除库存）
    }


def output_json(width, depth, scheme, copies, stats):
    """输出 JSON 格式"""
    # 按尺寸分组
    tile_counts = {}
    for w, h in scheme['tiles']:
        key = f"{w}×{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    tiles_list = []
    for size, count in tile_counts.items():
        w, h = map(int, size.split('×'))
        tiles_list.append({
            "width": w,
            "height": h,
            "count": count
        })

    output = {
        "drawer": {
            "width": width,
            "depth": depth
        },
        "grid": {
            "x": width // TILE_SIZE,
            "y": depth // TILE_SIZE
        },
        "scheme": {
            "x_parts": scheme['x_parts'],
            "y_parts": scheme['y_parts'],
            "x_splits": scheme['x_splits'],
            "y_splits": scheme['y_splits'],
            "tiles": tiles_list
        },
        "stats": {
            "unique_sizes": scheme['unique_sizes'],
            "total_tiles": scheme['tile_count'],
            "total_filament_g": round(stats['total_filament']),
            "total_time_min": int(stats['total_time']),
            "total_prints": stats['total_prints'],
            "full_time_min": int(stats.get('full_time', stats['total_time']))
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


def list_presets():
    """列出所有预设"""
    print("可用预设:")
    for name, (w, h, desc) in PRESETS.items():
        print(f"  {name:12} {w:4}×{h:4}mm - {desc}")


def parse_batch_input(input_str):
    """ '解析批量输入，如265x365:2 325x365:2 315x365:2'

    支持格式:
    - 265x365:2  (宽度x深度:份数)
    - 265 365 2 (宽度 深度 份数)
    """
    items = []

    # 首先尝试解析 "宽x深:份数" 格式
    import re
    # 匹配 "265x365:2" 或 "265x365x2" 格式
    pattern = r'(\d+)[x×](\d+)[x:(\d+)]?'

    # 按空格分割
    parts = input_str.strip().split()

    for part in parts:
        # 尝试匹配 "宽x深:份数" 或 "宽x深x份数" 格式
        match = re.match(r'(\d+)[x×](\d+)(?:[x:](\d+))?', part)
        if match:
            width = int(match.group(1))
            depth = int(match.group(2))
            copies = int(match.group(3)) if match.group(3) else 1
            items.append((width, depth, copies))
            continue

        # 尝试直接匹配数字（作为宽度）
        if part.isdigit():
            # 可能是单维度，需要更多信息
            continue

    # 如果上面的解析失败，尝试 "宽 深 份数" 格式
    if not items and len(parts) >= 3:
        try:
            width = int(parts[0])
            depth = int(parts[1])
            copies = int(parts[2])
            items.append((width, depth, copies))
        except:
            pass

    return items


def calculate_single(width, depth, copies=1, verbose=False):
    """计算单个尺寸的分割方案"""
    x, y = get_grid_dimensions(width, depth)

    if x < MIN_TILE or y < MIN_TILE:
        return None

    scheme = find_best_scheme(x, y, verbose)

    if not scheme:
        return None

    return {
        'width': width,
        'depth': depth,
        'copies': copies,
        'grid': (x, y),
        'scheme': scheme
    }


def merge_and_optimize(batch_results):
    """合并多个尺寸的方案，优化共用尺寸

    策略:
    1. 收集所有需要的瓦片尺寸
    2. 统计每个尺寸的总需求数量
    3. 输出合并后的打印计划
    """
    # 收集所有瓦片尺寸及其需求
    all_tiles = {}  # {(w, h): {drawer: count, total: total_count}}

    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']

        # 统计该尺寸的瓦片
        tile_counts = {}
        for w, h in scheme['tiles']:
            key = (w, h)
            tile_counts[key] = tile_counts.get(key, 0) + 1

        # 乘以份数
        for (w, h), count in tile_counts.items():
            if (w, h) not in all_tiles:
                all_tiles[(w, h)] = {'total': 0, 'by_drawer': []}

            total_for_drawer = count * copies
            all_tiles[(w, h)]['total'] += total_for_drawer
            all_tiles[(w, h)]['by_drawer'].append({
                'size': f"{width}×{depth}",
                'copies': copies,
                'tiles_per_copy': count,
                'total': total_for_drawer
            })

    return all_tiles


def calculate_total_prints(batch_results, schemes):
    """计算给定方案组合的总打印次数

    Args:
        batch_results: 批量计算结果列表，每个元素包含 width, depth, copies, scheme
        schemes: 对应的分割方案列表

    Returns:
        (total_prints, details): 总打印次数和每个尺寸的详细信息
    """
    # 合并所有瓦片
    all_tiles = {}
    for result, scheme in zip(batch_results, schemes):
        if result is None or scheme is None:
            continue
        copies = result['copies']
        for w, h in scheme['tiles']:
            key = (w, h)
            if key not in all_tiles:
                all_tiles[key] = 0
            all_tiles[key] += copies

    # 计算每个尺寸的打印次数
    max_stacks = get_max_stacks()
    total_prints = 0
    details = {}

    for (w, h), stacks in all_tiles.items():
        prints_needed = (stacks + max_stacks - 1) // max_stacks
        total_prints += prints_needed
        details[(w, h)] = {
            'stacks': stacks,
            'print_count': prints_needed
        }

    return total_prints, details


def calculate_batch_cost_with_inventory(schemes, batch_results, inventory):
    """计算批量方案的总成本，正确追踪库存使用

    正确的逻辑：按节省成本排序，优先给节省多的抽屉分配库存

    Args:
        schemes: 分割方案列表
        batch_results: 批量计算结果列表
        inventory: 库存字典 {"6x7": 3, ...}

    Returns:
        (total_cost, inventory_usage): 总成本和每个抽屉的库存使用情况
    """
    if not inventory:
        return sum(
            calculate_print_cost(s['tiles'], {}, batch_results[i].get('copies', 1))[0]
            for i, s in enumerate(schemes) if s
        ), {}

    # 第一步：计算每个抽屉不使用库存和使用库存的成本差异
    # 按节省成本从高到低排序
    savings = []
    for i, scheme in enumerate(schemes):
        if scheme is None:
            continue

        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        # 不使用库存的成本
        cost_no_inv, _, _ = calculate_print_cost(scheme['tiles'], {}, copies)
        # 使用库存的成本
        cost_with_inv, from_inv, _ = calculate_print_cost(scheme['tiles'], inventory, copies)

        saved = cost_no_inv - cost_with_inv
        savings.append({
            'index': i,
            'scheme': scheme,
            'cost_no_inv': cost_no_inv,
            'cost_with_inv': cost_with_inv,
            'from_inv': from_inv,
            'saved': saved
        })

    # 按节省成本从高到低排序
    savings.sort(key=lambda x: x['saved'], reverse=True)

    # 第二步：按排序分配库存
    remaining_inv = dict(inventory)
    total_cost = 0
    inventory_usage = {}

    for item in savings:
        i = item['index']
        scheme = item['scheme']
        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        # 检查库存是否足够
        can_use = True
        for key, needed in item['from_inv'].items():
            if remaining_inv.get(key, 0) < needed:
                can_use = False
                break

        if can_use:
            # 使用库存
            cost = item['cost_with_inv']
            for key, used in item['from_inv'].items():
                remaining_inv[key] -= used
            inventory_usage[i] = item['from_inv']
        else:
            # 库存不足，不能使用库存
            cost = item['cost_no_inv']
            inventory_usage[i] = {}

        total_cost += cost

    return total_cost, inventory_usage


def optimize_batch_global(batch_results, inventory=None):
    """贪心 + 局部搜索优化

    Args:
        batch_results: 批量计算结果列表
        inventory: 可选库存字典 {"6x7": 3, ...}
    """
    if not batch_results:
        return None

    # 步骤1：各自找最优作为初始解
    # 注意：不传inventory，让每个抽屉选择最优的瓦片方案（与库存无关）
    # 库存分配由 calculate_batch_cost_with_inventory 统一处理
    initial_schemes = []
    for i, r in enumerate(batch_results):
        if r is None:
            initial_schemes.append(None)
            continue
        x, y = r['grid']
        copies = r.get('copies', 1)
        # 不传 inventory，每个抽屉选择成本最低的方案
        scheme = find_best_scheme(x, y, inventory=None, copies=copies)
        initial_schemes.append(scheme)

    # 计算初始解的成本（打印次数或库存成本）
    if inventory:
        initial_cost, _ = calculate_batch_cost_with_inventory(
            initial_schemes, batch_results, inventory
        )
    else:
        initial_total, _ = calculate_total_prints(batch_results, initial_schemes)
        initial_cost = initial_total

    # 步骤2：为每个抽屉生成所有方案
    all_options = []
    for result in batch_results:
        if result is None:
            all_options.append([None])
            continue
        x, y = result['grid']
        schemes = find_all_schemes(x, y)
        all_options.append(schemes)

    # 步骤3：找最优组合
    best_schemes = initial_schemes.copy()
    best_cost = initial_cost

    # 对每个抽屉，尝试其他方案，看能否减少成本
    for i, options in enumerate(all_options):
        if len(options) <= 1:
            continue

        for option in options:
            # 构建新组合
            test_schemes = best_schemes.copy()
            test_schemes[i] = option

            # 检查是否有效（不能有 None）
            if None in test_schemes:
                continue

            # 计算新组合的成本（使用新的批量成本计算函数）
            if inventory:
                total, _ = calculate_batch_cost_with_inventory(
                    test_schemes, batch_results, inventory
                )
            else:
                total, _ = calculate_total_prints(batch_results, test_schemes)

            if total < best_cost:
                best_schemes = test_schemes
                best_cost = total

    # 返回优化结果
    # 重新计算最终的库存使用情况，并更新到每个方案中
    if inventory:
        final_cost, final_inv_usage = calculate_batch_cost_with_inventory(
            best_schemes, batch_results, inventory
        )
        # 更新每个方案的 from_inventory 字段
        for i, scheme in enumerate(best_schemes):
            if scheme is not None and i in final_inv_usage:
                scheme['from_inventory'] = final_inv_usage[i]
    else:
        final_cost = best_cost

    return {
        'schemes': best_schemes,
        'total_prints': best_cost if not inventory else None,
        'cost': final_cost if inventory else None,
        'initial_prints': initial_cost if not inventory else None,
        'initial_cost': initial_cost if inventory else None,
        'improved': best_cost < initial_cost
    }


def print_batch_plan(batch_results, merged_tiles, inventory=None, json_output=False):
    """打印批量打印计划

    Args:
        batch_results: 批量计算结果列表
        merged_tiles: 合并后的瓦片字典
        inventory: 库存字典
        json_output: 是否输出 JSON 格式
    """
    # 如果是 JSON 模式，只计算统计信息不打印
    if json_output:
        max_stacks = get_max_stacks()
        sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

        total_main = 0
        total_support = 0
        total_time = 0
        total_prints = 0
        tiles_output = []

        # 记录库存使用情况
        from_inventory = {}
        need_print_tiles = {}

        for (w, h), info in sorted_tiles:
            cells = w * h
            total_stacks = info['total']

            # 检查库存
            key = f"{w}x{h}"
            available = inventory.get(key, 0) if inventory else 0
            to_print = max(0, total_stacks - available)

            # 记录库存使用
            if available > 0:
                from_inventory[key] = min(available, total_stacks)
            if to_print > 0:
                need_print_tiles[key] = to_print

            # 计算实际打印成本（基于需要打印的数量）
            if to_print > max_stacks:
                num_prints = (to_print + max_stacks - 1) // max_stacks
                stacks_per_print = to_print // num_prints
                remainder = to_print % num_prints

                height = stacks_per_print * FULL_THICKNESS
                main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

                if remainder > 0:
                    total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                    total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells
                    time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                    total_time += time_main
                else:
                    total_main += main_per * num_prints
                    total_support += support_per * num_prints
                    total_time += time_per * num_prints

                total_prints += num_prints
            elif to_print > 0:
                main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)
                total_main += main_g
                total_support += support_g
                total_time += time_min
                total_prints += 1
            # to_print == 0 means completely covered by inventory

            tiles_output.append({
                "width": w,
                "height": h,
                "stacks": total_stacks,
                "prints": total_prints if to_print > 0 else 0,
                "from_inventory": from_inventory.get(key, 0),
                "to_print": to_print
            })

        # 输出 JSON
        output = {
            "drawers": [
                {
                    "width": r['width'],
                    "depth": r['depth'],
                    "copies": r['copies']
                }
                for r in batch_results if r
            ],
            "tiles": tiles_output,
            "stats": {
                "total_filament_g": round(total_main + total_support),
                "total_time_min": int(total_time),
                "total_prints": total_prints
            }
        }

        # 如果有库存，添加库存信息
        if inventory and (from_inventory or need_print_tiles):
            output["inventory_usage"] = {
                "from_inventory": from_inventory,
                "need_print": need_print_tiles
            }

        print(json.dumps(output, indent=2, ensure_ascii=False))
        return {
            'total_main': total_main,
            'total_support': total_support,
            'total_filament': total_main + total_support,
            'total_time': total_time,
            'total_prints': total_prints
        }

    # 人类可读模式
    print("=" * 70)
    print("openGrid 批量打印计划 - 合并优化版")
    print("=" * 70)

    # 先打印每个尺寸的分割方案
    print("\n--- 各尺寸分割方案 ---")
    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']
        x, y = result['grid']

        print(f"\n{width}×{depth}mm × {copies}份:")
        print(f"  格子: {x} × {y}")
        print(f"  分割: {scheme['x_parts']}×{scheme['y_parts']}")
        print(f"  X: {' + '.join(map(str, scheme['x_splits']))}")
        print(f"  Y: {' + '.join(map(str, scheme['y_splits']))}")

    # 打印合并后的瓦片清单
    print("\n" + "=" * 70)
    print("--- 合并后的瓦片清单（可一起打印）---")
    print("=" * 70)

    max_stacks = get_max_stacks()

    # 按尺寸排序
    sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0

    for (w, h), info in sorted_tiles:
        cells = w * h
        total_stacks = info['total']

        print(f"\n{w}×{h} 格 ({w*28}mm × {h*28}mm):")

        # 显示来源
        for src in info['by_drawer']:
            print(f"  来源: {src['size']} × {src['copies']}份 = {src['total']} stack")

        # 检查库存
        key = f"{w}x{h}"
        available = inventory.get(key, 0) if inventory else 0
        to_print = max(0, total_stacks - available)

        # 显示库存使用情况
        if inventory:
            if available > 0:
                print(f"  库存: {min(available, total_stacks)}")
            if to_print > 0:
                print(f"  需打印: {to_print}")
            else:
                print(f"  需打印: 无 (完全使用库存)")

        # 计算打印次数（基于实际需要打印的数量）
        if to_print > max_stacks:
            num_prints = (to_print + max_stacks - 1) // max_stacks
            stacks_per_print = to_print // num_prints
            remainder = to_print % num_prints

            height = stacks_per_print * FULL_THICKNESS

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"  打印: {num_prints}次 ({stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                # 累计
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells

                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                print(f"  打印: {num_prints}次 (每次{stacks_per_print} stack, {height:.0f}mm)")
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        elif to_print > 0:
            height = to_print * FULL_THICKNESS
            main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)

            print(f"  打印: 1次 ({to_print} stack, {height:.0f}mm)")
            print(f"    耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1
        # else: to_print == 0 means completely covered by inventory, no print needed

    # 打印统计
    print("\n" + "=" * 70)
    print("--- 总计 ---")
    print("=" * 70)
    print(f"总耗材: ~{total_main + total_support:.0f}g")
    print(f"  主耗材: ~{total_main:.0f}g")
    print(f"  支撑耗材: ~{total_support:.0f}g")
    print(f"总打印次数: {total_prints}次")
    print(f"总打印时间: ~{format_time(total_time)}")

    return {
        'total_main': total_main,
        'total_support': total_support,
        'total_filament': total_main + total_support,
        'total_time': total_time,
        'total_prints': total_prints
    }


def batch_mode(input_str, verbose=False, inventory=None, json_output=False):
    """批量计算模式

    Args:
        input_str: 输入字符串
        verbose: 是否详细输出
        inventory: 可选库存字典 {"6x7": 3, ...}
        json_output: 是否输出 JSON 格式
    """
    import re

    # 解析输入
    # 支持格式: "265x365:2 325x365:2" 或 "265 365 2 325 365 2"
    items = []

    # 方法1: 尝试 "宽x深:份数" 格式
    pattern = r'(\d+)[x×](\d+)(?::(\d+))?'
    matches = re.findall(pattern, input_str)

    if matches:
        for m in matches:
            width = int(m[0])
            depth = int(m[1])
            copies = int(m[2]) if m[2] else 1
            items.append((width, depth, copies))

    # 方法2: 如果解析失败，尝试空格分隔
    if not items:
        parts = input_str.split()
        # 尝试每三个一组
        i = 0
        while i + 2 < len(parts):
            try:
                width = int(parts[i])
                depth = int(parts[i+1])
                copies = int(parts[i+2])
                items.append((width, depth, copies))
                i += 3
            except:
                break

    if not items:
        print("无法解析输入格式")
        print("支持的格式:")
        print("  265x365:2 325x365:2 315x365:2")
        print("  265x365 325x365 315x365 (默认每项1份)")
        print("  265 365 2 325 365 2 315 365 2")
        return

    # 输出调试信息到 stderr（如果需要）
    # JSON 模式下不输出任何调试信息
    def _print(msg):
        if json_output:
            return  # JSON 模式下不打印任何内容
        else:
            print(msg)

    _print(f"解析到 {len(items)} 个尺寸:")
    for w, d, c in items:
        _print(f"  {w}×{d}mm × {c}份")

    # 如果有库存，显示库存信息
    if inventory:
        _print(f"库存: {inventory}")
    _print("")

    # 计算每个尺寸的分割方案
    batch_results = []
    for width, depth, copies in items:
        result = calculate_single(width, depth, copies, verbose)
        if result:
            batch_results.append(result)
        else:
            _print(f"警告: {width}×{depth}mm 无法生成有效方案")

    if not batch_results:
        _print("错误: 没有有效的尺寸")
        return

    # 根据是否有库存选择不同的优化方式
    if inventory:
        # 使用全局优化（带库存）
        optimized = optimize_batch_global(batch_results, inventory=inventory)
        # 更新 batch_results 中的 schemes 为优化后的方案
        if optimized and 'schemes' in optimized:
            for i, scheme in enumerate(optimized['schemes']):
                if i < len(batch_results) and scheme:
                    batch_results[i]['scheme'] = scheme
        # 始终使用 merge_and_optimize 获取合并的瓦片
        merged = merge_and_optimize(batch_results)
    else:
        # 简单的合并优化
        merged = merge_and_optimize(batch_results)

    # 打印计划
    stats = print_batch_plan(batch_results, merged, inventory=inventory, json_output=json_output)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='openGrid 抽屉分割计算器 - 优化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 split_calc.py 485 425            # 指定尺寸
  python3 split_calc.py 485 425 -c 3       # 指定份数
  python3 split_calc.py -p klean           # 使用预设
  python3 split_calc.py 485 425 -j         # JSON 输出

  # 批量模式（自动合并优化）
  python3 split_calc.py -b "265x365:2 325x365:2 315x365:2"
  python3 split_calc.py -b "265x365 325x365 315x365"
  python3 split_calc.py -b "265 365 2 325 365 2 315 365 2"

预设尺寸:
  klean       Klean件盒 270×170mm
  ikea-sunda  IKEA Sunda 360×500mm
  ikea-kal    IKEA KAL 360×500mm
  ikea-alex   IKEA Alex 360×500mm
  standard    标准抽屉 400×400mm
        """
    )

    parser.add_argument('width', nargs='?', type=int, help='抽屉宽度(mm)')
    parser.add_argument('depth', nargs='?', type=int, help='抽屉深度(mm)')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数 (默认1)')
    parser.add_argument('-p', '--preset', type=str, help='预设尺寸 (klean, ikea-sunda, ikea-kal, ikea-alex, standard, small, medium, large)')
    parser.add_argument('-b', '--batch', type=str, help='批量计算: "265x365:2 325x365:2" 或 "265 365 2 325 365 2"')
    parser.add_argument('-i', '--inventory', type=str, help='库存文件路径 (JSON格式)')
    parser.add_argument('-j', '--json', action='store_true', help='JSON 格式输出')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--list-presets', action='store_true', help='列出所有预设')
    args = parser.parse_args()

    # 读取库存文件
    inventory = None
    if args.inventory:
        import json as json_module
        try:
            with open(args.inventory, 'r', encoding='utf-8') as f:
                data = json_module.load(f)
                inventory = data.get('inventory', {})
                if args.verbose:
                    print(f"[DEBUG] 加载库存: {inventory}")
        except FileNotFoundError:
            print(f"错误: 库存文件不存在: {args.inventory}")
            sys.exit(1)
        except json_module.JSONDecodeError as e:
            print(f"错误: 库存文件格式错误: {e}")
            sys.exit(1)

    # 批量模式处理
    if args.batch:
        batch_mode(args.batch, args.verbose, inventory=inventory, json_output=args.json)
        return

    # 列出预设
    if args.list_presets:
        list_presets()
        return

    # 无参数时显示帮助
    if args.width is None and args.preset is None:
        parser.print_help()
        sys.exit(0)

    # 预设模式
    if args.preset:
        if args.preset not in PRESETS:
            print(f"错误: 未知预设 '{args.preset}'")
            print("\n可用预设:")
            list_presets()
            sys.exit(1)
        width, depth, _ = PRESETS[args.preset]
        copies = args.copies
    else:
        width = args.width
        depth = args.depth
        copies = args.copies

    # 验证参数
    if width is None or depth is None:
        print("错误: 请提供抽屉尺寸或使用预设")
        parser.print_help()
        sys.exit(1)

    if width < 50 or depth < 50:
        print("错误: 尺寸太小")
        sys.exit(1)

    if args.verbose:
        print(f"[DEBUG] Input: {width}mm × {depth}mm, copies={copies}")

    x, y = get_grid_dimensions(width, depth)

    print(f"输入: {width}mm × {depth}mm")
    print(f"格子: {x} × {y}")
    print()

    if x < MIN_TILE or y < MIN_TILE:
        print("错误: 抽屉尺寸太小，无法放置最小瓦片")
        sys.exit(1)

    scheme = find_best_scheme(x, y, args.verbose, inventory=inventory)

    if not scheme:
        print("错误: 无法生成有效方案!")
        sys.exit(1)

    print(f"最优: {scheme['unique_sizes']}种尺寸, {scheme['tile_count']}块瓦片")
    print()

    stats = print_plan(width, depth, scheme, copies, args.verbose, inventory=inventory)

    if args.json:
        output_json(width, depth, scheme, copies, stats)

if __name__ == "__main__":
    from config import ensure_initialized, reload_config
    ensure_initialized()
    reload_config()
    main()
