#!/usr/bin/env python3
"""方案展示模块"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# 初始化 Jinja2 环境
TEMPLATE_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def present_schemes(schemes, inventory):
    """展示多方案对比"""

    output = []
    output.append("")
    output.append("╔══════════════════════════════════════════════════════════╗")
    output.append("║  方案对比                                              ║")
    output.append("╚══════════════════════════════════════════════════════════╝")
    output.append("")

    for key, data in schemes.items():
        name = data["name"]
        scheme = data.get("scheme") or {}

        # 处理 tiles 格式 - 可能是元组列表或字典列表
        tiles = scheme.get("tiles", [])
        if tiles and isinstance(tiles[0], tuple):
            # 元组列表格式: [(w, h), (w, h), ...]
            # 统计每种尺寸的数量
            tile_dict = {}
            for w, h in tiles:
                key_str = f"{w}x{h}"
                tile_dict[key_str] = tile_dict.get(key_str, 0) + 1
            tile_list = [{"width": w, "height": h, "count": c} for (w, h), c in
                        [(tuple(map(int, k.split('x'))), v) for k, v in tile_dict.items()]]
        else:
            tile_list = tiles

        # 独特尺寸
        unique_sizes = len(tile_list)

        # 总瓦片数
        total_tiles = sum(t.get("count", 1) for t in tile_list)

        # 瓦片列表
        tile_strs = []
        for t in tile_list:
            w = t.get("width") or t[0]
            h = t.get("height") or t[1]
            count = t.get("count", 1)
            tile_strs.append(f"{w}×{h}: {count}")

        # 库存信息 - 增强版
        from_inv = scheme.get("from_inventory", {})
        need_print = scheme.get("need_print", {})

        if from_inv or need_print:
            # 收集所有需要的瓦片尺寸
            all_needed = {}
            if from_inv:
                for k, v in from_inv.items():
                    all_needed[k] = all_needed.get(k, 0) + v
            if need_print:
                for k, v in need_print.items():
                    all_needed[k] = all_needed.get(k, 0) + v

            # 计算覆盖率
            covered = 0
            total_sizes = len(all_needed)
            for size_key, need in all_needed.items():
                available = inventory.get(size_key, 0) if inventory else 0
                if available >= need:
                    covered += 1

            coverage = int(covered / total_sizes * 100) if total_sizes > 0 else 0

            # 库存使用详情
            inv_parts = []
            for size_key in sorted(from_inv.keys()):
                w, h = size_key.split('x')
                count = from_inv[size_key]
                inv_parts.append(f"{w}×{h}×{count}")

            # 打印需求详情
            print_parts = []
            for size_key in sorted(need_print.keys()):
                w, h = size_key.split('x')
                count = need_print[size_key]
                print_parts.append(f"{w}×{h}×{count}")

            # 构建库存信息行
            inv_line = ""
            if inv_parts:
                inv_line += f"📦 {'+'.join(inv_parts)}"
            if print_parts:
                if inv_line:
                    inv_line += " | "
                inv_line += f"🖨️ {'+'.join(print_parts)}"

            if coverage > 0:
                inv_line += f" | 💰 节省 {coverage}%"

            output.append(f"[{key.upper()}] {name}")
            if inv_line:
                output.append(f"    {inv_line}")
        else:
            # 无库存时显示简单信息
            output.append(f"[{key.upper()}] {name} (全部需要打印)")

        output.append(f"    独特尺寸: {unique_sizes} 种  |  瓦片数: {total_tiles} 块")
        output.append(f"    {', '.join(tile_strs)}")
        output.append("")

    output.append("请选择方案 [A/B/C]: ")

    return "\n".join(output)


def format_scheme_for_display(scheme, inventory=None):
    """格式化单个方案"""
    tiles = scheme.get("tiles", [])

    parts = []
    for t in tiles:
        w = t.get("width") or t[0]
        h = t.get("height") or t[1]
        count = t.get("count", 1)
        parts.append(f"{w}×{h}: {count}")

    return ", ".join(parts)


def prepare_project_data(project_name, scheme_data, drawer_specs, stl_files):
    """Prepare data for HTML template"""
    scheme = scheme_data.get("scheme", {})
    stats = scheme_data.get("stats", {})
    inventory_usage = scheme_data.get("inventory_usage", {})

    # Prepare tiles with source info - use a counter to consume inventory quota
    tiles = scheme.get("tiles", [])
    processed_tiles = []
    
    # 获取可变副本用于在处理中扣减
    inv_remaining = {}
    if isinstance(inventory_usage, dict):
        inv_remaining = inventory_usage.get("from_inventory", {}).copy()
    
    for tile in tiles:
        if isinstance(tile, dict):
            w, h = tile['width'], tile['height']
            count = tile.get('count', 1)
        else:
            w, h = tile[0], tile[1]
            count = 1
            
        key = f"{w}x{h}"
        # 确定这一块是否来自库存
        is_from_inv = False
        if inv_remaining.get(key, 0) > 0:
            is_from_inv = True
            inv_remaining[key] -= 1
            
        processed_tiles.append({
            "width": w,
            "height": h,
            "count": count,
            "from_inventory": is_from_inv
        })

    # Prepare drawer info
    drawer_info = []
    for d in drawer_specs:
        drawer_info.append({
            "width": d["width"],
            "depth": d["depth"],
            "copies": d.get("copies", 1)
        })

    # Prepare STL files info
    stl_info = []
    for f in stl_files:
        p = Path(f)
        stl_info.append({
            "name": p.name,
            "path": f"stl/{p.name}",
            "size": p.stat().st_size if p.exists() else 0
        })

    return {
        "project_name": project_name,
        "drawers": drawer_info,
        "scheme": scheme,
        "stats": stats,
        "tiles": processed_tiles,
        "inventory_usage": inventory_usage,
        "stl_files": stl_info,
    }


def generate_print_plan_html(project_path, project_name, scheme_data, drawer_specs, stl_files):
    """Generate HTML print plan"""
    from opengrid.ui.visualizer import Visualizer

    data = prepare_project_data(project_name, scheme_data, drawer_specs, stl_files)

    # Generate SVG with inventory awareness
    v = Visualizer()
    scheme = scheme_data.get("scheme", {})
    inv_usage = scheme_data.get("inventory_usage", {})
    svg = v.generate_assembly_svg(scheme, inventory_usage=inv_usage)

    # Generate HTML
    html = _generate_simple_html(data, svg)

    with open(project_path / "print_plan.html", 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_simple_html(data, svg):
    """Generate beautiful HTML with technical industrial design"""
    template = env.get_template("project_plan.html.j2")
    return template.render(**data, svg=svg)


def generate_comparison_html(scheme_no_inv, scheme_with_inv):
    """
    生成两种方案的对比 HTML 页面

    参数:
        scheme_no_inv: 无库存方案数据 (dict)
        scheme_with_inv: 有库存方案数据 (dict)

    返回:
        HTML 字符串
    """
    from opengrid.ui.comparison_template import COMPARISON_TEMPLATE
    from opengrid.ui.visualizer import Visualizer

    # 错误处理
    if not scheme_no_inv or not scheme_with_inv:
        raise ValueError("方案数据不能为空")

    # 提取尺寸
    dims = scheme_no_inv.get("dimensions", {})
    drawer_width = dims.get("width", 0)
    drawer_depth = dims.get("depth", 0)

    # 提取统计
    stats_no_inv = scheme_no_inv.get("stats", {})
    stats_with_inv = scheme_with_inv.get("stats", {})

    time_no_inv = round(stats_no_inv.get("total_time_min", 0), 1)
    time_with_inv = round(stats_with_inv.get("total_time_min", 0), 1)
    filament_no_inv = round(stats_no_inv.get("filament_main_g", 0), 2)
    filament_with_inv = round(stats_with_inv.get("filament_main_g", 0), 2)

    # 计算节省百分比和绝对值
    time_saved_pct = 0
    filament_saved_pct = 0
    time_saved_abs = round(time_no_inv - time_with_inv, 1)
    filament_saved_abs = round(filament_no_inv - filament_with_inv, 2)

    if time_no_inv > 0:
        time_saved_pct = round((time_no_inv - time_with_inv) / time_no_inv * 100, 1)
    if filament_no_inv > 0:
        filament_saved_pct = round((filament_no_inv - filament_with_inv) / filament_no_inv * 100, 1)

    # 判断是否使用库存更优
    is_winner = time_with_inv < time_no_inv

    # 生成 SVG
    v = Visualizer()
    scheme_no = scheme_no_inv.get("scheme", {})
    scheme_with = scheme_with_inv.get("scheme", {})
    inv_usage = scheme_with_inv.get("inventory_usage", {})

    # 使用增强的 Visualizer 生成拼图蓝图
    svg_no_inv = v.generate_assembly_svg(scheme_no)
    svg_with_inv = v.generate_assembly_svg(scheme_with, inventory_usage=inv_usage)

    # 如果无法生成标准 SVG（缺少 splits 数据），则回退到散件模式
    if not svg_no_inv:
        # 内部兜底函数保持原有散件堆放逻辑，但由于上面已经修复了 output_json，这里理论上不会触发
        def get_fallback_svg(scheme_data, is_inventory_scheme=False):
            if not scheme_data: return ""
            tiles = scheme_data.get("tiles", [])
            if not tiles: return ""
            
            cell_size = 20
            padding = 20
            gap = 5
            max_cells_x = 11
            svg_parts = []
            x_offset = padding
            y_offset = padding
            row_height = 0
            max_width = 0
            all_sizes = [t["width"] * t["height"] for t in tiles]
            from_inv = {}
            if is_inventory_scheme and inv_usage:
                from_inv = inv_usage.get("from_inventory", {}).copy()

            for t in tiles:
                w, h = t.get("width", 0), t.get("height", 0)
                if x_offset + w * cell_size > max_cells_x * cell_size + padding + 10:
                    x_offset = padding
                    y_offset += row_height + gap
                    row_height = 0
                key = f"{w}x{h}"
                if is_inventory_scheme and from_inv.get(key, 0) > 0:
                    color = "var(--accent-cyan)"; from_inv[key] -= 1
                elif is_inventory_scheme: color = "var(--accent-orange)"
                else: color = v._get_color_for_size(w, h, all_sizes)
                svg_parts.append(f'<rect x="{x_offset}" y="{y_offset}" width="{w*cell_size-2}" height="{h*cell_size-2}" rx="3" ry="3" fill="{color}" stroke="black" stroke-opacity="0.1" stroke-width="1"/>')
                text_x = x_offset + w * cell_size // 2; text_y = y_offset + h * cell_size // 2
                font_size = min(w, h) * 4
                if font_size < 10: font_size = 10
                svg_parts.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" dominant-baseline="middle" font-size="{font_size}" font-weight="600" fill="white">{w}x{h}</text>')
                x_offset += w * cell_size + gap
                row_height = max(row_height, h * cell_size)
                max_width = max(max_width, x_offset)

            svg_width = max(max_width + padding, 240)
            svg_height = y_offset + row_height + padding
            return f'<svg width="100%" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">{"".join(svg_parts)}</svg>'

        svg_no_inv = get_fallback_svg(scheme_no, False)
        svg_with_inv = get_fallback_svg(scheme_with, True)

    # 瓦片列表
    tiles_no_inv = scheme_no_inv.get("tiles", [])
    tiles_with_inv = scheme_with_inv.get("tiles", [])

    # 构建瓦片 HTML
    def build_tiles_html(tiles, inv_usage=None):
        from collections import Counter
        counts = Counter((t["width"], t["height"]) for t in tiles)
        result = []
        # 创建一个可变副本
        inv_counts = {}
        if inv_usage:
            inv_counts = inv_usage.get("from_inventory", {}).copy()

        for (w, h), cnt in sorted(counts.items(), key=lambda x: x[0][0]*x[0][1], reverse=True):
            key = f"{w}x{h}"
            # 在列表展示中，如果这一类中有库存，标记为库存
            is_inv = inv_counts.get(key, 0) > 0
            cls = "inventory" if is_inv else "print"
            result.append(f'<div class="tile-item {cls}">{w}×{h} ×{cnt}</div>')
        return "".join(result)

    tiles_no_inv_html = build_tiles_html(tiles_no_inv)
    tiles_with_inv_html = build_tiles_html(tiles_with_inv, inv_usage)

    # 汇总卡片
    if is_winner:
        summary_html = f'''
        <div class="summary-card">
            <div class="summary-title">使用库存方案节省</div>
            <div class="summary-stats">
                <div class="summary-stat">
                    <div class="summary-stat-value">{time_saved_pct}%</div>
                    <div class="summary-stat-label">打印时间 (-{time_saved_abs} min)</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-value">{filament_saved_pct}%</div>
                    <div class="summary-stat-label">耗材 (-{filament_saved_abs}g)</div>
                </div>
            </div>
        </div>'''
    else:
        summary_html = ''

    # 准备模板变量
    data = {
        "drawer_width": drawer_width,
        "drawer_depth": drawer_depth,
        "svg_no_inventory": svg_no_inv,
        "svg_with_inventory": svg_with_inv,
        "time_no_inventory": time_no_inv,
        "time_with_inventory": time_with_inv,
        "filament_no_inventory": filament_no_inv,
        "filament_with_inventory": filament_with_inv,
        "tiles_no_inventory": len(tiles_no_inv),
        "tiles_with_inventory": len(tiles_with_inv),
        "unique_no_inventory": stats_no_inv.get("unique_sizes", 0),
        "unique_with_inventory": stats_with_inv.get("unique_sizes", 0),
        "tiles_no_inventory_list": tiles_no_inv_html,
        "tiles_with_inventory_list": tiles_with_inv_html,
        "scheme_with_inventory_winner": "winner" if is_winner else "",
        "scheme_with_inventory_badge": "更优方案" if is_winner else "库存方案",
        "value_class_with_inventory": "green" if is_winner else "cyan",
        "summary_html": summary_html,
    }

    template = env.get_template("comparison.html.j2")
    return template.render(**data)
