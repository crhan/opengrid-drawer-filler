"""slicer 子命令实现"""
import sys
from opengrid.stl import generator as stl_generator


def add_parser(subparsers):
    parser = subparsers.add_parser('slicer', help='STL 生成和切片')
    sub = parser.add_subparsers(dest='slicer_command', required=True)

    # generate
    gen_p = sub.add_parser('generate', help='生成 STL')
    gen_p.add_argument('dimensions', help='尺寸 WxHxS')
    gen_p.add_argument('-f', '--force', action='store_true', help='强制重新生成')

    # slice
    slice_p = sub.add_parser('slice', help='[未实现] 切片 STL')
    slice_p.add_argument('file', help='STL 文件')
    slice_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    # open
    open_p = sub.add_parser('open', help='[未实现] 在切片器中打开')
    open_p.add_argument('file', help='STL 文件')
    open_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    parser.set_defaults(func=handle_slicer)
    return parser


def _parse_slicer_dims(text: str) -> tuple[int, int, int]:
    """解析 slicer generate 的 WxHxS 尺寸串，失败时给清晰错误并退出。

    Returns: (width, height, stacks)，三者均为正整数（单位：cells / 层）
    """
    dims = text.split('x')
    if len(dims) != 3:
        print(f"错误: 尺寸格式应为 WxHxS（宽x深x堆叠层数），如 7x5x2", file=sys.stderr)
        print(f"  收到: {text!r}", file=sys.stderr)
        sys.exit(1)
    try:
        w, h, s = int(dims[0]), int(dims[1]), int(dims[2])
    except ValueError:
        print(f"错误: 宽/深/堆叠层数必须为整数，如 7x5x2", file=sys.stderr)
        print(f"  收到: {text!r}", file=sys.stderr)
        sys.exit(1)
    if w <= 0 or h <= 0 or s <= 0:
        print(f"错误: 宽/深/堆叠层数必须为正整数，收到 {w}x{h}x{s}", file=sys.stderr)
        sys.exit(1)
    return w, h, s


def handle_slicer(args):
    """处理 slicer 命令"""
    cmd = args.slicer_command

    if cmd == 'generate':
        w, h, s = _parse_slicer_dims(args.dimensions)

        # 生成 STL
        output = stl_generator.generate_stl(w, h, s, force=args.force)
        print(f"生成: {output}")

    elif cmd == 'slice':
        # TODO: 实现切片逻辑
        print(f"切片: {args.file} (slicer={args.slicer})")

    elif cmd == 'open':
        # TODO: 实现打开逻辑
        print(f"打开: {args.file} (slicer={args.slicer})")


__all__ = ['add_parser']
