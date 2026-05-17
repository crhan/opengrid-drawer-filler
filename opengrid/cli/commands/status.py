"""status 子命令实现 - 展示项目状态"""
import json
import sys

from opengrid.config import load_config_or_default, get_printer_config_or_default
from opengrid.inventory import load_inventory, format_inventory_for_display, get_inventory_path


def add_parser(subparsers):
    """注册 status 子命令"""
    parser = subparsers.add_parser('status', help='显示项目状态')
    parser.add_argument('-j', '--json', action='store_true',
                        help='以 JSON 格式输出（供 Agent 解析）')
    parser.set_defaults(func=handle_status)
    return parser


def _collect_status() -> dict:
    """收集状态数据，统一供人话与 JSON 输出复用。"""
    config = load_config_or_default()
    printer = get_printer_config_or_default()

    model = config.get('printer', {}).get('model', 'p1p')
    bed_x = printer.get('bed_x', 256)
    bed_y = printer.get('bed_y', 256)
    max_z = printer.get('max_z', 256)

    output_dir = config.get('output', {}).get('stl_dir', '~/3D打印/opengrid/')
    tile_type = config.get('opengrid', {}).get('tile_type', 'Full')
    stacking = config.get('opengrid', {}).get('stacking_method', 'Ironing')

    try:
        inv_path = get_inventory_path(config)
        inv = load_inventory({"inventory_path": str(inv_path)})
    except (ValueError, FileNotFoundError):
        inv = {}

    return {
        'printer': {
            'model': model,
            'bed_x': bed_x,
            'bed_y': bed_y,
            'max_z': max_z,
        },
        'output': {
            'stl_dir': output_dir,
        },
        'opengrid': {
            'tile_type': tile_type,
            'stacking_method': stacking,
        },
        'inventory': inv,
    }


def handle_status(args):
    """处理 status 命令 - 展示项目状态"""
    data = _collect_status()

    if getattr(args, 'json', False):
        _emit_json(data)
        return

    _print_human(data)


def _emit_json(data: dict) -> None:
    """Agent 友好的 JSON 输出。"""
    inv = data['inventory']
    items = [{'size': key, 'count': inv[key]} for key in sorted(inv.keys())]
    payload = {
        'printer': data['printer'],
        'output': data['output'],
        'opengrid': data['opengrid'],
        'inventory': {
            'items': items,
            'total_types': len(items),
            'total_count': sum(inv.values()),
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _print_human(data: dict) -> None:
    """原有人话输出。"""
    print("\n========== openGrid 状态 ==========\n")
    print(format_inventory_for_display(data['inventory']))
    print()
    p = data['printer']
    print(f"打印机: {p['model'].upper()} ({p['bed_x']}x{p['bed_y']}x{p['max_z']}mm)")
    print(f"输出目录: {data['output']['stl_dir']}")
    print(f"瓦片类型: {data['opengrid']['tile_type']} | 堆叠: {data['opengrid']['stacking_method']}")


__all__ = ['add_parser']
