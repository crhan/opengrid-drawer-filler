#!/usr/bin/env python3
"""配置摘要模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from opengrid.config import load_config, get_printer_config
from opengrid.inventory import load_inventory

PRINTER_NAMES = {
    "a1_mini": "A1 mini",
    "a1": "A1",
    "p1p": "P1P",
    "p1s": "P1S",
    "x1c": "X1C",
    "x1e": "X1E",
    "h2d": "H2D"
}

def get_config_summary():
    """返回配置摘要"""
    config = load_config()
    printer_config = get_printer_config()

    # 获取打印机型号
    model = config.get("printer", {}).get("model", "p1p")
    printer_name = PRINTER_NAMES.get(model, model.upper())

    # 获取库存
    inventory = load_inventory()

    # 获取项目目录
    projects_dir = config.get("projects_dir", "~/opengrid_projects/")

    return {
        "printer": {
            "model": printer_name,
            "bed_x": printer_config["bed_x"],
            "bed_y": printer_config["bed_y"],
            "max_z": printer_config["max_z"]
        },
        "inventory": inventory,
        "projects_dir": str(projects_dir)
    }

def format_summary(summary):
    """格式化配置摘要"""
    p = summary["printer"]
    inv = summary["inventory"]

    # 库存摘要
    if inv:
        inv_parts = [f"{k}: {v} stack" for k, v in sorted(inv.items())]
        inv_str = ", ".join(inv_parts)
    else:
        inv_str = "(空)"

    return f"""
╔══════════════════════════════════════════════════════════╗
║  当前配置                                              ║
╠══════════════════════════════════════════════════════════╣
║  打印机: {p['model']} ({p['bed_x']}×{p['bed_y']}mm)                                ║
║  库存:   {inv_str}                          ║
║  输出:   {summary['projects_dir']}          ║
╚══════════════════════════════════════════════════════════╝
"""
