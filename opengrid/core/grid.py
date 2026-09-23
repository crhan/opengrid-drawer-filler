"""Grid dimension calculations"""
from dataclasses import dataclass

from .constants import TILE_SIZE, TILE_THICKNESS, STACK_GAP_MM


@dataclass
class GridConfig:
    """网格分割配置"""
    max_cells_x: int      # bed_x // TILE_SIZE
    max_cells_y: int      # bed_y // TILE_SIZE
    tile_size: int = 28
    min_tile: int = 2


def max_layers_per_stack(max_z: float, tile_thickness: float, stack_gap: float = STACK_GAP_MM) -> int:
    """一个 Stack 最多能叠几层 Tile。

    n 层实际高度 = n × tile_thickness + (n-1) × stack_gap ≤ max_z
    → n ≤ (max_z + stack_gap) / (tile_thickness + stack_gap)

    tile_thickness 是单块瓦片裸厚（Full 6.8mm），不含层间隙。
    这是唯一的层数上限公式：成本估算、批量合并、slicer generate 校验都走这里，
    否则会出现"算的是 47 层、实际 47 层有 338mm 超出 Z 轴"这类不一致。
    """
    return max(1, int((max_z + stack_gap) / (tile_thickness + stack_gap)))


def get_max_stacks(printer_config):
    """当前打印机单个 Stack 的最大层数（见 max_layers_per_stack）"""
    return max_layers_per_stack(printer_config.max_z, printer_config.tile_thickness)


def get_grid_dimensions(width_mm, depth_mm, tile_size: int = TILE_SIZE):
    """Calculate available grid cells for drawer dimensions

    Args:
        width_mm: drawer width in mm
        depth_mm: drawer depth in mm
        tile_size: grid pitch in mm (default: TILE_SIZE constant)

    Returns:
        (x, y) number of cells in each dimension
    """
    x = width_mm // tile_size
    y = depth_mm // tile_size
    return x, y


def validate_tile(w, h, grid_config: GridConfig):
    """Validate if a tile size is within printer limits

    Args:
        w: tile width in cells
        h: tile height in cells
        grid_config: GridConfig instance with max_cells_x, max_cells_y

    Returns:
        True if tile is within limits
    """
    max_x = grid_config.max_cells_x
    max_y = grid_config.max_cells_y

    return grid_config.min_tile <= w <= max_x and grid_config.min_tile <= h <= max_y
