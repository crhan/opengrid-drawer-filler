"""status 子命令实现 - 展示项目状态"""
import json

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

    # 库存状态分四种：未配置 / 文件不存在 / 文件坏 / 正常读到（可能为空）
    inv = {}
    inv_status = 'loaded'
    inv_path_str = None
    try:
        inv_path = get_inventory_path(config)
        inv_path_str = str(inv_path)
        inv = load_inventory({"inventory_path": inv_path_str})
        if not inv:
            inv_status = 'empty'
    except FileNotFoundError:
        # FileNotFoundError 不是 ValueError 子类，先后顺序无所谓
        inv_status = 'not_found'
    except json.JSONDecodeError:
        # JSONDecodeError 是 ValueError 子类，**必须**在 ValueError 之前 catch
        inv_status = 'invalid'
    except ValueError:
        inv_status = 'unconfigured'

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
        '_inventory_meta': {
            'status': inv_status,
            'path': inv_path_str,
        },
    }


def handle_status(args):
    """处理 status 命令 - 展示项目状态"""
    data = _collect_status()

    if getattr(args, 'json', False):
        _emit_json(data)
        return

    _print_human(data)


def _emit_json(data: dict) -> None:
    """Agent 友好的 JSON 输出。

    inventory.status 区分五种情形（让 Agent 不再把"真没货"和"配置坏"混淆）：
      - loaded:       配置 OK 文件 OK 且有库存
      - empty:        配置 OK 文件 OK 但库存为空
      - unconfigured: opengrid_config.yaml 没配 inventory_path
      - not_found:    配了 path 但文件不存在
      - invalid:      文件存在但 JSON 坏
    """
    inv = data['inventory']
    meta = data['_inventory_meta']
    items = [{'size': key, 'count': inv[key]} for key in sorted(inv.keys())]
    payload = {
        'printer': data['printer'],
        'output': data['output'],
        'opengrid': data['opengrid'],
        'inventory': {
            'status': meta['status'],
            'path': meta['path'],
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
