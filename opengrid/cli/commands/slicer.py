"""slicer 子命令实现"""
from opengrid.stl import generator as stl_generator


def add_parser(subparsers):
    parser = subparsers.add_parser('slicer', help='STL 生成和切片')
    sub = parser.add_subparsers(dest='slicer_command', required=True)

    # generate
    gen_p = sub.add_parser('generate', help='生成 STL')
    gen_p.add_argument('dimensions', help='尺寸 WxHxS')
    gen_p.add_argument('-f', '--force', action='store_true', help='强制重新生成')

    # slice
    slice_p = sub.add_parser('slice', help='切片 STL')
    slice_p.add_argument('file', help='STL 文件')
    slice_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    # open
    open_p = sub.add_parser('open', help='在切片器中打开')
    open_p.add_argument('file', help='STL 文件')
    open_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    parser.set_defaults(func=handle_slicer)
    return parser


def handle_slicer(args):
    """处理 slicer 命令"""
    cmd = args.slicer_command

    if cmd == 'generate':
        # 解析尺寸
        dims = args.dimensions.split('x')
        if len(dims) != 3:
            print("错误: 尺寸格式应为 WxHxS")
            return
        w, h, s = map(int, dims)

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
