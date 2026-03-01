from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, TYPE_CHECKING


# 时间计算参数 (基于 12 个实测数据拟合)
TIME_PER_CELL_LAYER = 2.98   # d: 每格每层时间 (min/cell/layer)
TIME_PER_LAYER_TOTAL = 7.4   # k: 每层总开销 c + swap (min/layer)
TIME_PREP = -4.5             # prep: 打印开始准备时间（数学修正项）
SAME_PLATE_PENALTY = 0       # 同盘切换开销（已废弃，每个 Stack 独立计算）
SWAP_PENALTY = 60            # 换盘惩罚

# 耗材计算参数 (g/cell/layer)
FILAMENT_PER_CELL_LAYER = 1.15  # d_filament: 每格每层耗材量
FILAMENT_GAP = 2.6             # gap: 层间 gap 耗材量（每层固定开销）


def calculate_plates(
    stacks: List[Stack],
    plate_width: int,
    plate_depth: int
) -> List[Plate]:
    """
    根据盘面尺寸将 Stacks 分配到各 Plate

    当前实现：每个 Stack 独占一盘
    未来扩展：根据盘面尺寸优化摆放多个 Stacks
    """
    # 当前简化实现：每个 Stack 独占一盘
    return [
        Plate(index=i, stacks=[stack])
        for i, stack in enumerate(stacks)
    ]


def _calculate_stack_cost(stack: Stack, is_first: bool, is_single_stack: bool) -> tuple[float, float]:
    """
    计算单个 Stack 的成本

    参数:
        stack: 打印堆叠
        is_first: 是否为该盘上的第一个 Stack
        is_single_stack: 该盘是否只有这一个 Stack

    返回:
        (time_minutes, filament_grams): 打印时间和耗材量

    公式:
        time = cells * layers * d + layers * k + prep
        filament = cells * layers * d_filament + (layers-1) * gap
    """
    cells = stack.tile.w * stack.tile.h
    layers = stack.count

    # 打印时间 = cells * layers * d + layers * k + prep
    stack_time = cells * layers * TIME_PER_CELL_LAYER
    stack_time += layers * TIME_PER_LAYER_TOTAL
    stack_time += TIME_PREP

    # 耗材 = cells * layers * d_filament + (layers-1) * gap
    stack_filament = cells * layers * FILAMENT_PER_CELL_LAYER
    if layers > 1:
        stack_filament += (layers - 1) * FILAMENT_GAP

    return stack_time, stack_filament


def calculate_cost(plates: List[Plate]) -> CostResult:
    """
    计算打印成本

    参数:
        plates: 打印盘列表

    返回:
        CostResult: 包含总时间、总耗材、盘数、换盘惩罚等

    成本计算公式:
        - 打印时间 = cells * layers * TIME_PER_CELL_LAYER + layers * TIME_PER_LAYER
        - 第一个 Stack 有 TIME_PREP，后续 Stack 有 SAME_PLATE_PENALTY
        - 换盘惩罚 = (plate_count - 1) * SWAP_PENALTY
        - 耗材 = cells * layers * FILAMENT_PER_CELL_LAYER
    """
    total_cost = 0.0
    total_filament = 0.0
    swap_penalty_total = 0
    plate_costs = []

    for plate in plates:
        plate_time = 0.0
        plate_filament = 0.0
        is_single_stack = len(plate.stacks) == 1

        for i, stack in enumerate(plate.stacks):
            stack_time, stack_filament = _calculate_stack_cost(stack, i == 0, is_single_stack)
            plate_time += stack_time
            plate_filament += stack_filament

        plate_costs.append(PlateCost(
            index=plate.index,
            stacks=plate.stacks,
            print_time=plate_time,
            filament_g=plate_filament
        ))

        total_cost += plate_time
        total_filament += plate_filament

    # 换盘惩罚：Plate 数 - 1
    num_plates = len(plates)
    if num_plates > 1:
        swap_penalty_total = (num_plates - 1) * SWAP_PENALTY
        total_cost += swap_penalty_total

    return CostResult(
        total_cost=total_cost,
        total_filament_g=total_filament,
        plate_count=num_plates,
        swap_penalty_total=swap_penalty_total,
        plates=plate_costs
    )


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
