# GridConfig 重构设计

## 目标

消除 `constants.py` 中的动态全局常量（MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS），改用配置对象显式传递。

## 问题

当前实现通过 `recalculate_derived_constants()` 动态修改全局常量：

```python
MAX_X = 10      # 初始值
MAX_Y = 11
MAX_Z = 325
FULL_THICKNESS = 7.2

def recalculate_derived_constants(bed_x, bed_y, ...):
    global MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS
    MAX_X = bed_x // TILE_SIZE
    MAX_Y = bed_y // TILE_SIZE
    MAX_Z = max_z
    FULL_THICKNESS = base_thickness + ...
```

问题：
1. **引用透明性丧失** — 同样输入的函数在不同时间返回不同结果
2. **隐式依赖** — `scheme.py`, `grid.py` 直接 import 动态常量，形成隐藏耦合
3. **难以测试** — 测试间存在状态污染风险

## 设计

### 1. 保留的静态常量

`constants.py` 仅保留真正静态的定义：

```python
TILE_SIZE = 28
MIN_TILE = 2

TILE_THICKNESS = {
    "Full": 6.8,
    "Lite": 4.0,
    "Heavy": 13.8
}

FILAMENT_MAIN_PER_CELL = 1.13
FILAMENT_SUPPORT_PER_CELL = 0.06
PRINT_TIME_PER_CELL = 3.1
SWAP_PENALTY = 60
PRESETS = {...}
```

### 2. 新增 GridConfig

位置：`opengrid/core/grid.py`

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

### 3. PrinterConfig 扩展

位置：`opengrid/core/split_result.py`

```python
@dataclass
class PrinterConfig:
    max_z: int            # Z 轴限制
    bed_x: int            # 盘面宽度
    bed_y: int            # 盘面深度
    tile_thickness: float # 瓦片厚度
    max_cells_x: int      # bed_x // tile_size
    max_cells_y: int      # bed_y // tile_size
```

### 4. 函数签名修改

| 函数 | 修改 |
|------|------|
| `find_all_schemes(x, y, grid_config)` | 添加 `grid_config: GridConfig` |
| `validate_tile(w, h, grid_config)` | 添加 `grid_config: GridConfig` |
| `normalize_tiles(tiles, grid_config)` | 添加 `grid_config: GridConfig` |
| `get_max_stacks(printer_config)` | 添加 `printer_config: PrinterConfig` |
| `get_grid_dimensions(width, depth, tile_size)` | 添加 `tile_size` 参数 |

### 5. normalize_tiles 修复

修复旋转逻辑，支持对称的瓦片方向规范化：

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

### 6. 调用链

```
handle_split()
    → PrinterConfig(...)
    → SplitResult.compute(..., printer)
        → find_all_schemes(grid_x, grid_y, GridConfig(...))
            → validate_tile(..., grid_config)
            → normalize_tiles(..., grid_config)
            → split_with_limit(..., max_val=grid_config.max_cells_x)
```

### 7. 旧版兼容函数删除

删除以下不再需要的函数和导出：
- `recalculate_derived_constants()` — 删除
- `core/__init__.py` 中 MAX_X, MAX_Y, MAX_Z, FULL_THICKNESS 的导出 — 删除

## 测试

修改后运行现有测试确保行为一致：
```bash
uv run pytest tests/
```

## 风险

- 函数签名变更影响面较大，需全面回归测试
- `cost.py` 中仍有旧代码依赖 PrinterConfig 字典形式，需一并迁移
