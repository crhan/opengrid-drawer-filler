"""slicer 子命令实现"""
import sys

from opengrid.core.batch_planner import build_printer_config
from opengrid.core.grid import get_max_stacks
from opengrid.stl import generator as stl_generator


def add_parser(subparsers):
    parser = subparsers.add_parser('slicer', help='STL 生成和切片')
    sub = parser.add_subparsers(dest='slicer_command', required=True)

    # generate
    gen_p = sub.add_parser('generate', help='生成 STL')
    gen_p.add_argument('dimensions', help='尺寸 WxHxS（宽 cells x 深 cells x 堆叠层数）')
    gen_p.add_argument('-f', '--force', action='store_true', help='强制重新生成（覆盖已有文件）')
    gen_p.add_argument('-v', '--verbose', action='store_true', help='打印 OpenSCAD 命令行和 stderr')

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


def _parse_dims(text: str) -> tuple[int, int, int] | str:
    """纯函数：解析 WxHxS 字符串。

    Returns:
        成功时返回 (w, h, s) tuple；失败时返回错误消息字符串（不退出，不打印）。
    """
    dims = text.split('x')
    if len(dims) != 3:
        return f"尺寸格式应为 WxHxS（宽x深x堆叠层数），如 7x5x2\n  收到: {text!r}"
    try:
        w, h, s = int(dims[0]), int(dims[1]), int(dims[2])
    except ValueError:
        return f"宽/深/堆叠层数必须为整数，如 7x5x2\n  收到: {text!r}"
    if w <= 0 or h <= 0 or s <= 0:
        return f"宽/深/堆叠层数必须为正整数，收到 {w}x{h}x{s}"
    return (w, h, s)


def _validate_dims(w: int, h: int, s: int, printer) -> str | None:
    """纯函数：用 PrinterConfig 检查 WxHxS 是否超出上限。

    Returns:
        None 表示合法；超限时返回错误消息字符串。
    """
    max_w = printer.max_cells_x
    max_h = printer.max_cells_y
    max_s = get_max_stacks(printer)
    if w > max_w or h > max_h or s > max_s:
        return (
            f"尺寸超出当前打印机限制 ({printer.bed_x}x{printer.bed_y}x{printer.max_z}mm)\n"
            f"  收到: {w}x{h}x{s}\n"
            f"  允许: 宽≤{max_w} cells / 深≤{max_h} cells / 堆叠≤{max_s} 层"
        )
    return None


def _parse_slicer_dims(text: str) -> tuple[int, int, int]:
    """CLI wrapper：解析 + 上限校验，失败时打 stderr 并 sys.exit(1)。

    上限来自当前打印机配置（PrinterConfig），跨打印机切换 yaml 后自动适配。
    业务逻辑在纯函数 _parse_dims / _validate_dims 里，便于单元测试。
    """
    parsed = _parse_dims(text)
    if isinstance(parsed, str):
        print(f"错误: {parsed}", file=sys.stderr)
        sys.exit(1)

    w, h, s = parsed
    err = _validate_dims(w, h, s, build_printer_config())
    if err is not None:
        print(f"错误: {err}", file=sys.stderr)
        sys.exit(1)

    return w, h, s


def handle_slicer(args):
    """处理 slicer 命令"""
    cmd = args.slicer_command

    if cmd == 'generate':
        w, h, s = _parse_slicer_dims(args.dimensions)

        try:
            output, status = stl_generator.generate_stl(
                w, h, s,
                verbose=getattr(args, 'verbose', False),
                force=args.force,
            )
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(2)
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        if status == "skipped":
            print(f"跳过（已存在）: {output}")
        else:
            print(f"生成: {output}")

    elif cmd == 'slice':
        # TODO: 实现切片逻辑
        print(f"切片: {args.file} (slicer={args.slicer})")

    elif cmd == 'open':
        # TODO: 实现打开逻辑
        print(f"打开: {args.file} (slicer={args.slicer})")


__all__ = ['add_parser']
