# split 子命令实现：参数解析、单抽屉分割计算与输出分发
# 批量计算逻辑已迁移至 opengrid/cli/batch.py

import sys
import json
from pathlib import Path
from opengrid.cli.batch import batch_mode
from opengrid.cli.utils import parse_dimensions
from opengrid.cli.formatters import print_plan, output_json
from opengrid.core.split_result import PrinterConfig, SplitResult
from opengrid.core.grid import GridConfig
from opengrid.config import load_config_or_default, get_printer_config_or_default


def _build_printer_config() -> PrinterConfig:
    """从当前配置构造 PrinterConfig

    Returns:
        PrinterConfig 实例，包含打印机床尺寸、Z 轴限制、瓦片厚度等参数
    """
    config = load_config_or_default()
    printer = get_printer_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    tile_size = config.get("opengrid", {}).get("tile_size", 28)

    from opengrid.core.constants import TILE_THICKNESS
    thickness = TILE_THICKNESS.get(tile_type, 7.2)

    bed_x = printer.get("bed_x", 256)
    bed_y = printer.get("bed_y", 256)

    return PrinterConfig(
        max_z=printer.get("max_z", 256),
        bed_x=bed_x,
        bed_y=bed_y,
        tile_thickness=thickness,
        max_cells_x=bed_x // tile_size,
        max_cells_y=bed_y // tile_size,
    )


def _build_grid_config() -> GridConfig:
    """从当前配置构造 GridConfig

    Returns:
        GridConfig 实例，包含最大格子数约束
    """
    printer = _build_printer_config()
    return GridConfig(
        max_cells_x=printer.max_cells_x,
        max_cells_y=printer.max_cells_y,
    )


def add_parser(subparsers):
    """注册 split 子命令及其所有参数

    Args:
        subparsers: argparse 的子命令注册器

    Returns:
        已配置好的 ArgumentParser 实例
    """
    parser = subparsers.add_parser('split', help='抽屉分割计算')
    parser.add_argument('dimensions', nargs='*', help='抽屉尺寸，如 265x365 或 265x365:2（份数）')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数')
    parser.add_argument('-j', '--json', action='store_true',
                        help='JSON 输出到标准输出（可管道传递，与 -o 连用时输出到文件）')
    parser.add_argument('-o', '--output', help='JSON 输出文件路径（默认临时目录）')
    parser.add_argument('-H', '--html', help='生成 HTML 报告并保存到指定路径')
    parser.add_argument('-P', '--project-dir', help='生成完整项目到指定目录')
    parser.add_argument('-b', '--batch', help='批量输入')
    parser.add_argument('-i', '--inventory', help='库存文件路径')
    parser.add_argument('--no-inventory', action='store_true',
                        help='禁用库存（忽略配置文件中的 inventory_path）')
    parser.set_defaults(func=handle_split)
    return parser


def handle_split(args):
    """处理 split 命令，加载库存、路由到批量或单抽屉计算并输出结果

    Args:
        args: argparse 解析后的命名空间对象
    """
    import tempfile
    import time

    inventory = None
    if args.inventory:
        try:
            with open(args.inventory, 'r', encoding='utf-8') as f:
                data = json.load(f)
            inventory = data.get('inventory', {})
        except FileNotFoundError:
            print(f"错误: 库存文件不存在: {args.inventory}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"错误: 库存文件格式无效: {args.inventory}", file=sys.stderr)
            sys.exit(1)
    elif not args.no_inventory:
        try:
            from opengrid.config import load_config_or_default, get_config_path
            config = load_config_or_default()
            config_dir = get_config_path().parent
            from opengrid.inventory import get_inventory_path
            inv_path = get_inventory_path(config, config_dir)
            if inv_path.exists():
                with open(inv_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                inventory = data.get('inventory', {})
        except Exception:
            pass

    if args.batch:
        batch_mode(
            args.batch,
            verbose=False,
            inventory=inventory,
            json_output=args.json
        )
        return

    dims = parse_dimensions(args.dimensions)

    if not dims:
        print("错误: 请提供尺寸参数，如 265x365 或 265x365:2", file=sys.stderr)
        sys.exit(1)

    width, depth, copies = dims[0]

    printer = _build_printer_config()
    split_result = SplitResult.compute(width, depth, copies, inventory, printer)
    scheme = split_result

    if args.json and not args.output:
        print(output_json(width, depth, split_result, copies, inventory=inventory))
    elif args.output:
        json_data = output_json(width, depth, split_result, copies, inventory=inventory)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        print(f"方案已保存: {output_path}")
    elif args.html:
        from opengrid.ui.visualizer import Visualizer
        v = Visualizer()
        plan_data = {
            'scheme': scheme,
            'drawer': {'width': width, 'depth': depth},
            'stats': {
                'total_tiles': len(scheme.get('tiles', [])),
                'unique_sizes': len(set(scheme.get('tiles', []))),
                'total_prints': 1
            }
        }
        v.generate_html(plan_data, args.html)
        print(f"已生成 HTML 报告: {args.html}")
    elif args.project_dir:
        from opengrid.ui.presenter import generate_print_plan_html
        project_path = Path(args.project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        scheme_data = {
            'scheme': scheme,
            'stats': {
                'total_time': f"{int(width*depth*0.001)} min",
                'total_filament': f"{int(width*depth*0.0004)}g"
            },
            'inventory_usage': {
                'from_inventory': scheme.get('from_inventory', {}),
                'need_print': scheme.get('need_print', {})
            }
        }
        drawer_specs = [{'width': width, 'depth': depth, 'copies': copies}]

        generate_print_plan_html(
            project_path=project_path,
            project_name=project_path.name,
            scheme_data=scheme_data,
            drawer_specs=drawer_specs,
            stl_files=[]
        )
        print(f"已生成项目计划: {project_path}/print_plan.html")
    else:
        print_plan(width, depth, scheme, copies, inventory)


from opengrid.cli.batch import (
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    calculate_batch_cost_with_inventory,
    optimize_batch_global,
    build_batch_data,
    print_batch_plan,
)

__all__ = [
    'add_parser',
    'calculate_single',
    'merge_and_optimize',
    'calculate_total_prints',
    'calculate_batch_cost_with_inventory',
    'optimize_batch_global',
    'build_batch_data',
    'print_batch_plan',
]
