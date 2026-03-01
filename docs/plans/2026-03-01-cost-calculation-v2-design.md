# 成本计算逻辑设计

## 概述

重构成本计算逻辑，支持以 Stack 为单位的打印成本计算，并引入 Plate 概念管理换盘惩罚。

## 术语（按规范）

| 术语 | 含义 |
|------|------|
| **Cell** | 最小空间单位，28mm × 28mm |
| **Tile** | 基础面板，由 M×N Cells 组成 |
| **Stack** | Tile 的垂直堆叠。如 7x6s5 = 1 Stack（含 5 层 Tile） |
| **Plate** | 打印盘，当前每盘一个 Stack，未来通过算法优化可容纳多个 |
| **换盘惩罚** | 不同尺寸切换时增加的时间成本（SWAP_PENALTY = 60 分钟） |

## 数据结构

```python
from pydantic import BaseModel
from typing import List

class Tile(BaseModel):
    """基础面板"""
    w: int          # 宽度 (cells)
    h: int          # 高度 (cells)
    copies: int = 1 # 需要打印的数量

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
```

## 函数设计

整体流程：`Tile → calculate_stacks() → Stack → calculate_plates() → Plate → calculate_cost() → CostResult`

### 1. calculate_stacks

根据 Z 高度限制将 Tiles 均匀分配到多个 Stacks。

```python
def calculate_stacks(
    tiles: List[Tile],
    max_z: int,
    tile_thickness: float,  # 瓦片厚度 (Full=6.8, Lite=4.0, Heavy=13.8)
    stack_gap: float = 0.4  # 层间间隙
) -> List[Stack]:
    """
    根据 Z 高度限制计算 Stack 划分

    高度计算：
    - 单层高度 = tile_thickness + stack_gap
    - 总高度 = n × tile_thickness + (n-1) × stack_gap
                = n × (tile_thickness + stack_gap) - stack_gap

    最大层数：max_count = floor((max_z + stack_gap) / (tile_thickness + stack_gap))

    均匀分配：超过最大层数时，尽量均匀分成多个 Stack

    Args:
        tiles: 基础面板列表
        max_z: 打印机 Z 轴最大高度 (mm)
        tile_thickness: 瓦片厚度 (mm)
        stack_gap: 层间间隙 (mm)，默认 0.4

    Returns:
        Stack 列表
    """
```

### 2. calculate_plates

```python
def calculate_plates(
    stacks: List[Stack],
    plate_width: int,   # 盘宽度 (cells)
    plate_depth: int    # 盘深度 (cells)
) -> List[Plate]:
    """
    根据盘面尺寸将 Stacks 分配到各 Plate

    当前实现：每个 Stack 独占一盘
    未来扩展：根据盘面尺寸优化摆放多个 Stacks

    Args:
        stacks: Stack 列表
        plate_width: 盘宽度 (cells)
        plate_depth: 盘深度 (cells)

    Returns:
        Plate 列表
    """
```

### 3. calculate_cost

```python
def calculate_cost(plates: List[Plate]) -> CostResult:
    """
    计算打印成本

    Args:
        plates: Plate 列表

    Returns:
        成本计算结果
    """
```

**计算逻辑：**

1. 对每 Stack：
   - 打印时间 = cells × layers × d + layers × c + (layers-1) × swap + prep
2. 对每 Plate：
   - 换盘惩罚 = (Stack 数 - 1) × SWAP_PENALTY（不同 Stack 间）
   - 同盘开销 = (Stack 数 - 1) × SAME_PLATE_PENALTY（同一盘内切换）
3. 汇总：
   - total_cost = Σ(每 Stack 打印时间) + 换盘惩罚 + 同盘开销
   - plate_count = 盘数

## 时间计算公式

```
单 Stack 打印时间 = cells × layers × d + layers × c + (layers-1) × swap + prep
总成本 = Σ(所有 Stack 时间) + (Plate 数 - 1) × SWAP_PENALTY + (同盘内切换数) × SAME_PLATE_PENALTY
```

**模型参数（基于 12 个实测数据拟合）：**

| 参数 | 值 | 含义 |
|------|-----|------|
| d | 2.98 min/cell/layer | 每格每层时间 |
| k | 7.4 min/layer | 每层总开销 (c + swap) |
| prep | -4.5 min | 打印开始准备时间（数学修正项） |
| SAME_PLATE_PENALTY | 0 min | 同盘切换开销（已废弃，每个 Stack 独立计算） |
| SWAP_PENALTY | 60 min | 换盘惩罚 |

**简化公式：** `time = cells × layers × d + layers × k + prep`

### 耗材计算

**模型：** `grams = cells × layers × d_filament + (layers-1) × gap`

**参数：**

| 参数 | 值 | 含义 |
|------|-----|------|
| d_filament | 1.15 g/cell/layer | 每格每层耗材量 |
| gap | 2.6 g/layer | 层间 gap 耗材量（每层固定开销） |

**验证：**

| 输入 | 计算 | 实际 | 差 |
|------|------|------|-----|
| 6x4s1 | 27.5 | 27.56 | -0.1 |
| 10x8s1 | 91.6 | 88.83 | +2.8 |
| 10x8s2 | 185.8 | 185.35 | +0.5 |
| 6x8s6 | 342.8 | 346.26 | -3.4 |
| 6x7s6 | 301.6 | 304.54 | -3.0 |
| 8x8s5 | 376.9 | 376.34 | +0.5 |
| 5x6s8 | 293.0 | 289.56 | +3.5 |
| 8x9s2 | 167.5 | 165.95 | +1.6 |
| 9x5s12 | 647.0 | 647.03 | 0 |
| 9x5s6 | 322.2 | 321.79 | +0.4 |
| 9x5s3 | 159.8 | 159.20 | +0.6 |
| 6x5s4+6x8s2 | 257.8 | 257.71 | +0.1 |

最大误差：3.5g

## 参考数据验证（12 组数据）

| 输入 | 计算 | 实际 | 差 |
|------|------|------|-----|
| 6x4s1 | 74 | 77 | -3 |
| 10x8s1 | 241 | 232 | +9 |
| 10x8s2 | 487 | 483 | +4 |
| 6x8s6 | 898 | 908 | -10 |
| 6x7s6 | 791 | 802 | -11 |
| 8x8s5 | 986 | 993 | -7 |
| 5x6s8 | 770 | 772 | -2 |
| 8x9s2 | 439 | 438 | +1 |
| 9x5s12 | 1693 | 1684 | +9 |
| 9x5s6 | 844 | 843 | +1 |
| 9x5s3 | 420 | 419 | +1 |
| 6x5s4 + 6x8s2 | 684 | 677 | +7 |

最大误差：11 分钟

## 文件位置

新增文件：`opengrid/core/cost_v2.py`
