# GridConfig 重构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 消除 constants.py 中的动态全局常量（MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS），改用配置对象显式传递。

**架构:** 新增 GridConfig 数据类，扩展 PrinterConfig，将配置作为参数透传到所有需要它的函数。

**技术栈:** Python dataclass, 无新依赖

---

## 任务总览

| 任务 | 内容 |
|------|------|
| Task 1 | constants.py 清理：删掉动态常量，保留静态常量 |
| Task 2 | 新增 GridConfig 数据类到 grid.py |
| Task 3 | 修改 validate_tile() 接收 GridConfig |
| Task 4 | 修改 normalize_tiles() 接收 GridConfig 并修复旋转逻辑 |
| Task 5 | 修改 find_all_schemes() 接收 GridConfig |
| Task 6 | 修改 get_max_stacks() 接收 PrinterConfig |
| Task 7 | 扩展 PrinterConfig 添加 max_cells_x/max_cells_y |
| Task 8 | 修改 split_result.py 调用链透传配置 |
| Task 9 | 修改 split.py 入口构建配置对象 |
| Task 10 | 清理 core/__init__.py 导出 |
| Task 11 | 运行测试验证 |

---

## Task 1: constants.py 清理

**文件:**
- Modify: `opengrid/core/constants.py:1-70`

**Step 1: 重写 constants.py**

删除 MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS 以及 recalculate_derived_constants 函数：

```python
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
```

**Step 2: 验证**

运行: `python -c "from opengrid.core.constants import TILE_SIZE, MIN_TILE, TILE_THICKNESS; print('OK')"`

预期: 输出 OK

**Step 3: Commit**

```bash
git add opengrid/core/constants.py
git commit -m "refactor: remove dynamic constants from constants.py"
```

---

## Task 2: 新增 GridConfig

**文件:**
- Modify: `opengrid/core/grid.py:1-25`

**Step 1: 添加 dataclass 导入和数据类**

在 grid.py 开头添加：

```python
from dataclasses import dataclass

@dataclass
class GridConfig:
    """网格分割配置"""
    max_cells_x: int      # bed_x // TILE_SIZE
    max_cells_y: int      # bed_y // TILE_SIZE
    tile_size: int = 28
    min_tile: int = 2
```

**Step 2: 验证**

运行: `python -c "from opengrid.core.grid import GridConfig; g = GridConfig(9, 18); print(g.max_cells_x, g.max_cells_y)"`

预期: 输出 `9 18`

**Step 3: Commit**

```bash
git add opengrid/core/grid.py
git commit -m "refactor: add GridConfig dataclass"
```

---

## Task 3: validate_tile 接收 GridConfig

**文件:**
- Modify: `opengrid/core/grid.py:17-20`

**Step 1: 修改 validate_tile**

```python
def validate_tile(w, h, grid_config: GridConfig):
    """Validate if a tile size is within printer limits"""
    return (grid_config.min_tile <= w <= grid_config.max_cells_x and
            grid_config.min_tile <= h <= grid_config.max_cells_y)
```

**Step 2: 更新 get_grid_dimensions 添加 tile_size 参数**

```python
def get_grid_dimensions(width_mm, depth_mm, tile_size=28):
    """Calculate available grid cells for drawer dimensions"""
    x = width_mm // tile_size
    y = depth_mm // tile_size
    return x, y
```

**Step 3: 验证**

运行: `python -c "
from opengrid.core.grid import GridConfig, validate_tile
g = GridConfig(9, 18)
print(validate_tile(5, 6, g))  # True
print(validate_tile(10, 5, g)) # False
"`

预期: 输出 True False

**Step 4: Commit**

```bash
git add opengrid/core/grid.py
git commit -m "refactor: validate_tile accepts GridConfig"
```

---

## Task 4: normalize_tiles 修复旋转逻辑

**文件:**
- Modify: `opengrid/core/scheme.py:11-19`

**Step 1: 修改 normalize_tiles**

```python
def normalize_tiles(tiles, grid_config: GridConfig):
    """Normalize tiles: rotate if it makes the tile valid"""
    normalized = []
    for w, h in tiles:
        if (grid_config.min_tile <= w <= grid_config.max_cells_x and
            grid_config.min_tile <= h <= grid_config.max_cells_y):
            normalized.append((w, h))
        elif (grid_config.min_tile <= h <= grid_config.max_cells_x and
              grid_config.min_tile <= w <= grid_config.max_cells_y):
            normalized.append((h, w))
        else:
            normalized.append((w, h))  # 无效，保留原样
    return normalized
```

**Step 2: 添加 GridConfig 导入**

```python
from .grid import validate_tile, GridConfig
```

**Step 3: 验证**

运行: `python -c "
from opengrid.core.grid import GridConfig
from opengrid.core.scheme import normalize_tiles

g = GridConfig(9, 18)  # max 9x18
tiles = [(10, 5), (4, 10), (3, 3)]
result = normalize_tiles(tiles, g)
print(result)
"`

预期: 输出 [(5, 10), (4, 10), (3, 3)] — 第一块旋转了

**Step 4: Commit**

```bash
git add opengrid/core/scheme.py
git commit -m "refactor: normalize_tiles with symmetric rotation logic"
```

---

## Task 5: find_all_schemes 接收 GridConfig

**文件:**
- Modify: `opengrid/core/scheme.py:124-214`

**Step 1: 修改 find_all_schemes 签名**

```python
def find_all_schemes(x, y, grid_config: GridConfig, max_schemes=2000):
```

**Step 2: 内部替换 MAX_X/MAX_Y**

在函数体内：
- 第144行: `min_x_parts = max(1, int((x + grid_config.max_cells_x - 1) // grid_config.max_cells_x))`
- 第145行: `min_y_parts = max(1, int((y + grid_config.max_cells_y - 1) // grid_config.max_cells_y))`
- 第171行: `x_splits = split_with_limit(x, x_parts, grid_config.max_cells_x, max_results=500)`
- 第175行: `y_splits = split_with_limit(y, y_parts, grid_config.max_cells_y, max_results=500)`

**Step 3: 修改 validate_tile 调用**

在第189行附近:
```python
if not validate_tile(xd, yd, grid_config):
```

**Step 4: 验证**

运行: `python -c "
from opengrid.core.grid import GridConfig
from opengrid.core.scheme import find_all_schemes

g = GridConfig(9, 18)
schemes = find_all_schemes(11, 16, g)
print(f'Found {len(schemes)} schemes')
print(schemes[0])
"`

预期: 输出多个方案，第一个方案的 tiles 都 <= 9x18

**Step 5: Commit**

```bash
git add opengrid/core/scheme.py
git commit -m "refactor: find_all_schemes accepts GridConfig"
```

---

## Task 6: get_max_stacks 接收 PrinterConfig

**文件:**
- Modify: `opengrid/core/grid.py:5-7`

**Step 1: 修改 get_max_stacks**

```python
def get_max_stacks(printer_config):
    """Calculate maximum number of stacks based on Z height"""
    return int(printer_config.max_z // printer_config.tile_thickness)
```

**Step 2: 验证**

运行: `python -c "
from dataclasses import dataclass

@dataclass
class PC:
    max_z: int
    tile_thickness: float

pc = PC(256, 7.2)
from opengrid.core.grid import get_max_stacks
print(get_max_stacks(pc))
"`

预期: 输出 35

**Step 3: Commit**

```bash
git add opengrid/core/grid.py
git commit -m "refactor: get_max_stacks accepts PrinterConfig"
```

---

## Task 7: 扩展 PrinterConfig

**文件:**
- Modify: `opengrid/core/split_result.py:20-27`

**Step 1: 扩展 PrinterConfig**

```python
@dataclass
class PrinterConfig:
    """打印机配置，由入口处从 config 构造，传入 SplitResult.compute"""
    max_z: int            # Z 轴最大高度 (mm)
    bed_x: int           # 打印盘宽度 (mm)
    bed_y: int           # 打印盘深度 (mm)
    tile_thickness: float # 瓦片厚度 (mm)，由 tile_type 决定
    max_cells_x: int      # bed_x // tile_size
    max_cells_y: int     # bed_y // tile_size
```

**Step 2: 验证**

运行: `python -c "
from opengrid.core.split_result import PrinterConfig
p = PrinterConfig(256, 256, 256, 7.2, 9, 9)
print(p.max_cells_x, p.max_cells_y)
"`

预期: 输出 9 9

**Step 3: Commit**

```bash
git add opengrid/core/split_result.py
git commit -m "refactor: extend PrinterConfig with max_cells"
```

---

## Task 8: 修改 split_result.py 调用链

**文件:**
- Modify: `opengrid/core/split_result.py:71-167`

**Step 1: 修改 compute 方法签名**

```python
@classmethod
def compute(
    cls,
    width: int,
    depth: int,
    copies: int,
    inventory: Optional[dict],
    printer: PrinterConfig,
) -> "SplitResult":
```

**Step 2: 构造 GridConfig**

在 compute 方法开头添加：

```python
from .grid import GridConfig

grid_config = GridConfig(
    max_cells_x=printer.max_cells_x,
    max_cells_y=printer.max_cells_y,
    tile_size=28,  # TODO: 从 printer 获取
    min_tile=2
)
```

**Step 3: 修改 find_all_schemes 调用**

```python
candidates = find_all_schemes(grid_x, grid_y, grid_config)
```

**Step 4: 验证**

运行: `python -c "
from opengrid.core.split_result import PrinterConfig, SplitResult

printer = PrinterConfig(
    max_z=256,
    bed_x=256,
    bed_y=256,
    tile_thickness=7.2,
    max_cells_x=9,
    max_cells_y=9
)
result = SplitResult.compute(325, 460, 1, None, printer)
print(f'grid: {result.grid}')
print(f'tiles: {len(result.tiles)}')
"`

预期: 输出 grid 和 tiles 数量

**Step 5: Commit**

```bash
git add opengrid/core/split_result.py
git commit -m "refactor: SplitResult.compute passes GridConfig"
```

---

## Task 9: 修改 split.py 入口

**文件:**
- Modify: `opengrid/cli/commands/split.py:45-57`

**Step 1: 修改 _build_printer_config**

```python
def _build_printer_config() -> PrinterConfig:
    """从当前配置构造 PrinterConfig"""
    config = load_config_or_default()
    printer = get_printer_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    tile_size = config.get("opengrid", {}).get("tile_size", 28)

    from opengrid.core.constants import TILE_THICKNESS
    thickness = TILE_THICKNESS.get(tile_type, 7.2)

    return PrinterConfig(
        max_z=printer.get("max_z", 256),
        bed_x=printer.get("bed_x", 256),
        bed_y=printer.get("bed_y", 256),
        tile_thickness=thickness,
        max_cells_x=printer.get("bed_x", 256) // tile_size,
        max_cells_y=printer.get("bed_y", 256) // tile_size,
    )
```

**Step 2: 删除 _init_constants 调用（如果不再需要）**

检查是否有其他地方需要 _init_constants。如果不需要，保留但简化。

**Step 3: 验证**

运行: `python -c "
from opengrid.cli.commands.split import _build_printer_config
p = _build_printer_config()
print(f'max_cells: {p.max_cells_x}x{p.max_cells_y}')
"`

预期: 输出类似 9x9

**Step 4: Commit**

```bash
git add opengrid/cli/commands/split.py
git commit -m "refactor: build PrinterConfig with max_cells in split.py"
```

---

## Task 10: 清理 core/__init__.py

**文件:**
- Modify: `opengrid/core/__init__.py:1-10`

**Step 1: 删除已移除的导出**

```python
from .constants import (
    TILE_SIZE,
    MIN_TILE,
    FILAMENT_MAIN_PER_CELL,
    FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL,
    SWAP_PENALTY,
    PRESETS,
)

from .grid import GridConfig, get_grid_dimensions, validate_tile, get_max_stacks
from .scheme import find_all_schemes, find_best_scheme, normalize_tiles
from .splitter import split_with_limit, calc_balance, calc_scheme_balance
from .split_result import PrinterConfig, SplitResult
```

**Step 2: 验证**

运行: `python -c "from opengrid.core import GridConfig, PrinterConfig; print('OK')"`

预期: OK

**Step 3: Commit**

```bash
git add opengrid/core/__init__.py
git commit -m "refactor: update core/__init__.py exports"
```

---

## Task 11: 运行测试

**Step 1: 运行全部测试**

```bash
cd /Users/ruohanc/Documents/projects/opengrid_plugin
uv run pytest tests/ -v
```

预期: 全部通过

**Step 2: 如果有失败**

修复失败的测试或代码。常见问题：
- 旧代码仍使用 MAX_X/MAX_Y
- 函数签名不匹配

**Step 3: Commit**

```bash
git add -A
git commit -m "test: run full test suite for GridConfig refactor"
```

---

## 执行选项

**Plan complete and saved to `docs/plans/2026-03-01-grid-config-refactor-implementation.md`. Two execution options:**

**1. Subagent-Driven (当前 session)** - 调度子任务逐个执行，任务间审查

**2. Parallel Session (新 session)** - 在 worktree 中开新 session 批量执行

选哪个？
