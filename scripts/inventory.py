#!/usr/bin/env python3
"""
openGrid 库存管理模块
管理 openGrid tile 的库存，支持入库、扣库、撤销操作。

用法:
    python3 inventory.py list                  查看库存
    python3 inventory.py add 7x5:6 10x5:3   入库
    python3 inventory.py deduct 7x5:3         扣库
    python3 inventory.py undo                 撤销上次操作

    # 使用自定义库存文件
    python3 inventory.py -f test.json list
    python3 inventory.py --file test.json add 6x6:5
"""

import json
import os
import sys
import argparse
from datetime import datetime

DEFAULT_INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')
INVENTORY_FILE = DEFAULT_INVENTORY_FILE  # 可通过 -f 指定


def set_inventory_file(path):
    """设置当前使用的库存文件路径"""
    global INVENTORY_FILE
    INVENTORY_FILE = path


def _load_data():
    """加载完整的库存数据（含日志）"""
    if not os.path.exists(INVENTORY_FILE):
        return {"inventory": {}, "log": []}
    with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_data(data):
    """保存完整的库存数据"""
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_inventory():
    """返回当前库存 dict，文件不存在时返回空 dict"""
    data = _load_data()
    return data.get("inventory", {})


def save_inventory(inv, log_entry):
    """保存库存并追加日志"""
    data = _load_data()
    data["inventory"] = inv
    log_entry["timestamp"] = datetime.now().isoformat()
    data["log"].append(log_entry)
    _save_data(data)


def add_inventory(items, reason=""):
    """入库，返回更新后库存"""
    inv = load_inventory()
    for key, count in items.items():
        inv[key] = inv.get(key, 0) + count
    save_inventory(inv, {"action": "add", "items": items, "reason": reason})
    return inv


def deduct_inventory(items, reason=""):
    """扣库，返回更新后库存。库存不足时 raise ValueError"""
    inv = load_inventory()
    # 先检查所有项是否够
    for key, count in items.items():
        available = inv.get(key, 0)
        if available < count:
            raise ValueError(
                f"库存不足: {key} 需要 {count}，仅有 {available}"
            )
    # 扣除
    for key, count in items.items():
        inv[key] -= count
        if inv[key] == 0:
            del inv[key]
    save_inventory(inv, {"action": "deduct", "items": items, "reason": reason})
    return inv


def undo_last():
    """撤销最近一次 add/deduct 操作，返回更新后库存"""
    data = _load_data()
    log = data.get("log", [])

    # 找到最近一次非 undo 操作
    last_entry = None
    for entry in reversed(log):
        if entry["action"] != "undo":
            last_entry = entry
            break

    if last_entry is None:
        raise ValueError("没有可撤销的操作")

    inv = data["inventory"]
    items = last_entry["items"]

    if last_entry["action"] == "add":
        # 撤销入库 = 扣除
        for key, count in items.items():
            inv[key] = inv.get(key, 0) - count
            if inv[key] <= 0:
                inv.pop(key, None)
    elif last_entry["action"] == "deduct":
        # 撤销扣库 = 加回
        for key, count in items.items():
            inv[key] = inv.get(key, 0) + count

    # 从日志中移除被撤销的条目
    log.remove(last_entry)

    # 记录 undo 操作
    undo_entry = {
        "action": "undo",
        "items": items,
        "reason": f"撤销 {last_entry['action']}",
        "timestamp": datetime.now().isoformat()
    }
    log.append(undo_entry)

    data["inventory"] = inv
    data["log"] = log
    _save_data(data)
    return inv


def get_inventory_match(tiles, copies, inv):
    """计算方案的库存匹配情况

    Args:
        tiles: list of (w, h) tuples from scheme
        copies: 打印份数
        inv: 当前库存 dict

    Returns:
        {
            "from_inventory": {"7x5": 3},  # 从库存取用
            "need_print": {"10x5": 3},     # 需新打印
            "match_score": 3               # 库存匹配 stack 数
        }
    """
    # 统计每种尺寸的需求
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}
    match_score = 0

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inv.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining
        match_score += used

    return {
        "from_inventory": from_inventory,
        "need_print": need_print,
        "match_score": match_score
    }


def print_inventory():
    """打印当前库存"""
    inv = load_inventory()
    if not inv:
        print("库存为空")
        return
    print("当前库存:")
    for key in sorted(inv.keys()):
        w, h = key.split('x')
        count = inv[key]
        print(f"  {w}×{h}: {count} stack")
    total = sum(inv.values())
    print(f"\n共 {len(inv)} 种尺寸, {total} stack")


def parse_items(args):
    """解析 '7x5:6 10x5:3' 格式"""
    import re
    items = {}
    for arg in args:
        match = re.match(r'(\d+)x(\d+):(\d+)', arg)
        if match:
            key = f"{match.group(1)}x{match.group(2)}"
            items[key] = int(match.group(3))
        else:
            print(f"格式错误: {arg} (应为 WxH:N，如 7x5:6)")
            sys.exit(1)
    return items


def main():
    parser = argparse.ArgumentParser(
        description="openGrid 库存管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 inventory.py list                  查看库存
  python3 inventory.py add 7x5:6 10x5:3   入库
  python3 inventory.py deduct 7x5:3         扣库
  python3 inventory.py undo                 撤销上次操作
  python3 inventory.py -f test.json list     使用自定义库存文件
        """
    )
    parser.add_argument('-f', '--file', type=str, default=None,
                        help='指定库存文件路径 (默认: inventory.json)')
    parser.add_argument('command', nargs='?', help='命令: list, add, deduct, undo')
    parser.add_argument('args', nargs='*', help='命令参数')

    args = parser.parse_args()

    # 设置库存文件
    if args.file:
        set_inventory_file(args.file)

    cmd = args.command

    if cmd is None:
        print("用法:")
        print("  python3 inventory.py list              查看库存")
        print("  python3 inventory.py add 7x5:6 10x5:3 入库")
        print("  python3 inventory.py deduct 7x5:3       扣库")
        print("  python3 inventory.py undo              撤销上次操作")
        print("  python3 inventory.py -f test.json list 使用自定义库存文件")
        sys.exit(1)

    if cmd == "list":
        print_inventory()
    elif cmd == "add":
        if not args.args:
            print("用法: python3 inventory.py add 7x5:6 10x5:3")
            sys.exit(1)
        items = parse_items(args.args)
        result = add_inventory(items, reason="手动入库")
        print("入库完成:")
        for key, count in items.items():
            print(f"  {key}: +{count}")
        print_inventory()
    elif cmd == "deduct":
        if not args.args:
            print("用法: python3 inventory.py deduct 7x5:3")
            sys.exit(1)
        items = parse_items(args.args)
        try:
            result = deduct_inventory(items, reason="手动扣库")
            print("扣库完成:")
            for key, count in items.items():
                print(f"  {key}: -{count}")
            print_inventory()
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
    elif cmd == "undo":
        try:
            result = undo_last()
            print("已撤销上次操作")
            print_inventory()
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
