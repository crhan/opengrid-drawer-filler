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
