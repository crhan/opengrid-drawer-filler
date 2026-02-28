#!/usr/bin/env python3
"""CLI 模块 - 统一入口"""

from opengrid.cli.commands.compare import add_parser as add_compare_parser
from . import commands
from opengrid import config


def main():
    """CLI 主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    # 添加全局参数
    parser.add_argument('-c', '--config', help='配置文件路径（默认在当前目录查找）')
    parser.add_argument('-i', '--inventory', help='库存文件路径（默认从配置文件读取）')

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

    # 将 config 路径同步到 config 模块
    config.set_cli_config_path(args.config)
    config.set_cli_inventory_path(args.inventory)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


__all__ = ['main']
