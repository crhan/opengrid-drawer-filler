#!/usr/bin/env python3
"""openGrid 交互式工作流入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config_summary import get_config_summary, format_summary
from scheme_generator import generate_schemes
from scheme_presenter import present_schemes
from project_manager import ProjectManager
from stl_manager import generate_and_link_stls
from visualizer import Visualizer
from inventory import load_inventory
from config import get_projects_dir, load_config, get_printer_config


def interactive_main():
    """交互式主流程"""

    # 1. 解析用户输入
    if len(sys.argv) < 2:
        print("用法: python3 interactive.py <抽屉尺寸>")
        print("示例: python3 interactive.py 485x425")
        print("     python3 interactive.py 485x425x2  (2份)")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1]
    # 支持 "485x425" 或 "485x425x2" 格式
    parts = args.split('x')
    if len(parts) == 2:
        width, depth = map(int, parts)
        copies = 1
    elif len(parts) == 3:
        width, depth, copies = map(int, parts)
    else:
        print("格式错误: 应为 WxD 或 WxDxC")
        sys.exit(1)

    # 2. 显示配置摘要
    summary = get_config_summary()
    print(format_summary(summary))

    # 3. 生成多方案
    inventory = load_inventory()
    schemes = generate_schemes(width, depth, copies, inventory)

    # 4. 展示方案
    print(present_schemes(schemes, inventory))

    # 5. 等待用户选择
    choice = input().strip().upper()
    scheme_map = {"A": "math", "B": "inventory", "C": "print_limit"}

    if choice not in scheme_map:
        print("无效选择")
        sys.exit(1)

    selected_key = scheme_map[choice]
    selected = schemes[selected_key]["scheme"]

    if not selected:
        print("方案无效")
        sys.exit(1)

    # 6. 创建项目
    print("\n请输入项目名称: ", end="")
    project_name = input().strip() or "抽屉"

    projects_dir = get_projects_dir()
    pm = ProjectManager(projects_dir)
    project_path = pm.create_project(project_name, [
        {"width": width, "depth": depth, "copies": copies}
    ])

    print(f"✓ 已创建项目: {project_path}")

    # 7. 生成 STL
    print("正在生成 STL 文件...")
    stl_files = generate_and_link_stls(selected, project_path, copies)
    print(f"✓ 已生成 STL: {', '.join([Path(f).name for f in stl_files])}")

    # 8. 生成 HTML
    printer_cfg = get_printer_config()
    model = load_config().get("printer", {}).get("model", "p1p")

    v = Visualizer()
    html_path = project_path / "plan.html"

    # 准备数据 - 处理 tiles 格式
    tiles_data = []
    inv_match = selected.get("inventory_match", {})

    # tiles 可能是元组列表或字典列表
    tiles = selected.get("tiles", [])
    if tiles and isinstance(tiles[0], tuple):
        # 元组列表格式: [(w, h), (w, h), ...]
        # 需要统计每种尺寸的数量
        tile_dict = {}
        for w, h in tiles:
            key = f"{w}x{h}"
            tile_dict[key] = tile_dict.get(key, 0) + 1
        for key, count in tile_dict.items():
            w, h = key.split('x')
            tiles_data.append({
                "width": int(w),
                "height": int(h),
                "count": count,
                "from_inventory": inv_match.get("from_inventory", {}).get(key, 0) > 0
            })
    else:
        # 字典列表格式
        for tile in tiles:
            w = tile.get("width", 0)
            h = tile.get("height", 0)
            key = f"{w}x{h}"
            tiles_data.append({
                "width": w,
                "height": h,
                "count": tile.get("count", 1),
                "from_inventory": inv_match.get("from_inventory", {}).get(key, 0) > 0
            })

    v.generate_plan_html({
        "project_name": project_path.name,
        "drawer": {"width": width, "depth": depth},
        "printer": {"model": model.upper(), "bed_x": printer_cfg["bed_x"], "bed_y": printer_cfg["bed_y"]},
        "scheme": selected,
        "tiles": tiles_data,
        "stats": {"total_time": "~3h"},
        "svg": v.generate_assembly_svg(selected),
        "inventory_usage": inv_match.get("need_print", {}),
        "stl_files": stl_files,
        "script_path": str(Path(__file__).parent)
    }, str(html_path))

    print(f"✓ 已生成计划: {html_path}")
    print("\n提示: 在浏览器中打开 plan.html 查看完整打印计划")


if __name__ == "__main__":
    interactive_main()
