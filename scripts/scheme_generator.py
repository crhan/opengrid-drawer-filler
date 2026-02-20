#!/usr/bin/env python3
"""多方案生成模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from split_calc import calculate_single
from matcher import get_inventory_match
from inventory import load_inventory


def generate_schemes(width, depth, copies, inventory):
    """生成三种方案

    Returns:
        {
            "math": {...},      # 纯数学优化
            "inventory": {...}, # 库存感知
            "print_limit": {...} # 打印次数约束
        }
    """
    # 方案 A: 纯数学优化
    math_result = calculate_single(width, depth, copies)
    math_scheme = math_result.get("scheme", {}) if math_result else None

    # 方案 B: 库存感知
    inventory_scheme = generate_inventory_aware_scheme(width, depth, copies, inventory)

    # 方案 C: 打印次数约束（暂用数学优化 + 标注）
    print_limit_scheme = math_scheme.copy() if math_scheme else {}
    if print_limit_scheme:
        print_limit_scheme["constraint"] = "max_prints: 3"

    return {
        "math": {
            "name": "纯数学优化",
            "description": "最小化独特尺寸 → 最小瓦片数 → 均衡度最好",
            "scheme": math_scheme
        },
        "inventory": {
            "name": "库存感知",
            "description": "优先使用现有库存瓦片，减少打印量",
            "scheme": inventory_scheme
        },
        "print_limit": {
            "name": "打印次数≤3",
            "description": "限制打印次数的方案",
            "scheme": print_limit_scheme
        }
    }


def generate_inventory_aware_scheme(width, depth, copies, inventory):
    """生成库存感知方案

    算法：
    1. 先找到数学最优方案
    2. 检查库存匹配情况
    3. 如果库存可匹配，调整方案优先使用库存尺寸
    """
    # 基础方案
    result = calculate_single(width, depth, copies)
    base_scheme = result.get("scheme", {}) if result else None

    if not base_scheme:
        return None

    if not inventory:
        return base_scheme

    tiles = base_scheme.get("tiles", [])
    total_tiles = len(tiles)

    # 计算库存匹配
    # tiles 是 [(w,h), (w,h), ...] 格式
    tile_sizes = list(set(tiles))  # 去重
    match_result = get_inventory_match(tile_sizes, copies, inventory)

    match_score = match_result["match_score"]
    if match_score > 0:
        # 有库存匹配，可以优化
        base_scheme["inventory_match"] = match_result

    return base_scheme
