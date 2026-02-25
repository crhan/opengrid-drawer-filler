#!/usr/bin/env python3
"""方案展示模块"""

from pathlib import Path


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
    """Prepare data for HTML template

    Args:
        project_name: str
        scheme_data: dict with scheme, stats, inventory_usage
        drawer_specs: list of drawer specs
        stl_files: list of STL file paths

    Returns:
        dict: Data for template rendering
    """
    scheme = scheme_data.get("scheme", {})
    stats = scheme_data.get("stats", {})
    inventory_usage = scheme_data.get("inventory_usage", {})

    # Prepare tiles with source info
    tiles = scheme.get("tiles", [])
    for tile in tiles:
        key = f"{tile['width']}x{tile['height']}"
        tile['from_inventory'] = key in inventory_usage

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
        "tiles": tiles,
        "inventory_usage": inventory_usage,
        "stl_files": stl_info,
    }


def generate_print_plan_html(project_path, project_name, scheme_data, drawer_specs, stl_files):
    """Generate HTML print plan

    Args:
        project_path: Path to project directory
        project_name: str
        scheme_data: dict
        drawer_specs: list
        stl_files: list
    """
    from opengrid.ui.visualizer import Visualizer

    data = prepare_project_data(project_name, scheme_data, drawer_specs, stl_files)

    # Generate SVG
    v = Visualizer()
    scheme = scheme_data.get("scheme", {})
    svg = v.generate_assembly_svg(scheme)

    # Generate HTML
    html = _generate_simple_html(data, svg)

    with open(project_path / "print_plan.html", 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_simple_html(data, svg):
    """Generate beautiful HTML with technical industrial design"""
    from jinja2 import Template

    template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>openGrid 打印计划 - {{ project_name }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0b;
            --bg-secondary: #141416;
            --bg-tertiary: #1c1c1f;
            --border-subtle: #2a2a2e;
            --border-active: #3d3d42;
            --text-primary: #f0f0f2;
            --text-secondary: #8b8b94;
            --text-muted: #5a5a63;
            --accent-orange: #ff6b35;
            --accent-orange-dim: #cc5529;
            --accent-cyan: #00d4ff;
            --accent-cyan-dim: #00a8cc;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Noto Sans SC', 'JetBrains Mono', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: -1;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-subtle);
            animation: fadeInDown 0.5s ease;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange-dim));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 20px;
            color: white;
            font-family: 'JetBrains Mono', monospace;
        }

        .header-title h1 {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }

        .header-title p {
            font-size: 13px;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }

        .status-badge {
            padding: 6px 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            font-size: 12px;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-badge::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--accent-orange);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 20px;
            transition: border-color 0.3s ease;
            animation: fadeInUp 0.5s ease backwards;
        }

        .card:nth-child(1) { animation-delay: 0.1s; }
        .card:nth-child(2) { animation-delay: 0.2s; }
        .card:nth-child(3) { animation-delay: 0.3s; }
        .card:nth-child(4) { animation-delay: 0.4s; }

        .card:hover {
            border-color: var(--border-active);
        }

        .card-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
            margin-bottom: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }

        .info-item {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border-subtle);
        }

        .info-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            margin-bottom: 8px;
            font-family: 'JetBrains Mono', monospace;
        }

        .info-value {
            font-size: 22px;
            font-weight: 600;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }

        .info-value span {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 400;
        }

        .svg-container {
            display: flex;
            justify-content: center;
            padding: 30px;
            background: var(--bg-tertiary);
            border-radius: 12px;
            border: 1px solid var(--border-subtle);
        }

        .svg-container svg {
            max-width: 100%;
            height: auto;
        }

        .tile-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px;
        }

        .tile-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .tile-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }

        .tile-card.from-inventory::before {
            background: var(--accent-cyan);
        }

        .tile-card.need-print::before {
            background: var(--accent-orange);
        }

        .tile-card:hover {
            transform: translateY(-4px);
            border-color: var(--border-active);
        }

        .tile-card.from-inventory:hover {
            box-shadow: 0 8px 30px rgba(0, 212, 255, 0.15);
        }

        .tile-card.need-print:hover {
            box-shadow: 0 8px 30px rgba(255, 107, 53, 0.15);
        }

        .tile-size {
            font-size: 24px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            margin-bottom: 8px;
        }

        .tile-card.from-inventory .tile-size {
            color: var(--accent-cyan);
        }

        .tile-card.need-print .tile-size {
            color: var(--accent-orange);
        }

        .tile-count {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .tile-source {
            font-size: 11px;
            margin-top: 10px;
            padding: 4px 10px;
            border-radius: 12px;
            display: inline-block;
        }

        .tile-card.from-inventory .tile-source {
            background: rgba(0, 212, 255, 0.15);
            color: var(--accent-cyan);
        }

        .tile-card.need-print .tile-source {
            background: rgba(255, 107, 53, 0.15);
            color: var(--accent-orange);
        }

        .file-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            transition: all 0.2s ease;
        }

        .file-item:hover {
            border-color: var(--border-active);
            background: var(--bg-primary);
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .file-icon {
            width: 40px;
            height: 40px;
            background: var(--bg-secondary);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        .file-name {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: var(--text-primary);
        }

        .file-meta {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .file-btn {
            padding: 10px 18px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .file-btn:hover {
            background: var(--accent-orange);
            border-color: var(--accent-orange);
            color: white;
        }

        .template-btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 14px 28px;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-orange-dim));
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            font-family: 'Noto Sans SC', sans-serif;
        }

        .template-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(255, 107, 53, 0.3);
        }

        .stats-row {
            display: flex;
            gap: 12px;
            margin-top: 20px;
            flex-wrap: wrap;
        }

        .stat-tag {
            padding: 8px 14px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            font-size: 13px;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-tag strong {
            color: var(--text-primary);
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }

        @media (max-width: 600px) {
            .container {
                padding: 24px 16px;
            }

            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }

            .info-grid {
                grid-template-columns: 1fr;
            }

            .tile-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-left">
                <div class="logo">OG</div>
                <div class="header-title">
                    <h1>{{ project_name }}</h1>
                    <p>openGrid 打印计划</p>
                </div>
            </div>
            <div class="status-badge">等待打印</div>
        </header>

        <div class="card">
            <div class="card-title">抽屉信息</div>
            <div class="info-grid">
                {% for drawer in drawers %}
                <div class="info-item">
                    <div class="info-label">尺寸</div>
                    <div class="info-value">{{ drawer.width }}×{{ drawer.depth }}<span>mm</span></div>
                </div>
                <div class="info-item">
                    <div class="info-label">数量</div>
                    <div class="info-value">{{ drawer.copies }}<span>份</span></div>
                </div>
                {% endfor %}
                {% if stats %}
                <div class="info-item">
                    <div class="info-label">预估时间</div>
                    <div class="info-value">{{ stats.get('total_time', '—') }}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">预估耗材</div>
                    <div class="info-value">{{ stats.get('total_filament', '—') }}</div>
                </div>
                {% endif %}
            </div>
        </div>

        {% if svg %}
        <div class="card">
            <div class="card-title">拼接示意图</div>
            <div class="svg-container">
                {{ svg|safe }}
            </div>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-title">瓦片清单</div>
            <div class="tile-grid">
                {% for tile in tiles %}
                <div class="tile-card {% if tile.from_inventory %}from-inventory{% else %}need-print{% endif %}">
                    <div class="tile-size">{{ tile.width }}×{{ tile.height }}</div>
                    <div class="tile-count">×{{ tile.count }}</div>
                    <div class="tile-source">{% if tile.from_inventory %}库存{% else %}需打印{% endif %}</div>
                </div>
                {% endfor %}
            </div>
            {% if inventory_usage %}
            <div class="stats-row">
                <div class="stat-tag">使用库存: <strong>{{ inventory_usage|length }}</strong> 种尺寸</div>
            </div>
            {% endif %}
        </div>

        {% if stl_files %}
        <div class="card">
            <div class="card-title">STL 文件</div>
            <div class="file-list">
                {% for stl in stl_files %}
                <div class="file-item">
                    <div class="file-info">
                        <div class="file-icon">📦</div>
                        <div>
                            <div class="file-name">{{ stl.name }}</div>
                            <div class="file-meta">{{ stl.path }}</div>
                        </div>
                    </div>
                    <a href="{{ stl.path }}" class="file-btn" target="_blank">打开</a>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-title">切片模板</div>
            <a href="openGrid_h2d.3mf" class="template-btn" onclick="event.preventDefault(); window.open('openGrid_h2d.3mf', '_blank');">
                <span>📐</span> 在 OrcaSlicer 中打开模板
            </a>
        </div>
    </div>
</body>
</html>'''

    t = Template(template)
    return t.render(**data, svg=svg)


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

    # 计算节省百分比
    time_saved_pct = 0
    filament_saved_pct = 0
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

    # 处理 x_splits/y_splits 缺失情况
    def get_svg(scheme_data, drawer_dims=None):
        if not scheme_data:
            return ""
        if "x_splits" in scheme_data and "y_splits" in scheme_data:
            return v.generate_assembly_svg(scheme_data)
        # 从 tiles 简单生成 SVG
        tiles = scheme_data.get("tiles", [])
        if not tiles:
            return ""

        # 计算布局：按宽度累积，自动换行
        # 假设格子大小为 28mm (TILE_SIZE)
        tile_size = 28
        cell_size = 20  # SVG 中每个格子的像素大小
        padding = 20
        gap = 5

        # 计算每行最大宽度（不超过 11 个格子，即 325mm）
        max_cells_x = 11

        # 按位置累积计算布局
        svg_parts = []
        x_offset = padding
        y_offset = padding
        row_height = 0
        max_width = 0

        for t in tiles:
            w, h = t.get("width", 0), t.get("height", 0)

            # 检查是否需要换行
            if x_offset + w * cell_size > max_cells_x * cell_size + padding:
                x_offset = padding
                y_offset += row_height + gap
                row_height = 0

            color = v._get_color_for_size(w, h, [t["width"]*t["height"] for t in tiles])

            # 绘制矩形
            svg_parts.append(f'<rect x="{x_offset}" y="{y_offset}" width="{w*cell_size-2}" height="{h*cell_size-2}" fill="{color}" stroke="black" stroke-width="1"/>')

            # 绘制文字（根据瓦片大小调整字体）
            text_x = x_offset + w * cell_size // 2
            text_y = y_offset + h * cell_size // 2
            font_size = min(w, h) * 3
            if font_size < 10:
                font_size = 10
            svg_parts.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" dominant-baseline="middle" font-size="{font_size}" fill="white" style="text-shadow: 1px 1px 2px black;">{w}x{h}</text>')

            # 更新位置
            x_offset += w * cell_size + gap
            row_height = max(row_height, h * cell_size)
            max_width = max(max_width, x_offset)

        svg_width = max_width + padding
        svg_height = y_offset + row_height + padding

        svg_parts.insert(0, f'<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">')
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    svg_no_inv = get_svg(scheme_no)
    svg_with_inv = get_svg(scheme_with)

    # 瓦片列表
    tiles_no_inv = scheme_no_inv.get("tiles", [])
    tiles_with_inv = scheme_with_inv.get("tiles", [])
    inv_usage = scheme_with_inv.get("inventory_usage", {})

    # 构建瓦片 HTML
    def build_tiles_html(tiles, inv_usage=None):
        from collections import Counter
        counts = Counter((t["width"], t["height"]) for t in tiles)
        result = []
        for (w, h), cnt in counts.items():
            is_inv = inv_usage and inv_usage.get("from_inventory", {}).get(f"{w}x{h}", 0) > 0
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
                    <div class="summary-stat-label">打印时间</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-value">{filament_saved_pct}%</div>
                    <div class="summary-stat-label">耗材</div>
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

    return COMPARISON_TEMPLATE.substitute(data)
