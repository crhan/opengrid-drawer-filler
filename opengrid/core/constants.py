"""Core constants for openGrid calculations"""

# Grid dimensions
TILE_SIZE = 28  # mm per cell
MIN_TILE = 2    # minimum tile size in cells

# Tile thickness by type (mm)
TILE_THICKNESS = {
    "Full": 6.8,
    "Lite": 4.0,
    "Heavy": 13.8
}

# Vertical stacking 物理参数
# STACK_GAP_MM 同时被 opengrid/core/cost_v2.py（计算 Z 高度成本）和 opengrid/stl/wrapper.scad
# （SCAD 端实际堆叠 translate Z 步长）使用，任何一处改了都会让"成本估算"和"实物高度"对不上。
# 别在别处硬编码 0.4。
STACK_GAP_MM = 0.4

# Filament estimates (based on 实测数据)
FILAMENT_MAIN_PER_CELL = 1.13
FILAMENT_SUPPORT_PER_CELL = 0.06
PRINT_TIME_PER_CELL = 3.1

# Swap penalty for color changes (minutes)
SWAP_PENALTY = 60

# Preset drawer sizes
PRESETS = {
    "klean": (270, 170, "Klean件盒"),
    "ikea-sunda": (360, 500, "IKEA Sunda"),
    "ikea-kal": (360, 500, "IKEA KAL"),
    "ikea-alex": (360, 500, "IKEA Alex"),
    "standard": (400, 400, "标准抽屉"),
    "small": (300, 300, "小抽屉"),
    "medium": (400, 400, "中抽屉"),
    "large": (500, 500, "大抽屉"),
}
