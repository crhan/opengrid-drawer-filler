from pydantic import BaseModel, Field
from typing import List


class Tile(BaseModel):
    """基础面板"""
    w: int = Field(ge=1)  # 宽度 (cells)，必须 >= 1
    h: int = Field(ge=1)  # 高度 (cells)，必须 >= 1
    copies: int = Field(default=1, ge=1)  # 需要打印的数量，必须 >= 1


class Stack(BaseModel):
    """打印堆叠"""
    tile: Tile   # 基础面板
    count: int = Field(ge=1)  # 层数（垂直堆叠的 Tile 数量），必须 >= 1


class Plate(BaseModel):
    """打印盘"""
    index: int = Field(ge=0)        # 盘索引，从 0 开始
    stacks: List[Stack]            # 该盘上的 Stacks


class PlateCost(BaseModel):
    """单盘成本"""
    index: int = Field(ge=0)           # 盘索引，从 0 开始
    stacks: List[Stack]
    print_time: float = Field(ge=0)   # 打印时间（分钟），必须 >= 0
    filament_g: float = Field(ge=0)   # 耗材用量（克），必须 >= 0


class CostResult(BaseModel):
    """成本计算结果"""
    total_cost: float = Field(ge=0)           # 总时间（分钟），必须 >= 0
    total_filament_g: float = Field(ge=0)   # 总耗材（克），必须 >= 0
    plate_count: int = Field(ge=0)           # 盘数，必须 >= 0
    swap_penalty_total: int = Field(ge=0)    # 换盘惩罚总额，必须 >= 0
    plates: List[PlateCost]                  # 每盘详情


def calculate_stacks(
    tiles: List[Tile],
    max_z: int,
    tile_thickness: float,
    stack_gap: float = 0.4
) -> List[Stack]:
    """
    根据 Z 高度限制计算 Stack 划分

    参数:
        tiles: 基础面板列表
        max_z: 打印机 Z 轴限制 (mm)
        tile_thickness: 单层瓦片厚度 (mm)
        stack_gap: Stack 之间的空气间隙 (mm)

    返回:
        Stack 列表，每个 Stack 包含一个 Tile 和堆叠层数

    高度计算：
        - 总高度 = n × tile_thickness + (n-1) × stack_gap
        - 最大层数 = floor((max_z + stack_gap) / (tile_thickness + stack_gap))

    均匀分配：超过最大层数时，尽量均匀分成多个 Stack
    """
    # 计算每 Stack 最大层数
    max_per_stack = int((max_z + stack_gap) / (tile_thickness + stack_gap))
    if max_per_stack < 1:
        max_per_stack = 1

    result = []

    for tile in tiles:
        copies = tile.copies
        # 均匀分配：计算需要多少个 Stack
        num_stacks = (copies + max_per_stack - 1) // max_per_stack
        base_count = copies // num_stacks
        remainder = copies % num_stacks

        for i in range(num_stacks):
            # 前 remainder 个 Stack 多分一个
            count = base_count + (1 if i < remainder else 0)
            if count > 0:
                result.append(Stack(tile=tile, count=count))

    return result
