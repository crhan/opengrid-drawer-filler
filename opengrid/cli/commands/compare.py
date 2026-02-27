"""compare 子命令实现 - 生成 HTML 对比并打开"""
import json
import os
import sys
import webbrowser
from pathlib import Path
from argparse import Namespace

from opengrid.ui.presenter import generate_comparison_html

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _load_scheme(path_str: str) -> dict:
    """加载方案 JSON 文件"""
    path = Path(path_str)
    if not path.exists():
        print(f"错误: 文件不存在: {path.absolute()}", file=sys.stderr)
        sys.exit(1)
    # 文件大小限制
    if path.stat().st_size > MAX_FILE_SIZE:
        print(f"错误: 文件过大 (最大 {MAX_FILE_SIZE // 1024 // 1024}MB)", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)


def _generate_html(scheme_a: dict, scheme_b: dict) -> str:
    """生成 HTML 对比页面"""
    try:
        return generate_comparison_html(scheme_a, scheme_b)
    except ValueError as e:
        print(f"错误: 方案数据无效: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 生成 HTML 失败: {e}", file=sys.stderr)
        sys.exit(1)


def _resolve_output_path(output: str, force: bool) -> Path:
    """解析并验证输出路径"""
    path = Path(output).resolve()
    if path.exists() and not force:
        print(f"错误: 文件已存在: {path}，使用 --force 覆盖", file=sys.stderr)
        sys.exit(1)
    return path


def _write_html(html: str, output_path: Path) -> None:
    """写入 HTML 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"已生成: {output_path.absolute()}")


def _open_html(path: Path) -> None:
    """用系统默认浏览器打开 HTML 文件"""
    try:
        webbrowser.open(f"file://{path.absolute()}")
    except Exception as e:
        print(f"警告: 无法打开浏览器: {e}", file=sys.stderr)


def add_parser(subparsers):
    parser = subparsers.add_parser('compare', help='生成方案对比 HTML 并打开')
    parser.add_argument('scheme_a', help='方案A的JSON文件路径')
    parser.add_argument('scheme_b', help='方案B的JSON文件路径')
    parser.add_argument('-o', '--output', default='comparison.html', help='输出文件路径')
    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖已存在的文件')
    parser.add_argument('--no-open', action='store_true', help='不自动打开 HTML')
    parser.set_defaults(func=handle_compare)
    return parser


def handle_compare(args: Namespace) -> None:
    """处理 compare 命令"""
    # 加载并验证方案
    scheme_a = _load_scheme(args.scheme_a)
    scheme_b = _load_scheme(args.scheme_b)

    # 生成 HTML
    html = _generate_html(scheme_a, scheme_b)

    # 写入文件
    output_path = _resolve_output_path(args.output, args.force)
    _write_html(html, output_path)

    # 打开 HTML
    if not args.no_open:
        _open_html(output_path)


__all__ = ['add_parser']
