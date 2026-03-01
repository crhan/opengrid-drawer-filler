from pydantic import BaseModel
from typing import List


class Tile(BaseModel):
    """基础面板"""
    w: int  # 宽度 (cells)
    h: int  # 高度 (cells)
    copies: int = 1  # 需要打印的数量


class Stack(BaseModel):
    """打印堆叠"""
    tile: Tile   # 基础面板
    count: int  # 层数（垂直堆叠的 Tile 数量）


class Plate(BaseModel):
    """打印盘"""
    index: int              # 盘索引
    stacks: List[Stack]    # 该盘上的 Stacks


class PlateCost(BaseModel):
    """单盘成本"""
    index: int
    stacks: List[Stack]
    print_time: float   # 打印时间（分钟）
    filament_g: float   # 耗材用量（克）


class CostResult(BaseModel):
    """成本计算结果"""
    total_cost: float           # 总时间（分钟）
    total_filament_g: float   # 总耗材（克）
    plate_count: int           # 盘数
    swap_penalty_total: int    # 换盘惩罚总额
    plates: List[PlateCost]    # 每盘详情
