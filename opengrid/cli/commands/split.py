"""split 子命令实现"""
from opengrid.cli.utils import parse_dimensions
from opengrid.cli.formatters import print_plan, output_json
from opengrid.core import find_best_scheme, get_grid_dimensions


def add_parser(subparsers):
    parser = subparsers.add_parser('split', help='抽屉分割计算')
    parser.add_argument('dimensions', nargs='*', help='尺寸列表')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数')
    parser.add_argument('-j', '--json', action='store_true', help='JSON 输出')
    parser.add_argument('-b', '--batch', help='批量输入')
    parser.set_defaults(func=handle_split)
    return parser


def handle_split(args):
    """处理 split 命令"""
    # 解析输入
    dims = parse_dimensions(args.dimensions)

    if not dims:
        print("错误: 请提供尺寸参数")
        return

    width, depth, copies = dims[0]

    # 计算网格
    grid_w, grid_h = get_grid_dimensions(width, depth)

    # 找最优方案
    scheme = find_best_scheme(grid_w, grid_h)

    # 输出
    if args.json:
        print(output_json(width, depth, scheme, copies))
    else:
        print_plan(width, depth, scheme, copies)


__all__ = ['add_parser']
