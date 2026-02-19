"""Inventory CRUD operations"""
import json
import os
from datetime import datetime

# Inventory file path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, 'inventory.json')


def _get_inventory_file():
    """Get inventory file path - can be overridden for testing"""
    if hasattr(sys.modules.get('inventory', None), 'INVENTORY_FILE'):
        return sys.modules['inventory'].INVENTORY_FILE
    return INVENTORY_FILE


def _load_data():
    """Load inventory data with log"""
    inv_file = _get_inventory_file()
    if not os.path.exists(inv_file):
        return {"inventory": {}, "log": []}
    with open(inv_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_data(data):
    """Save inventory data"""
    inv_file = _get_inventory_file()
    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_inventory():
    """Return current inventory dict"""
    data = _load_data()
    return data.get("inventory", {})


def save_inventory(inv, log_entry):
    """Save inventory with log entry"""
    data = _load_data()
    data["inventory"] = inv
    log_entry["timestamp"] = datetime.now().isoformat()
    data["log"].append(log_entry)
    _save_data(data)


def add_inventory(items, reason=""):
    """Add items to inventory"""
    inv = load_inventory()
    for key, count in items.items():
        inv[key] = inv.get(key, 0) + count
    save_inventory(inv, {"action": "add", "items": items, "reason": reason})
    return inv


def deduct_inventory(items, reason=""):
    """Deduct items from inventory"""
    inv = load_inventory()
    for key, count in items.items():
        available = inv.get(key, 0)
        if available < count:
            raise ValueError(f"库存不足: {key} 需要 {count}，仅有 {available}")
    for key, count in items.items():
        inv[key] -= count
        if inv[key] == 0:
            del inv[key]
    save_inventory(inv, {"action": "deduct", "items": items, "reason": reason})
    return inv


def undo_last():
    """Undo last operation"""
    data = _load_data()
    log = data.get("log", [])

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
        for key, count in items.items():
            inv[key] = inv.get(key, 0) - count
            if inv[key] <= 0:
                inv.pop(key, None)
    elif last_entry["action"] == "deduct":
        for key, count in items.items():
            inv[key] = inv.get(key, 0) + count

    log.remove(last_entry)
    log.append({"action": "undo", "items": items, "reason": f"撤销 {last_entry['action']}"})

    data["inventory"] = inv
    _save_data(data)
    return inv


def print_inventory():
    """Print current inventory"""
    inv = load_inventory()
    if not inv:
        print("库存为空")
        return
    print("当前库存:")
    for key in sorted(inv.keys()):
        try:
            w, h = key.split('x')
            count = inv[key]
            print(f"  {w}×{h}: {count} stack")
        except (ValueError, AttributeError):
            print(f"  [无效格式: {key}]")
    total = sum(inv.values())
    print(f"\n共 {len(inv)} 种尺寸, {total} stack")


import sys
def parse_items(args):
    """Parse '7x5:6' format"""
    import re
    items = {}
    for arg in args:
        match = re.match(r'(\d+)x(\d+):(\d+)', arg)
        if match:
            key = f"{match.group(1)}x{match.group(2)}"
            items[key] = int(match.group(3))
        else:
            print(f"格式错误: {arg}")
            sys.exit(1)
    return items


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("用法: inventory.py list|add|deduct|undo ...")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        print_inventory()
    elif cmd == "add":
        items = parse_items(sys.argv[2:])
        result = add_inventory(items, reason="手动入库")
        print("入库完成:")
        for key, count in items.items():
            print(f"  {key}: +{count}")
        print_inventory()
    elif cmd == "deduct":
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


if __name__ == "__main__":
    main()
