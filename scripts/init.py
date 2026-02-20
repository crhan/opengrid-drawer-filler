#!/usr/bin/env python3
"""Interactive initialization script"""

import os
import sys
import yaml
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from .config import DEFAULTS, get_config_path
from .printer import PRINTER_PRESETS


def print_welcome():
    print("=" * 50)
    print("欢迎使用 opengrid-drawer-filler")
    print("=" * 50)


def collect_config():
    """Collect user configuration"""
    config = {"initialized": True}

    # STL output dir
    default_dir = DEFAULTS["output"]["stl_dir"]
    response = input(f"STL 输出目录 (默认: {default_dir}): ").strip()
    config["output"] = {"stl_dir": response or default_dir}

    # Printer model
    print("\n打印机型号:")
    for model in PRINTER_PRESETS:
        info = PRINTER_PRESETS[model]
        print(f"  - {model}: {info['bed_x']}x{info['bed_y']}x{info['max_z']}")
    default_model = DEFAULTS["printer"]["model"]
    response = input(f"选择打印机 (默认: {default_model}): ").strip().lower()
    config["printer"] = {"model": response or default_model}

    # Tile type
    default_type = DEFAULTS["opengrid"]["tile_type"]
    response = input(f"瓦片类型 (默认: {default_type}): ").strip()
    config["opengrid"] = {"tile_type": response or default_type}

    return config


def save_config(config):
    """Save config to file"""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    print(f"\n配置已保存到: {config_path}")


def main():
    """Main entry point"""
    print_welcome()
    config = collect_config()
    save_config(config)
    print("\n初始化完成！")


if __name__ == "__main__":
    main()
