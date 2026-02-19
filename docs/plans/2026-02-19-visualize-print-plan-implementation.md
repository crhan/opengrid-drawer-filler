# openGrid 打印计划可视化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 实现打印计划可视化功能，生成 PNG/HTML 格式的拼接示意图和瓦片清单图

**Architecture:** 将可视化逻辑拆分为独立模块 `visualizer.py`，通过 `print_plan.py` 作为入口消费 JSON 方案数据

**Tech Stack:** Python, Pillow (PNG生成), Jinja2 (HTML模板), JSON (数据接口)

---

### Task 1: 创建 visualizer.py 基础框架

**Files:**
- Create: `scripts/visualizer.py`

**Step 1: 创建测试文件**

```python
# tests/test_visualizer.py
import pytest
from scripts.visualizer import Visualizer, get_tile_color

def test_get_tile_color():
    """测试颜色映射函数"""
    # 单一尺寸应该返回固定颜色
    color = get_tile_color(100, [100])
    assert color is not None

    # 最小尺寸应该是蓝色
    color_min = get_tile_color(50, [50, 100])
    assert "240" in color_min  # 蓝色 hue

    # 最大尺寸应该是红色
    color_max = get_tile_color(100, [50, 100])
    assert "0" in color_max or "0," in color_max  # 红色 hue

def test_visualizer_init():
    """测试可视化器初始化"""
    v = Visualizer()
    assert v is not None
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_visualizer.py -v`
Expected: FAIL - module not found

**Step 3: 创建基础 visualizer 模块**

```python
# scripts/visualizer.py
"""openGrid 打印计划可视化模块"""

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
    """可视化器基类"""

    def __init__(self):
        self.tile_size = TILE_SIZE

    def generate_assembly_image(self, scheme_data):
        """生成拼接示意图"""
        raise NotImplementedError

    def generate_tiles_image(self, tiles_data):
        """生成瓦片清单图"""
        raise NotImplementedError
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_visualizer.py::test_get_tile_color -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/visualizer.py tests/test_visualizer.py
git commit -m "feat: add visualizer module with color mapping"
```

---

### Task 2: 实现 PNG 拼接示意图生成

**Files:**
- Modify: `scripts/visualizer.py`
- Create: `tests/test_visualizer_png.py`

**Step 1: 编写测试**

```python
# tests/test_visualizer_png.py
import pytest
from scripts.visualizer import Visualizer, get_tile_color

def test_generate_assembly_image():
    """测试拼接图生成"""
    v = Visualizer()

    # 模拟方案数据
    scheme_data = {
        "x_splits": [9, 8],
        "y_splits": [15],
        "tiles": [
            {"width": 9, "height": 15, "count": 1},
            {"width": 8, "height": 15, "count": 1}
        ]
    }

    # 生成图片
    image = v.generate_assembly_image(scheme_data)

    # 验证图片属性
    assert image is not None
    assert image.width > 0
    assert image.height > 0

def test_adaptive_size():
    """测试自适应尺寸"""
    v = Visualizer()

    # 大尺寸抽屉
    large_scheme = {"x_splits": [10], "y_splits": [11], "tiles": [{"width": 10, "height": 11}]}
    large_img = v.generate_assembly_image(large_scheme)

    # 小尺寸抽屉
    small_scheme = {"x_splits": [3], "y_splits": [3], "tiles": [{"width": 3, "height": 3}]}
    small_img = v.generate_assembly_image(small_scheme)

    # 大图应该比小图大
    assert large_img.width > small_img.width
    assert large_img.height > small_img.height
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_visualizer_png.py -v`
Expected: FAIL - generate_assembly_image not implemented

**Step 3: 实现 PNG 生成功能**

```python
# 在 scripts/visualizer.py 中添加

from PIL import Image, ImageDraw, ImageFont
import math


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
        # 计算需要的总画布大小
        total_x = sum(x_splits)
        total_y = sum(y_splits)

        # 限制最大和最小格子大小
        # 使用较长的边来确定格子大小，保证正方形
        max_cells = max(total_x, total_y)

        # 动态计算：在 MIN_CELL_SIZE 和 MAX_CELL_SIZE 之间
        # 画布目标大小约 600-800 像素
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

                # 转换 hsl 到 rgb (简化处理，使用预设颜色)
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
                # 简化：只在大格子中显示标签
                if x_dim >= 3 and y_dim >= 3:
                    # 计算文字位置（居中）
                    text_x = x_offset + x_dim * cell_size // 2
                    text_y = y_offset + y_dim * cell_size // 2
                    # 简单文字绘制（使用默认字体）
                    draw.text((text_x - 10, text_y - 5), label, fill='black')

                y_offset += y_dim * cell_size
            x_offset += x_dim * cell_size

        return image

    def _hsl_to_rgb(self, hsl_str):
        """将 hsl 字符串转换为 RGB 元组"""
        # 解析 hsl(h, s%, l%) 格式
        import re
        match = re.match(r'hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)', hsl_str)
        if not match:
            return (128, 128, 128)  # 默认灰色

        h, s, l = int(match.group(1)), int(match.group(2)), int(match.group(3))

        # 转换 hsl 到 rgb
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
```

**Step 4: 运行测试验证**

Run: `pytest tests/test_visualizer_png.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/visualizer.py tests/test_visualizer_png.py
git commit -m "feat: add PNG assembly image generation"
```

---

### Task 3: 实现 PNG 瓦片清单图生成

**Files:**
- Modify: `scripts/visualizer.py`

**Step 1: 添加瓦片清单图生成方法**

```python
# 在 Visualizer 类中添加

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
```

**Step 2: 快速测试**

```bash
python3 -c "
from scripts.visualizer import Visualizer
v = Visualizer()
tiles = [{'width': 9, 'height': 15, 'count': 1}, {'width': 8, 'height': 15, 'count': 1}]
img = v.generate_tiles_image(tiles)
print(f'Generated tiles image: {img.width}x{img.height}')
"
```

**Step 3: Commit**

```bash
git add scripts/visualizer.py
git commit -m "feat: add PNG tiles list image generation"
```

---

### Task 4: 创建 print_plan.py 主脚本

**Files:**
- Create: `scripts/print_plan.py`

**Step 1: 编写 print_plan.py**

```python
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
            print("HTML 输出尚未实现")
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
            print("HTML 输出尚未实现")
        else:
            output_text(plan_data)


if __name__ == "__main__":
    main()
```

**Step 2: 测试脚本**

```bash
# 先生成一个 JSON 方案
python3 scripts/split_calc.py 485 425 -j > /tmp/plan.json

# 测试文本输出
python3 scripts/print_plan.py /tmp/plan.json --text

# 测试 PNG 生成
python3 scripts/print_plan.py /tmp/plan.json --png -o /tmp/opengrid_output
ls -la /tmp/opengrid_output/
```

**Step 3: Commit**

```bash
git add scripts/print_plan.py
git commit -m "feat: add print_plan.py CLI script"
```

---

### Task 5: 实现 HTML 报告生成

**Files:**
- Modify: `scripts/visualizer.py`
- Create: `templates/assembly.html` (Jinja2 模板)

**Step 1: 添加 HTML 生成方法**

```python
# 在 scripts/visualizer.py 中添加

def generate_assembly_svg(self, scheme_data):
    """生成拼接图 SVG 代码"""
    x_splits = scheme_data["x_splits"]
    y_splits = scheme_data["y_splits"]

    all_sizes = [t["width"] * t["height"] for t in scheme_data["tiles"]]

    # 计算每个格子的大小
    cell_size = 40  # SVG 中固定大小
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
              <title>{x_dim}×{y_dim}</title>
          </rect>'''
            svg_parts.append(rect)

            # 绘制标签
            if x_dim >= 3 and y_dim >= 3:
                text_x = x_offset + x_dim * cell_size // 2
                text_y = y_offset + y_dim * cell_size // 2
                label = f'{x_dim}×{y_dim}'
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

    # 生成 SVG
    svg = self.generate_assembly_svg(scheme)

    # 瓦片数据
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
        <p><strong>抽屉尺寸:</strong> {{ drawer.width }}mm × {{ drawer.depth }}mm</p>
        <p><strong>分割方案:</strong> {{ scheme.x_parts }}×{{ scheme.y_parts }}</p>
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
            <div>{{ tile.width }}×{{ tile.height }}</div>
            <div>×{{ tile.count }}</div>
        </div>
        {% endfor %}
    </div>

    <h2>详细统计</h2>
    <table>
        <tr><th>尺寸</th><th>数量</th><th>单片耗材</th><th>打印次数</th></tr>
        {% for tile in tiles %}
        <tr>
            <td>{{ tile.width }}×{{ tile.height }}</td>
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
```

**Step 2: 修改 print_plan.py 支持 HTML**

```python
# 在 output_png 函数后添加

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
```

**Step 3: 测试 HTML 生成**

```bash
python3 scripts/print_plan.py /tmp/plan.json --html -o /tmp/opengrid_output
ls -la /tmp/opengrid_output/
```

**Step 4: Commit**

```bash
git add scripts/visualizer.py scripts/print_plan.py
git commit -m "feat: add HTML report generation"
```

---

### Task 6: 集成测试和批量模式

**Files:**
- Modify: `scripts/print_plan.py`

**Step 1: 添加批量模式支持**

```python
# 修改 main() 函数支持批量模式

def main():
    # ... existing code ...

    # 如果有多个文件且指定了批量模式
    if len(args.files) > 1 and (args.png or args.html):
        # 为每个方案生成输出
        for filepath in args.files:
            # ... 处理每个文件 ...

        # 生成合并的清单图
        all_tiles = []
        for filepath in args.files:
            plan_data = load_plan_from_file(filepath)
            tiles = plan_data.get("scheme", {}).get("tiles", [])
            drawer = plan_data.get("drawer", {})
            for tile in tiles:
                tile["source"] = f"{drawer.get('width', 0)}×{drawer.get('depth', 0)}"
                all_tiles.append(tile)

        merged_dir = os.path.join(args.output, "merged")
        os.makedirs(merged_dir, exist_ok=True)

        v = Visualizer()
        merged_img = v.generate_tiles_image(all_tiles, title="合并瓦片清单")
        merged_img.save(os.path.join(merged_dir, "merged_tiles.png"))
        print(f"已保存: {os.path.join(merged_dir, "merged_tiles.png")}")
```

**Step 2: 测试批量模式**

```bash
# 生成多个方案
python3 scripts/split_calc.py -b "265x365 325x365" -j > /tmp/batch.json

# 处理批量
python3 scripts/print_plan.py /tmp/batch*.json --png --html -o /tmp/batch_output
ls -R /tmp/batch_output/
```

**Step 3: Commit**

```bash
git add scripts/print_plan.py
git commit -m "feat: add batch mode support"
```

---

### Task 7: 最终验证

**Step 1: 运行所有测试**

```bash
pytest tests/test_visualizer.py tests/test_visualizer_png.py -v
```

**Step 2: 端到端测试**

```bash
# 生成方案
python3 scripts/split_calc.py 485 425 -j > /tmp/plan.json

# 生成所有输出
python3 scripts/print_plan.py /tmp/plan.json --text --png --html -o /tmp/opengrid_test

# 验证输出
ls -la /tmp/opengrid_test/
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: complete visualize print plan feature"
```

---

## 验收标准

- [ ] `python3 scripts/print_plan.py plan.json --text` 输出文本计划
- [ ] `python3 scripts/print_plan.py plan.json --html` 生成 HTML 报告
- [ ] `python3 scripts/print_plan.py plan.json --png` 生成 PNG 图片
- [ ] 批量模式正常工作
- [ ] 拼接图清晰展示瓦片尺寸和颜色区分
