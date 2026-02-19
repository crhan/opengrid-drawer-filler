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
