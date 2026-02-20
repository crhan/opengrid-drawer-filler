"""openGrid 打印计划可视化模块"""

import re
from PIL import Image, ImageDraw

TILE_SIZE = 28  # mm


def get_tile_color(size_key, all_sizes):
    """根据瓦片尺寸返回颜色
    尺寸越大颜色越暖（蓝->红）
    """
    if not all_sizes:
        return "hsl(240, 70%, 60%)"  # 默认蓝色

    min_size = min(all_sizes)
    max_size = max(all_sizes)

    if min_size == max_size:
        return "hsl(240, 70%, 60%)"

    normalized = (size_key - min_size) / (max_size - min_size)
    hue = 240 * (1 - normalized)  # 240=蓝, 0=红
    return f"hsl({int(hue)}, 70%, 60%)"


class Visualizer:
    """可视化器"""

    MIN_CELL_SIZE = 20  # 最小格子显示像素
    MAX_CELL_SIZE = 80  # 最大格子显示像素
    PADDING = 40        # 边距
    LABEL_SIZE = 12     # 标签字体大小

    def __init__(self):
        self.tile_size = TILE_SIZE

    def _calculate_cell_size(self, x_splits, y_splits):
        """计算自适应格子大小"""
        total_x = sum(x_splits)
        total_y = sum(y_splits)
        max_cells = max(total_x, total_y)
        target_size = 700 / max_cells
        cell_size = max(self.MIN_CELL_SIZE, min(self.MAX_CELL_SIZE, target_size))
        return int(cell_size)

    def _get_color_for_size(self, width, height, all_sizes):
        """获取瓦片颜色"""
        size = width * height
        return get_tile_color(size, all_sizes)

    def generate_assembly_image(self, scheme_data):
        """生成拼接示意图"""
        x_splits = scheme_data["x_splits"]
        y_splits = scheme_data["y_splits"]

        # 计算所有瓦片尺寸
        all_sizes = [t["width"] * t["height"] for t in scheme_data["tiles"]]

        # 自适应格子大小
        cell_size = self._calculate_cell_size(x_splits, y_splits)

        # 计算画布大小
        total_x = sum(x_splits)
        total_y = sum(y_splits)
        width = total_x * cell_size + 2 * self.PADDING
        height = total_y * cell_size + 2 * self.PADDING

        # 创建图片
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        # 绘制瓦片
        x_offset = self.PADDING
        for x_dim in x_splits:
            y_offset = self.PADDING
            for y_dim in y_splits:
                # 获取颜色
                color = self._get_color_for_size(x_dim, y_dim, all_sizes)
                color_rgb = self._hsl_to_rgb(color)

                # 绘制矩形
                rect = [
                    x_offset,
                    y_offset,
                    x_offset + x_dim * cell_size - 2,
                    y_offset + y_dim * cell_size - 2
                ]
                draw.rectangle(rect, fill=color_rgb, outline='black', width=1)

                # 绘制标签
                label = f"{x_dim}x{y_dim}"
                if x_dim >= 3 and y_dim >= 3:
                    text_x = x_offset + x_dim * cell_size // 2
                    text_y = y_offset + y_dim * cell_size // 2
                    draw.text((text_x - 10, text_y - 5), label, fill='black')

                y_offset += y_dim * cell_size
            x_offset += x_dim * cell_size

        return image

    def _hsl_to_rgb(self, hsl_str):
        """将 hsl 字符串转换为 RGB 元组"""
        match = re.match(r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)', hsl_str)
        if not match:
            return (128, 128, 128)

        h, s, l = int(match.group(1)), int(match.group(2)), int(match.group(3))

        s = s / 100
        l = l / 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2

        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

    def generate_tiles_image(self, tiles_data, title="瓦片清单"):
        """生成瓦片清单图"""
        if not tiles_data:
            return None

        # 计算需要的网格
        n_tiles = len(tiles_data)
        cols = min(4, n_tiles)  # 最多4列
        rows = (n_tiles + cols - 1) // cols

        # 格子大小
        cell_size = 120
        padding = 30
        label_height = 30

        width = cols * cell_size + (cols + 1) * padding
        height = rows * (cell_size + label_height) + 2 * padding + 50  # +50 for title

        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        # 获取所有尺寸用于颜色映射
        all_sizes = [t["width"] * t["height"] for t in tiles_data]

        # 绘制标题
        draw.text((width // 2 - 30, 10), title, fill='black')

        # 绘制每个瓦片
        for i, tile in enumerate(tiles_data):
            col = i % cols
            row = i // cols

            x = padding + col * (cell_size + padding)
            y = 50 + padding + row * (cell_size + label_height + padding)

            # 绘制瓦片方块
            color = self._get_color_for_size(tile["width"], tile["height"], all_sizes)
            color_rgb = self._hsl_to_rgb(color)

            draw.rectangle([x, y, x + cell_size, y + cell_size], fill=color_rgb, outline='black')

            # 绘制标签
            label = f"{tile['width']}x{tile['height']}\n×{tile['count']}"
            draw.text((x + 10, y + cell_size + 5), label, fill='black')

        return image

    def generate_assembly_svg(self, scheme_data):
        """生成拼接图 SVG 代码"""
        x_splits = scheme_data["x_splits"]
        y_splits = scheme_data["y_splits"]

        all_sizes = [t["width"] * t["height"] for t in scheme_data["tiles"]]

        cell_size = 40
        padding = 20

        total_x = sum(x_splits)
        total_y = sum(y_splits)

        width = total_x * cell_size + 2 * padding
        height = total_y * cell_size + 2 * padding

        svg_parts = []
        svg_parts.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')

        x_offset = padding
        for x_dim in x_splits:
            y_offset = padding
            for y_dim in y_splits:
                color = self._get_color_for_size(x_dim, y_dim, all_sizes)

                rect = f'''  <rect x="{x_offset}" y="{y_offset}"
                      width="{x_dim * cell_size - 2}" height="{y_dim * cell_size - 2}"
                      fill="{color}" stroke="black" stroke-width="1">
                  <title>{x_dim}x{y_dim}</title>
              </rect>'''
                svg_parts.append(rect)

                if x_dim >= 3 and y_dim >= 3:
                    text_x = x_offset + x_dim * cell_size // 2
                    text_y = y_offset + y_dim * cell_size // 2
                    label = f'{x_dim}x{y_dim}'
                    text = f'  <text x="{text_x}" y="{text_y}" text-anchor="middle" dominant-baseline="middle">{label}</text>'
                    svg_parts.append(text)

                y_offset += y_dim * cell_size
            x_offset += x_dim * cell_size

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def generate_html(self, plan_data, output_path):
        """生成 HTML 报告"""
        from jinja2 import Template

        scheme = plan_data.get("scheme", {})
        drawer = plan_data.get("drawer", {})
        stats = plan_data.get("stats", {})

        svg = self.generate_assembly_svg(scheme)

        tiles = scheme.get("tiles", [])
        all_sizes = [t["width"] * t["height"] for t in tiles]
        for tile in tiles:
            tile["color"] = self._get_color_for_size(tile["width"], tile["height"], all_sizes)

        template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>openGrid 打印计划</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .info { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .assembly { text-align: center; margin: 20px 0; }
        .tiles { display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }
        .tile { border: 1px solid #ccc; border-radius: 8px; padding: 10px; text-align: center; }
        .tile-color { width: 60px; height: 60px; border-radius: 4px; margin: 0 auto 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #f5f5f5; }
    </style>
</head>
<body>
    <h1>openGrid 打印计划</h1>

    <div class="info">
        <p><strong>抽屉尺寸:</strong> {{ drawer.width }}mm x {{ drawer.depth }}mm</p>
        <p><strong>分割方案:</strong> {{ scheme.x_parts }}x{{ scheme.y_parts }}</p>
        <p><strong>瓦片数量:</strong> {{ stats.total_tiles }} 块 ({{ stats.unique_sizes }} 种尺寸)</p>
        <p><strong>打印次数:</strong> {{ stats.total_prints }} 次</p>
    </div>

    <h2>拼接示意图</h2>
    <div class="assembly">
        {{ svg | safe }}
    </div>

    <h2>瓦片清单</h2>
    <div class="tiles">
        {% for tile in tiles %}
        <div class="tile">
            <div class="tile-color" style="background: {{ tile.color }};"></div>
            <div>{{ tile.width }}x{{ tile.height }}</div>
            <div>x{{ tile.count }}</div>
        </div>
        {% endfor %}
    </div>

    <h2>详细统计</h2>
    <table>
        <tr><th>尺寸</th><th>数量</th><th>单片耗材</th><th>打印次数</th></tr>
        {% for tile in tiles %}
        <tr>
            <td>{{ tile.width }}x{{ tile.height }}</td>
            <td>{{ tile.count }}</td>
            <td>约 {{ (tile.width * tile.height * 1.19) | round(1) }}g</td>
            <td>1</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>'''

        t = Template(template)
        html = t.render(
            drawer=drawer,
            scheme=scheme,
            stats=stats,
            tiles=tiles,
            svg=svg
        )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def generate_plan_html(self, project_data, output_path):
        """生成完整的打印计划 HTML（带库存扣减提示）

        Args:
            project_data: {
                "project_name": "...",
                "drawer": {"width": 485, "depth": 425},
                "printer": {...},
                "scheme": {...},
                "tiles": [...],
                "stats": {...},
                "svg": "...",
                "inventory_usage": {...},
                "stl_files": [...],
                "script_path": "..."
            }
            output_path: 输出 HTML 路径
        """
        from jinja2 import Template

        template = self._get_plan_template()
        html = template.render(**project_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _get_plan_template(self):
        """获取打印计划 HTML 模板"""
        return Template('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>openGrid 打印计划 - {{ project_name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-top: 0; }
        h2 { color: #666; font-size: 18px; margin-top: 20px; }
        .info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .info-item { background: #f9f9f9; padding: 12px; border-radius: 8px; }
        .info-label { color: #999; font-size: 12px; }
        .info-value { font-size: 18px; font-weight: 600; color: #333; }
        .tile-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
        .tile { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 16px; border-radius: 8px; text-align: center; min-width: 80px; }
        .tile .size { font-size: 20px; font-weight: bold; }
        .tile .count { font-size: 14px; opacity: 0.9; }
        .tile.from-inventory { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .tile.need-print { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        .assembly { text-align: center; margin: 20px 0; }
        .steps { counter-reset: step; }
        .step { position: relative; padding-left: 40px; margin-bottom: 16px; }
        .step:before { counter-increment: step; content: counter(step);
                       position: absolute; left: 0; top: 0;
                       width: 28px; height: 28px; background: #667eea; color: white;
                       border-radius: 50%; text-align: center; line-height: 28px; }
        #inventory-modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                          background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
        #inventory-modal.show { display: flex; }
        .modal-content { background: white; padding: 24px; border-radius: 12px; max-width: 400px; }
    </style>
</head>
<body>
    <h1>📦 openGrid 打印计划</h1>
    <p style="color: #666;">项目: {{ project_name }}</p>

    <div class="card">
        <h2>基本信息</h2>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">抽屉尺寸</div>
                <div class="info-value">{{ drawer.width }}×{{ drawer.depth }}mm</div>
            </div>
            <div class="info-item">
                <div class="info-label">打印机</div>
                <div class="info-value">{{ printer.model }} ({{ printer.bed_x }}×{{ printer.bed_y }}mm)</div>
            </div>
            <div class="info-item">
                <div class="info-label">分割方案</div>
                <div class="info-value">{{ scheme.x_parts }}×{{ scheme.y_parts }}</div>
            </div>
            <div class="info-item">
                <div class="info-label">预估打印时间</div>
                <div class="info-value">{{ stats.total_time }}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>拼接示意图</h2>
        <div class="assembly">
            {{ svg|safe }}
        </div>
    </div>

    <div class="card">
        <h2>瓦片清单</h2>
        <div class="tile-grid">
            {% for tile in tiles %}
            <div class="tile {% if tile.from_inventory %}from-inventory{% else %}need-print{% endif %}">
                <div class="size">{{ tile.width }}×{{ tile.height }}</div>
                <div class="count">×{{ tile.count }}</div>
                <div class="source">{% if tile.from_inventory %}库存{% else %}需打印{% endif %}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>操作步骤</h2>
        <div class="steps">
            <div class="step">在切片软件中打开 STL 文件进行排版</div>
            <div class="step">选择打印参数（层高 0.2mm，填充 15%）</div>
            <div class="step">开始打印</div>
            <div class="step">打印完成后从库存中扣减瓦片</div>
        </div>
    </div>

    <div id="inventory-modal">
        <div class="modal-content">
            <h3>📦 库存扣减</h3>
            <p>该方案使用了库存瓦片，是否现在从库存中扣减？</p>
            <p id="inventory-usage"></p>
            <button onclick="confirmDeduct()" style="background: #667eea; color: white; padding: 12px 24px;
                        border: none; border-radius: 8px; cursor: pointer; margin-right: 12px;">
                确认扣减
            </button>
            <button onclick="closeModal()" style="background: #ddd; color: #333; padding: 12px 24px;
                        border: none; border-radius: 8px; cursor: pointer;">
                稍后处理
            </button>
        </div>
    </div>

    <script>
    const inventoryUsage = {{ inventory_usage | tojson }};

    window.onload = function() {
        if (Object.keys(inventoryUsage).length > 0) {
            const modal = document.getElementById('inventory-modal');
            const usageText = document.getElementById('inventory-usage');
            const parts = [];
            for (const [size, count] of Object.entries(inventoryUsage)) {
                parts.push(`${size}: ${count} 块`);
            }
            usageText.textContent = parts.join(', ');
            modal.classList.add('show');
        }
    };

    function confirmDeduct() {
        // 打开扣库命令
        window.open('python3 {{ script_path }}/inventory.py deduct ' +
            Object.entries(inventoryUsage).map(([k,v]) => k + ':' + v).join(' '));
        closeModal();
    }

    function closeModal() {
        document.getElementById('inventory-modal').classList.remove('show');
    }
    </script>
</body>
</html>''')
