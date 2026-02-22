"""CLI 模块 - 统一入口"""

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
    commands.project.add_parser(subparsers)
    commands.inventory.add_parser(subparsers)
    commands.split.add_parser(subparsers)
    commands.slicer.add_parser(subparsers)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


__all__ = ['main']
