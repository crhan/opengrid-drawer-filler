#!/usr/bin/env python3
"""Interactive workflow entry point"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config_summary import get_config_summary, format_summary
from scripts.scheme_generator import generate_schemes
from scripts.scheme_presenter import present_schemes
from scripts.project_manager import ProjectManager
from scripts.stl_manager import generate_and_link_stls
from scripts.visualizer import Visualizer
from scripts.inventory import load_inventory
from scripts.config import get_projects_dir, load_config, get_printer_config


def interactive_main():
    """Interactive main flow"""
    if len(sys.argv) < 2:
        print("用法: interactive.py <抽屉尺寸>")
        sys.exit(1)

    # Parse args
    args = sys.argv[1]
    parts = args.split('x')
    if len(parts) == 2:
        width, depth = map(int, parts)
        copies = 1
    elif len(parts) == 3:
        width, depth, copies = map(int, parts)
    else:
        print("格式错误")
        sys.exit(1)

    # Show config summary
    summary = get_config_summary()
    print(format_summary(summary))

    # Generate schemes
    inventory = load_inventory()
    schemes = generate_schemes(width, depth, copies, inventory)

    # Present schemes
    print(present_schemes(schemes, inventory))

    # Get choice
    choice = input().strip().upper()
    scheme_map = {"A": "math", "B": "inventory", "C": "print_limit"}

    if choice not in scheme_map:
        print("无效选择")
        sys.exit(1)

    print("\n完成")


if __name__ == "__main__":
    interactive_main()
