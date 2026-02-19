#!/usr/bin/env python3
"""openGrid 打印计划输出工具

消费 JSON 方案数据，生成文本/Markdown/HTML/PNG 等多种格式的输出
"""

import argparse
import json
import sys
import os
from pathlib import Path

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from visualizer import Visualizer


def load_plan_from_file(path):
    """从文件加载 JSON 方案"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_plan_from_stdin():
    """从 stdin 加载 JSON 方案"""
    return json.load(sys.stdin)


def output_text(plan_data):
    """输出文本格式（简化的 ASCII 图）"""
    scheme = plan_data.get("scheme", {})
    x_splits = scheme.get("x_splits", [])
    y_splits = scheme.get("y_splits", [])

    drawer = plan_data.get("drawer", {})
    width = drawer.get("width", 0)
    depth = drawer.get("depth", 0)

    print(f"抽屉尺寸: {width}mm × {depth}mm")
    print(f"分割: {scheme.get('x_parts', 0)}×{scheme.get('y_parts', 0)}")
    print()
    print("排布:")
    for y_dim in y_splits:
        row = ""
        for x_dim in x_splits:
            row += f"{x_dim}×{y_dim} "
        print(row)


def output_png(plan_data, output_dir):
    """生成 PNG 图片"""
    v = Visualizer()
    scheme = plan_data.get("scheme", {})

    # 生成拼接图
    assembly_img = v.generate_assembly_image(scheme)

    # 生成瓦片清单图
    tiles = scheme.get("tiles", [])
    tiles_img = v.generate_tiles_image(tiles)

    # 保存
    drawer = plan_data.get("drawer", {})
    width = drawer.get("width", 0)
    depth = drawer.get("depth", 0)

    os.makedirs(output_dir, exist_ok=True)

    assembly_path = os.path.join(output_dir, "assembly.png")
    tiles_path = os.path.join(output_dir, "tiles.png")

    assembly_img.save(assembly_path)
    print(f"已保存: {assembly_path}")

    if tiles_img:
        tiles_img.save(tiles_path)
        print(f"已保存: {tiles_path}")


def output_html(plan_data, output_dir):
    """生成 HTML 报告"""
    v = Visualizer()

    drawer = plan_data.get("drawer", {})
    width = drawer.get("width", 0)
    depth = drawer.get("depth", 0)

    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(output_dir, "assembly.html")
    v.generate_html(plan_data, html_path)
    print(f"已保存: {html_path}")


def main():
    parser = argparse.ArgumentParser(description='openGrid 打印计划输出工具')
    parser.add_argument('files', nargs='*', help='JSON 方案文件路径')
    parser.add_argument('--text', action='store_true', help='输出文本格式')
    parser.add_argument('--png', action='store_true', help='生成 PNG 图片')
    parser.add_argument('--html', action='store_true', help='生成 HTML 报告')
    parser.add_argument('-o', '--output', default='output', help='输出目录')
    parser.add_argument('--stdin', action='store_true', help='从 stdin 读取 JSON')

    args = parser.parse_args()

    # 如果指定了 --stdin，从 stdin 读取
    if args.stdin:
        plan_data = load_plan_from_stdin()
        if args.png:
            output_png(plan_data, args.output)
        elif args.html:
            output_html(plan_data, args.output)
        else:
            output_text(plan_data)
        return

    # 处理文件列表
    if not args.files:
        print("请指定 JSON 文件或使用 --stdin")
        parser.print_help()
        sys.exit(1)

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            continue

        plan_data = load_plan_from_file(filepath)

        # 确定输出目录
        drawer = plan_data.get("drawer", {})
        width = drawer.get("width", 0)
        depth = drawer.get("depth", 0)

        if width and depth:
            output_dir = os.path.join(args.output, f"{width}x{depth}")
        else:
            output_dir = args.output

        if args.png:
            output_png(plan_data, output_dir)
        elif args.html:
            output_html(plan_data, output_dir)
        else:
            output_text(plan_data)

    # 如果有多个文件且指定了批量模式
    if len(args.files) > 1 and (args.png or args.html):
        # 生成合并的瓦片清单图
        all_tiles = []
        for filepath in args.files:
            if not os.path.exists(filepath):
                continue
            plan_data = load_plan_from_file(filepath)
            tiles = plan_data.get("scheme", {}).get("tiles", [])
            drawer = plan_data.get("drawer", {})
            for tile in tiles:
                tile_copy = tile.copy()
                tile_copy["source"] = f"{drawer.get('width', 0)}×{drawer.get('depth', 0)}"
                all_tiles.append(tile_copy)

        merged_dir = os.path.join(args.output, "merged")
        os.makedirs(merged_dir, exist_ok=True)

        v = Visualizer()
        merged_img = v.generate_tiles_image(all_tiles, title="合并瓦片清单")
        merged_path = os.path.join(merged_dir, "merged_tiles.png")
        merged_img.save(merged_path)
        print(f"已保存: {merged_path}")


if __name__ == "__main__":
    main()
