"""present 子命令实现 - 方案展示"""
import json
import sys
from pathlib import Path
from opengrid.ui.presenter import generate_comparison_html


def add_parser(subparsers):
    parser = subparsers.add_parser('present', help='方案展示（生成 HTML 对比页面）')
    parser.add_argument('scheme_a', help='方案A的JSON文件路径（无库存）')
    parser.add_argument('scheme_b', help='方案B的JSON文件路径（有库存）')
    parser.add_argument('-o', '--output', help='输出文件路径（默认 stdout）')
    parser.set_defaults(func=handle_present)
    return parser


def handle_present(args):
    """处理 present 命令"""
    # 读取方案A
    scheme_a_path = Path(args.scheme_a)
    if not scheme_a_path.exists():
        print(f"错误: 文件不存在: {args.scheme_a}", file=sys.stderr)
        sys.exit(1)

    with open(scheme_a_path, 'r', encoding='utf-8') as f:
        scheme_a = json.load(f)

    # 读取方案B
    scheme_b_path = Path(args.scheme_b)
    if not scheme_b_path.exists():
        print(f"错误: 文件不存在: {args.scheme_b}", file=sys.stderr)
        sys.exit(1)

    with open(scheme_b_path, 'r', encoding='utf-8') as f:
        scheme_b = json.load(f)

    # 生成 HTML
    try:
        html = generate_comparison_html(scheme_a, scheme_b)
    except Exception as e:
        print(f"错误: 生成 HTML 失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"已生成: {output_path.absolute()}")
    else:
        print(html)
