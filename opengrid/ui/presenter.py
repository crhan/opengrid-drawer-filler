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

            # 按面积（cell数量）计算覆盖率
            total_cells_needed = 0
            cells_covered = 0
            for size_key, need in all_needed.items():
                w, h = map(int, size_key.split("x"))
                area = w * h
                available = inventory.get(size_key, 0) if inventory else 0

                total_cells_needed += need * area
                cells_covered += min(need, available) * area

            coverage = int(cells_covered / total_cells_needed * 100) if total_cells_needed > 0 else 0

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


def _comparison_view(data):
    """把 split --json 的两种输出（单抽屉 / 多抽屉）统一成对比页要的视图

    Returns:
        {
          title, info: [(label, value)],
          time_min, filament_g, total_tiles, unique_sizes,
          tiles: [(w, h, count)],            # 已乘份数，按面积降序
          from_inventory: {"6x7": n},
          drawers: [(label, scheme_for_svg, inventory_usage_or_None)],
        }
    """
    stats = data.get("stats", {})
    inv_usage = data.get("inventory_usage") or {}

    if "drawers" in data:
        drawers = data["drawers"]
        return {
            "title": f"{len(drawers)} 只抽屉",
            "info": [(d["name"], f"{d['width']}×{d['depth']}mm ×{d['copies']}") for d in drawers],
            "time_min": round(stats.get("total_time_min", 0), 1),
            "filament_g": round(stats.get("total_filament_g", 0), 1),
            "total_tiles": stats.get("total_tiles", 0),
            "unique_sizes": stats.get("unique_sizes", 0),
            "tiles": [(t["width"], t["height"], t["count"]) for t in data.get("tiles", [])],
            "from_inventory": inv_usage.get("from_inventory", {}),
            "drawers": [
                (f"{d['name']} ×{d['copies']}", {**d["scheme"], "tiles": d["tiles"]}, d.get("inventory"))
                for d in drawers
            ],
        }

    dims = data.get("dimensions", {})
    copies = dims.get("copies", 1)
    counts = {}
    for t in data.get("tiles", []):
        k = (t["width"], t["height"])
        counts[k] = counts.get(k, 0) + copies
    return {
        "title": f"{dims.get('width', 0)}×{dims.get('depth', 0)} 抽屉",
        "info": [("宽度", f"{dims.get('width', 0)}mm"), ("深度", f"{dims.get('depth', 0)}mm"), ("份数", str(copies))],
        "time_min": round(stats.get("total_time_min", 0), 1),
        "filament_g": round(stats.get("filament_main_g", 0), 1),
        "total_tiles": sum(counts.values()),
        "unique_sizes": stats.get("unique_sizes", len(counts)),
        "tiles": sorted(((w, h, c) for (w, h), c in counts.items()), key=lambda t: t[0] * t[1], reverse=True),
        "from_inventory": inv_usage.get("from_inventory", {}),
        "drawers": [("", data.get("scheme", {}), inv_usage or None)],
    }


def _drawers_svg(view, with_inventory):
    """每只抽屉一张拼接图；多抽屉时加抽屉名做小标题"""
    from opengrid.ui.visualizer import Visualizer
    v = Visualizer()
    parts = []
    for label, scheme, inv in view["drawers"]:
        # 库存方案没用到库存时也传空 dict，保持"库存=青 / 打印=橙"的配色
        svg = v.generate_assembly_svg(scheme, inventory_usage=(inv or {"from_inventory": {}}) if with_inventory else None)
        if label:
            svg = f'<div class="drawer-svg-label">{label}</div>{svg}'
        parts.append(f'<div class="drawer-svg">{svg}</div>')
    return "".join(parts)


def _tiles_html(view, with_inventory):
    from opengrid.core.cost import tile_key
    from_inv = view["from_inventory"] if with_inventory else {}
    result = []
    for w, h, cnt in view["tiles"]:
        used = from_inv.get(tile_key(w, h), 0)
        if used:
            result.append(f'<div class="tile-item inventory">{w}×{h} ×{used}（库存）</div>')
        if cnt - used > 0:
            result.append(f'<div class="tile-item print">{w}×{h} ×{cnt - used}</div>')
    return "".join(result)


def generate_comparison_html(scheme_no_inv, scheme_with_inv):
    """
    生成两种方案的对比 HTML 页面；单抽屉和多抽屉的 split --json 输出都支持

    参数:
        scheme_no_inv: 无库存方案数据 (dict)
        scheme_with_inv: 有库存方案数据 (dict)

    返回:
        HTML 字符串
    """
    if not scheme_no_inv or not scheme_with_inv:
        raise ValueError("方案数据不能为空")
    if ("drawers" in scheme_no_inv) != ("drawers" in scheme_with_inv):
        raise ValueError("两个方案一个是单抽屉、一个是多抽屉，无法对比；请用相同的尺寸参数重新 split")

    a = _comparison_view(scheme_no_inv)
    b = _comparison_view(scheme_with_inv)

    time_saved_abs = round(a["time_min"] - b["time_min"], 1)
    filament_saved_abs = round(a["filament_g"] - b["filament_g"], 1)
    time_saved_pct = round(time_saved_abs / a["time_min"] * 100, 1) if a["time_min"] > 0 else 0
    filament_saved_pct = round(filament_saved_abs / a["filament_g"] * 100, 1) if a["filament_g"] > 0 else 0

    is_winner = b["time_min"] < a["time_min"]

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

    data = {
        "drawer_title": a["title"],
        "drawer_info": a["info"],
        "svg_no_inventory": _drawers_svg(a, with_inventory=False),
        "svg_with_inventory": _drawers_svg(b, with_inventory=True),
        "time_no_inventory": a["time_min"],
        "time_with_inventory": b["time_min"],
        "filament_no_inventory": a["filament_g"],
        "filament_with_inventory": b["filament_g"],
        "tiles_no_inventory": a["total_tiles"],
        "tiles_with_inventory": b["total_tiles"],
        "unique_no_inventory": a["unique_sizes"],
        "unique_with_inventory": b["unique_sizes"],
        "tiles_no_inventory_list": _tiles_html(a, with_inventory=False),
        "tiles_with_inventory_list": _tiles_html(b, with_inventory=True),
        "scheme_with_inventory_winner": "winner" if is_winner else "",
        "scheme_with_inventory_badge": "更优方案" if is_winner else "库存方案",
        "value_class_with_inventory": "green" if is_winner else "cyan",
        "summary_html": summary_html,
    }

    template = env.get_template("comparison.html.j2")
    return template.render(**data)
