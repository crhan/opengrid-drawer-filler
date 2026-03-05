"""status 子命令实现 - 展示项目状态"""
from opengrid.config import load_config_or_default, get_printer_config_or_default
from opengrid.inventory import load_inventory, format_inventory_for_display, get_inventory_path


def add_parser(subparsers):
    """注册 status 子命令"""
    parser = subparsers.add_parser('status', help='显示项目状态')
    parser.set_defaults(func=handle_status)
    return parser


def handle_status(args):
    """处理 status 命令 - 展示项目状态"""
    # 加载配置
    config = load_config_or_default()
    printer = get_printer_config_or_default()

    # 获取打印机信息
    model = config.get('printer', {}).get('model', 'p1p')
    bed_x = printer.get('bed_x', 256)
    bed_y = printer.get('bed_y', 256)
    max_z = printer.get('max_z', 256)

    # 获取输出目录
    output_dir = config.get('output', {}).get('stl_dir', '~/3D打印/opengrid/')

    # 获取瓦片配置
    tile_type = config.get('opengrid', {}).get('tile_type', 'Full')
    stacking = config.get('opengrid', {}).get('stacking_method', 'Ironing')

    # 加载库存
    try:
        inv_path = get_inventory_path(config)
        inv = load_inventory({"inventory_path": str(inv_path)})
    except (ValueError, FileNotFoundError):
        inv = {}

    # 打印状态
    _print_header()
    _print_inventory(inv)
    _print_config(model, bed_x, bed_y, max_z, output_dir, tile_type, stacking)


def _print_header():
    """打印状态头部"""
    print("\n========== openGrid 状态 ==========\n")


def _print_inventory(inv):
    """打印库存状态"""
    print(format_inventory_for_display(inv))
    print()


def _print_config(model, bed_x, bed_y, max_z, output_dir, tile_type, stacking):
    """打印配置信息"""
    print(f"打印机: {model.upper()} ({bed_x}x{bed_y}x{max_z}mm)")
    print(f"输出目录: {output_dir}")
    print(f"瓦片类型: {tile_type} | 堆叠: {stacking}")


__all__ = ['add_parser']
