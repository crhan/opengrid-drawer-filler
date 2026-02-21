"""Inventory CRUD operations"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Inventory file path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(SCRIPT_DIR, '..', 'inventory', 'inventory.json')


def get_inventory_path(config=None):
    """从配置获取库存文件路径

    Args:
        config: 配置字典，如为 None 则自动加载

    Returns:
        Path: 库存文件路径
    """
    if config is None:
        from opengrid.config import load_config
        config = load_config()

    inventory_path = config.get("inventory_path")
    if inventory_path:
        p = Path(inventory_path)
        if p.is_absolute():
            return p
        # 相对路径相对于配置文件所在目录
        config_dir = Path.cwd()
        return config_dir / p

    # 默认使用全局 inventory
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "inventory" / "inventory.json"


def _get_inventory_file(config=None):
    """Get inventory file path - 支持配置指定"""
    return str(get_inventory_path(config))


def _load_data(config=None):
    """Load inventory data with log"""
    inv_file = get_inventory_path(config)
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


def format_inventory_for_display(inv=None):
    """Format inventory for Agent display in Step 1

    Args:
        inv: inventory dict, if None loads from file

    Returns:
        str: formatted inventory display
    """
    if inv is None:
        inv = load_inventory()

    if not inv:
        return """╔════════════════════════════════════════╗
║  📦 库存状态                          ║
╚════════════════════════════════════════╝

   库存为空

   共 0 种尺寸, 0 stack"""

    # 格式化库存项为表格
    lines = ["┌──────────┬──────────┐"]
    lines.append("│ 瓦片尺寸  │   数量   │")
    lines.append("├──────────┼──────────┤")

    for key in sorted(inv.keys(), key=lambda x: (int(x.split('x')[0]) * int(x.split('x')[1])), reverse=True):
        try:
            w, h = key.split('x')
            count = inv[key]
            lines.append(f"│ {w:>6}×{h:<5} │   {count:>3}    │")
        except (ValueError, AttributeError):
            lines.append(f"│ [无效: {key:<5}] │   {inv[key]:>3}    │")

    lines.append("└──────────┴──────────┘")

    total = sum(inv.values())
    unique = len(inv)

    return f"""╔════════════════════════════════════════╗
║  📦 库存状态                          ║
╚════════════════════════════════════════╝

{chr(10).join(lines)}

共 **{unique} 种尺寸**, **{total} stack** (可用)"""

    """Parse '7x5:6' format,最后一个非格式参数作为 reason"""
    import re
    items = {}
    reason = ""
    for arg in args:
        match = re.match(r'(\d+)x(\d+):(\d+)', arg)
        if match:
            key = f"{match.group(1)}x{match.group(2)}"
            items[key] = int(match.group(3))
        else:
            # 最后一个非格式参数作为 reason
            reason = arg
    return items, reason


def get_inventory_match(tiles, copies, inv):
    """Calculate inventory match for a scheme

    Args:
        tiles: list of (w, h) tuples
        copies: print copies
        inv: inventory dict

    Returns:
        {
            "from_inventory": {"7x5": 3},
            "need_print": {"10x5": 3},
            "match_score": 3
        }
    """
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


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("用法: inventory.py list|add|deduct|undo ...")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        print_inventory()
    elif cmd == "add":
        items, reason = parse_items(sys.argv[2:])
        result = add_inventory(items, reason=reason if reason else "手动入库")
        print("入库完成:")
        for key, count in items.items():
            print(f"  {key}: +{count}")
        print_inventory()
    elif cmd == "deduct":
        items, reason = parse_items(sys.argv[2:])
        try:
            result = deduct_inventory(items, reason=reason if reason else "手动扣库")
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
