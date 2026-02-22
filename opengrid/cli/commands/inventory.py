"""inventory 子命令实现"""
from opengrid.config import load_config
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

    # add
    add_p = sub.add_parser('add', help='添加库存')
    add_p.add_argument('items', help='物品列表')
    add_p.add_argument('reason', nargs='?', default='', help='原因')

    # deduct
    deduct_p = sub.add_parser('deduct', help='扣减库存')
    deduct_p.add_argument('items', help='物品列表')
    deduct_p.add_argument('reason', nargs='?', default='', help='原因')

    # undo
    sub.add_parser('undo', help='撤销操作')

    parser.set_defaults(func=handle_inventory)
    return parser


def _build_inventory_config(config):
    """从项目配置构建库存配置"""
    inv_path = get_inventory_path(config)
    return {"inventory_path": str(inv_path)}


def handle_inventory(args):
    """处理 inventory 命令"""
    config = load_config()
    inv_config = _build_inventory_config(config)

    cmd = args.inventory_command

    if cmd == 'list':
        print_inventory(inv_config)

    elif cmd == 'add':
        from opengrid.inventory import parse_items
        items, reason = parse_items([args.items])
        if not items:
            print("错误: 未提供有效的物品格式 (如 8x8:5)")
            return
        # 使用传入的 reason，如果为空则使用默认值
        reason = reason or args.reason or "手动入库"
        add_inventory(items, reason, inv_config)
        print("添加成功")
        print_inventory(inv_config)

    elif cmd == 'deduct':
        from opengrid.inventory import parse_items
        items, reason = parse_items([args.items])
        if not items:
            print("错误: 未提供有效的物品格式 (如 8x8:5)")
            return
        reason = reason or args.reason or "手动扣库"
        deduct_inventory(items, reason, inv_config)
        print("扣减成功")
        print_inventory(inv_config)

    elif cmd == 'undo':
        undo_last(inv_config)
        print("撤销成功")
        print_inventory(inv_config)


__all__ = ['add_parser']
