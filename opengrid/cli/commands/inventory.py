"""inventory 子命令实现"""
import sys
from opengrid.config import load_config_or_default, get_config_path
from opengrid.inventory import (
    load_inventory,
    add_inventory,
    deduct_inventory,
    undo_last,
    print_inventory,
    get_inventory_path,
)


def add_parser(subparsers):
    parser = subparsers.add_parser('inventory', help='库存管理')
    sub = parser.add_subparsers(dest='inventory_command', required=True)

    # list
    sub.add_parser('list', help='列出库存')

    # init
    sub.add_parser('init', help='初始化库存文件（创建空白库存）')

    # add
    add_p = sub.add_parser('add', help='添加库存')
    add_p.add_argument('items', nargs='+', help='物品列表 (如 8x8:5 6x7:3)')
    add_p.add_argument('-r', '--reason', default='', help='操作原因（如 "收货"）')

    # deduct
    deduct_p = sub.add_parser('deduct', help='扣减库存')
    deduct_p.add_argument('items', nargs='+', help='物品列表 (如 8x8:5 6x7:3)')
    deduct_p.add_argument('-r', '--reason', default='', help='操作原因（如 "收货"）')

    # undo
    sub.add_parser('undo', help='撤销操作')

    parser.set_defaults(func=handle_inventory)
    return parser


def _build_inventory_config(config):
    """从项目配置构建库存配置"""
    config_dir = get_config_path().parent
    inv_path = get_inventory_path(config, config_dir)
    return {"inventory_path": str(inv_path)}


def handle_inventory(args):
    """处理 inventory 命令"""
    config = load_config_or_default()
    inv_config = _build_inventory_config(config)

    cmd = args.inventory_command

    if cmd == 'list':
        print_inventory(inv_config)

    elif cmd == 'init':
        from opengrid.inventory import get_inventory_path
        inv_path = get_inventory_path(config)
        import json
        if inv_path.exists():
            print(f"库存文件已存在: {inv_path}")
        else:
            inv_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"inventory": {}, "log": []}
            with open(inv_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"已创建空白库存文件: {inv_path}")

    elif cmd == 'add':
        from opengrid.inventory import parse_items
        items, parsed_reason = parse_items(args.items)
        if not items:
            print("错误: 未提供有效的物品格式 (如 8x8:5)", file=sys.stderr)
            sys.exit(1)
        # 使用解析的 reason 或传入的 reason，如果都为空则使用默认值
        reason = parsed_reason or args.reason or "手动入库"
        add_inventory(items, reason, inv_config)
        print("添加成功")
        print_inventory(inv_config)

    elif cmd == 'deduct':
        from opengrid.inventory import parse_items
        items, parsed_reason = parse_items(args.items)
        if not items:
            print("错误: 未提供有效的物品格式 (如 8x8:5)", file=sys.stderr)
            sys.exit(1)
        reason = parsed_reason or args.reason or "手动扣库"
        deduct_inventory(items, reason, inv_config)
        print("扣减成功")
        print_inventory(inv_config)

    elif cmd == 'undo':
        undo_last(inv_config)
        print("撤销成功")
        print_inventory(inv_config)


__all__ = ['add_parser']
