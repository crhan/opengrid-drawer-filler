# Cost v2 迁移设计

## 背景

当前 v1 的成本计算公式过于简单（`cells × 3.1 × count`），缺乏 Stack/Plate 概念，与 v2 的实测拟合模型存在显著误差。本次迁移目标：

- **保留**：库存匹配逻辑（v1 行为不变）
- **替换**：成本计算公式（v1 → v2）
- **统一**：方案评分和最终展示使用同一条计算路径

## 核心设计原则

**一次计算，到处读取。** 每次 split 请求生成一个 `SplitResult` 实例，入口处处理所有外部输入，之后所有环节（排序、展示、JSON 输出）只读实例属性，不重算。

## 数据结构

### PrinterConfig

```python
@dataclass
class PrinterConfig:
    max_z: int          # 打印机 Z 轴限制 (mm)
    bed_x: int          # 打印盘宽度 (mm)
    bed_y: int          # 打印盘深度 (mm)
    tile_thickness: float  # 瓦片厚度 (mm)，从 TILE_THICKNESS[tile_type] 读取
```

### SplitResult

```python
class SplitResult(BaseModel):
    # 输入上下文
    width: int
    depth: int
    copies: int

    # 分割方案
    grid: tuple[int, int]
    tiles: list[tuple[int, int]]
    x_splits: list[int]
    y_splits: list[int]
    unique_sizes: int
    balance: float

    # 库存匹配结果（v1 逻辑保留不变）
    from_inventory: dict    # {"6x8": 1, ...}
    need_print: dict        # {"6x8": 2, ...}

    # 打印成本（v2 计算）
    stacks: list[Stack]
    plates: list[Plate]
    cost: CostResult        # total_cost, total_filament_g, plate_count, swap_penalty_total
```

## 算法流程

### 整体流程

```
handle_split(args)
      │
      │ 入口处理：
      │   width, depth, copies = parse_dimensions(args)
      │   inventory = load_inventory(args)
      │   printer = PrinterConfig from config
      │
      ▼
SplitResult.compute(width, depth, copies, inventory, printer)
      │
      ├─ 1. grid = get_grid_dimensions(width, depth)
      ├─ 2. candidates = find_all_schemes(grid.x, grid.y)   # 上限 2000
      ├─ 3. 候选方案评分（含剪枝）
      └─ 4. 选出 best，实例化 SplitResult
```

### 候选方案评分（剪枝策略）

```
for candidate in candidates:

    Step 1: 库存匹配
      from_inv, need_print = inventory_match(candidate.tiles, inventory, copies)

      剪枝 A: need_print 为空 → 成本=0，立即返回（无需继续搜索）

    Step 2: v2 cost pipeline（只算 need_print 部分）
      stacks = calculate_stacks(need_print_tiles, printer.max_z, printer.tile_thickness)
      plates = calculate_plates(stacks, printer.bed_x, printer.bed_y)
      cost   = calculate_cost(plates)

      剪枝 B: 已有 best.cost == 0 → 跳过

    Step 3: 记录 score = (cost.total_cost, unique_sizes, tile_count, balance)
      更新 best
```

**阈值策略（性能目标 < 1s）：**
- 候选方案已按 `(unique_sizes, tile_count, balance)` 预排序
- 前 N 名全量精算（v2 pipeline）
- N 的初始值由测试决定，从 100 开始调整
- 超过 N 后只用启发式排序，不再调用 v2 pipeline
- 启发式排序保证相对最优，不保证全局最优

### 部分库存满足时的 cost 计算

```
inventory = {"6x8": 1}，need_total = {"6x8": 3, "4x4": 2}

库存匹配：
  from_inv   = {"6x8": 1}
  need_print = {"6x8": 2, "4x4": 2}   ← 进入 v2 pipeline

v2 pipeline：
  [Tile(6x8, copies=2), Tile(4x4, copies=2)]
        → [Stack(6x8, count=2), Stack(4x4, count=2)]
        → [Plate(0, [Stack(6x8)]), Plate(1, [Stack(4x4)])]
        → CostResult(total_cost = time(6x8×2) + time(4x4×2) + 1×SWAP_PENALTY)
```

不同候选方案产生不同的 `need_print` 组合，换盘次数自然不同，v2 计算出各自真实成本。

## 被删除的内容

### replan_with_inventory 消除

旧设计需要 `replan_with_inventory` 是因为 v1 打分不精确，事后需要补救。
新设计中所有候选方案在评分阶段就用 v2 + 库存打分，一次搜索直接选出最优，不需要事后补救。

### find_best_scheme 重构

原来的职责（找方案 + 打分）分离：
- 找方案 → `find_all_schemes()` 保留
- 打分 → 移入 `SplitResult.compute()`
- `find_best_scheme` 可作为 `SplitResult.compute()` 的薄包装保留，保持向后兼容

## 调用方影响

| 调用方 | 变化 |
|--------|------|
| `split.py::handle_split` | 入口构造 `PrinterConfig`，改为读 `SplitResult` 属性 |
| `formatters.py::output_json` | 直接读 `result.cost`，删除重复的 `calculate_print_cost` 调用 |
| `scheme.py::find_best_scheme` | 内部调用改为 v2 pipeline，或直接用 `SplitResult.compute()` |
| `cost.py::calculate_print_cost` | 内部成本公式替换为 v2，签名不变（兼容批量场景） |
| `cost.py::replan_with_inventory` | 删除 |
| 测试 | `test_inventory_cost.py` 更新断言数值（公式更准确后数字会变） |

## 文件变更

- 新增：`opengrid/core/split_result.py` — `SplitResult`, `PrinterConfig`
- 修改：`opengrid/core/cost.py` — 内部接入 v2 pipeline
- 修改：`opengrid/core/scheme.py` — `find_best_scheme` 使用 v2 评分
- 修改：`opengrid/cli/commands/split.py` — 入口构造 `PrinterConfig`
- 修改：`opengrid/cli/formatters.py` — 读 `SplitResult`，不重算
- 删除：`cost.py::replan_with_inventory`
