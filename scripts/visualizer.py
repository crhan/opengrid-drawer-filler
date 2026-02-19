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

    def generate_tiles_image(self, tiles_data):
        """生成瓦片清单图"""
        raise NotImplementedError
