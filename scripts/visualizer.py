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
