#!/usr/bin/env python3
"""Inventory management CLI wrapper

Usage:
    python scripts/inventory.py list
    python scripts/inventory.py add 8x8:5 6x7:3 "入库原因"
    python scripts/inventory.py deduct 8x8:2 "扣减原因"
    python scripts/inventory.py undo

    python scripts/inventory.py -l global list    # 使用全局配置
    python scripts/inventory.py -l project list   # 使用项目配置

    python scripts/inventory.py --help # 显示帮助
"""
import sys
import os
import argparse

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from opengrid import config as config_module
from opengrid import inventory as inventory_module


def main():
    parser = argparse.ArgumentParser(
        description='openGrid 库存管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/inventory.py list
  python scripts/inventory.py add 8x8:5 6x7:3 "入库原因：购买新材料"
  python scripts/inventory.py deduct 8x8:2 "扣减原因：打印使用"
  python scripts/inventory.py undo

  # 使用全局配置
  python scripts/inventory.py -l global list

  # 使用项目配置（当前目录有 opengrid_config.yaml）
  python scripts/inventory.py -l project list
        """
    )
    parser.add_argument('-l', '--level', choices=['auto', 'global', 'project'],
                        default='auto',
                        help='配置级别: auto (自动检测), global (全局), project (项目)')
    parser.add_argument('command', nargs='?', choices=['list', 'add', 'deduct', 'undo'],
                        help='子命令: list(查看) / add(添加) / deduct(扣减) / undo(撤销)')
    parser.add_argument('items', nargs='*', help='格式: 宽x高:数量 (如 8x8:5)')
    parser.add_argument('reason', nargs='?', help='操作原因 (add/deduct 时最后一个非格式参数)')

    args = parser.parse_args()

    # 加载配置
    scope = args.level
    config_module.reload_config(scope)
    config = config_module.load_config(scope)

    # 获取库存路径
    from opengrid.inventory import get_inventory_path
    inv_path = get_inventory_path(config)

    # 将参数转换回 sys.argv 格式，交给原有的 main 函数处理
    sys.argv = [sys.argv[0]]
    if args.command:
        sys.argv.append(args.command)
    if args.items:
        # 过滤出格式正确的 items，将 reason 放在最后
        formatted_items = []
        reason = args.reason
        for item in args.items:
            if ':' in item and 'x' in item:
                formatted_items.append(item)
            elif reason is None:
                # 第一个非格式参数作为 reason
                reason = item
            else:
                # 多个非格式参数，只取第一个作为 reason
                pass
        sys.argv.extend(formatted_items)
        if reason:
            sys.argv.append(reason)

    # 重新设置 inventory 模块的 INVENTORY_FILE
    inventory_module.INVENTORY_FILE = str(inv_path)

    # 调用原来的 main
    inventory_module.main()


if __name__ == "__main__":
    main()
