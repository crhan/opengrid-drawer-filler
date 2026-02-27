"""CLI 模块 - 统一入口"""

from opengrid.cli.commands.compare import add_parser as add_compare_parser
from . import commands


def main():
    """CLI 主入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # 注册子命令
    commands.split.add_parser(subparsers)
    commands.inventory.add_parser(subparsers)
    commands.slicer.add_parser(subparsers)
    commands.project.add_parser(subparsers)
    commands.status.add_parser(subparsers)
    commands.present.add_parser(subparsers)
    add_compare_parser(subparsers)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


__all__ = ['main']
