#!/usr/bin/env python3
"""
openGrid 库存管理模块
管理 openGrid tile 的库存，支持入库、扣库、撤销操作。
"""

import json
import os
import sys
from datetime import datetime

INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')


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
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 inventory.py list              查看库存")
        print("  python3 inventory.py add 7x5:6 10x5:3  入库")
        print("  python3 inventory.py deduct 7x5:3       扣库")
        print("  python3 inventory.py undo               撤销上次操作")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        print_inventory()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("用法: python3 inventory.py add 7x5:6 10x5:3")
            sys.exit(1)
        items = parse_items(sys.argv[2:])
        result = add_inventory(items, reason="手动入库")
        print("入库完成:")
        for key, count in items.items():
            print(f"  {key}: +{count}")
        print_inventory()
    elif cmd == "deduct":
        if len(sys.argv) < 3:
            print("用法: python3 inventory.py deduct 7x5:3")
            sys.exit(1)
        items = parse_items(sys.argv[2:])
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
