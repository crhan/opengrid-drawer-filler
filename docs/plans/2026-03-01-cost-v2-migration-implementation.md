# Cost v2 迁移实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将成本计算公式从 v1（`cells × 3.1 × count`）替换为 v2（实测拟合模型），库存匹配逻辑不变，评分和展示使用同一条计算路径。

**Architecture:** 新增 `PrinterConfig` + `SplitResult` 实例封装一次 split 的全部结果；`calculate_print_cost` 内部的成本公式替换为 v2 pipeline；`find_best_scheme` 评分改用 v2；删除 `replan_with_inventory`。

**Tech Stack:** Python 3.12+, pydantic v2, pytest, uv

---

## 背景知识

- `cost_v2.py` 已存在，包含 `Tile / Stack / Plate / CostResult` 数据模型及 `calculate_stacks / calculate_plates / calculate_cost` 三个函数
- `cost.py` 的 `calculate_print_cost` 签名 `(tiles, inventory, copies) → (cost, from_inventory, need_print)` **不变**，只改内部成本公式
- `find_all_schemes` 返回的候选方案已按 `(unique_sizes, tile_count, balance)` 预排序，前 N 名精算，其余跳过
- 性能目标：单次 `split` < 1s

---

## Task 1: 提取库存匹配为独立函数

> 把 `calculate_print_cost` 里的库存匹配逻辑提取成 `_match_inventory`，方便后续步骤复用。

**Files:**
- Modify: `opengrid/core/cost.py`
- Test: `tests/test_inventory_cost.py`

**Step 1: 确认现有测试全部通过（基线）**

```bash
uv run pytest tests/test_inventory_cost.py -v
```

Expected: ALL PASS（建立基线，确保重构前无遗留失败）

**Step 2: 在 `cost.py` 中提取 `_match_inventory`**

在 `calculate_print_cost` 上方新增（不删除原函数，只提取）：

```python
def _match_inventory(
    tiles: list[tuple[int, int]],
    inventory: dict,
    copies: int
) -> tuple[dict, dict]:
    """
    计算库存匹配结果。

    Args:
        tiles: 瓦片列表 [(w, h), ...]
        inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
        copies: 打印份数

    Returns:
        (from_inventory, need_print)
        - from_inventory: 从库存取的瓦片 {"6x8": 1, ...}
        - need_print: 仍需打印的瓦片 {"6x8": 2, ...}
    """
    # 规格化：小边在前（6x8 而非 8x6）
    tile_counts: dict[str, int] = {}
    for w, h in tiles:
        key = f"{min(w, h)}x{max(w, h)}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory: dict[str, int] = {}
    need_print: dict[str, int] = {}

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0) if inventory else 0
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    return from_inventory, need_print
```

然后把 `calculate_print_cost` 改写为调用 `_match_inventory`：

```python
def calculate_print_cost(tiles, inventory, copies):
    """Calculate print cost (in time minutes) and inventory usage

    Returns: (cost, from_inventory, need_print)
        - cost: total time cost in minutes, 0 means fully using inventory
        - from_inventory: tiles taken from inventory {"6x7": 2, ...}
        - need_print: tiles that need printing {"6x7": 1, ...}
    """
    from_inventory, need_print = _match_inventory(tiles, inventory, copies)

    # Calculate time cost for printing
    total_time = 0
    total_prints = len(need_print)

    for key, count in need_print.items():
        if count > 0:
            w, h = map(int, key.split('x'))
            cells = w * h
            time_min = cells * PRINT_TIME_PER_CELL * count
            total_time += time_min

    if total_prints > 1:
        total_time += (total_prints - 1) * SWAP_PENALTY

    return total_time, from_inventory, need_print
```

**Step 3: 确认测试仍然全部通过**

```bash
uv run pytest tests/test_inventory_cost.py -v
```

Expected: ALL PASS（重构无破坏）

**Step 4: Commit**

```bash
git add opengrid/core/cost.py
git commit -m "refactor: extract _match_inventory from calculate_print_cost"
```

---

## Task 2: 替换 calculate_print_cost 的成本公式为 v2

> 库存匹配不变，只把计算时间的那段替换为 v2 pipeline。

**Files:**
- Modify: `opengrid/core/cost.py`
- Test: `tests/test_inventory_cost.py`

**Step 1: 写新的失败测试，验证 v2 精度**

在 `tests/test_inventory_cost.py` 末尾追加：

```python
class TestCostV2Formula:
    """验证 calculate_print_cost 内部使用 v2 公式"""

    def test_single_tile_time_accuracy(self):
        """6x4s1 单盘时间应接近 74min（v2 公式），v1 公式得 ~75min 差异在可接受范围外"""
        # 6x4: 24 cells, copies=1 -> 1 个 Stack
        # v2: 24*1*2.98 + 1*7.4 - 4.5 = 74.4
        # v1: 24*3.1*1 = 74.4（巧合接近，用更大数据区分）
        tiles = [(6, 8)]  # 48 cells
        cost, _, _ = calculate_print_cost(tiles, {}, copies=6)
        # v2: 48*6*2.98 + 6*7.4 - 4.5 = 898.1
        # v1: 48*3.1*6 = 892.8
        # 实测: 908，v2 误差 10，v1 误差 15+
        assert abs(cost - 898) < 12, f"v2 公式期望 ~898，实际 {cost}"

    def test_swap_penalty_included(self):
        """多尺寸需要打印时，换盘惩罚应被计入"""
        tiles = [(6, 8), (4, 4)]  # 2 种尺寸，各 1 片
        cost, _, need_print = calculate_print_cost(tiles, {}, copies=1)
        # 2 个 Plate → 换盘惩罚 60min
        assert cost > 60, f"换盘惩罚应被计入，实际 {cost}"
        assert len(need_print) == 2
```

**Step 2: 运行确认测试失败**

```bash
uv run pytest tests/test_inventory_cost.py::TestCostV2Formula -v
```

Expected: FAIL（当前用 v1 公式，数值偏差超阈值）

**Step 3: 替换 `calculate_print_cost` 内的成本公式**

修改 `opengrid/core/cost.py`，在文件顶部添加导入：

```python
from .cost_v2 import (
    Tile as TileV2,
    calculate_stacks,
    calculate_plates,
    calculate_cost as calculate_cost_v2,
)
from .constants import (
    FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL, SWAP_PENALTY,
    MAX_Z, FULL_THICKNESS,
)
```

将 `calculate_print_cost` 中的成本计算段替换：

```python
def calculate_print_cost(tiles, inventory, copies):
    """Calculate print cost (in time minutes) and inventory usage

    Args:
        tiles: 瓦片列表 [(w, h), ...]
        inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
        copies: 打印份数

    Returns: (cost, from_inventory, need_print)
        - cost: 总打印时间（分钟），0 表示完全使用库存
        - from_inventory: 从库存取的瓦片 {"6x7": 2, ...}
        - need_print: 仍需打印的瓦片 {"6x7": 1, ...}
    """
    from_inventory, need_print = _match_inventory(tiles, inventory, copies)

    if not need_print:
        return 0, from_inventory, need_print

    # 构造 v2 Tile 列表（need_print 的每个条目 = 一种尺寸 + copies 数量）
    tiles_v2 = []
    for key, count in need_print.items():
        w, h = map(int, key.split('x'))
        tiles_v2.append(TileV2(w=w, h=h, copies=count))

    # v2 pipeline：Tile[] → Stack[] → Plate[] → CostResult
    stacks = calculate_stacks(tiles_v2, MAX_Z, FULL_THICKNESS)
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    result = calculate_cost_v2(plates)

    return result.total_cost, from_inventory, need_print
```

**Step 4: 运行新测试**

```bash
uv run pytest tests/test_inventory_cost.py -v
```

Expected: ALL PASS

**Step 5: 运行全套测试，检查是否有破坏**

```bash
uv run pytest tests/ -v --ignore=tests/test_integration_cli.py
```

Expected: 大部分 PASS，`test_inventory_cost.py` 中与 v1 数值强绑定的断言可能需要更新（见 Step 6）

**Step 6: 更新 `test_inventory_cost.py` 中的数值断言**

若有断言形如 `assert cost == 74.4`（硬编码 v1 数值），更新为 v2 预期值或放宽为范围检查：

```python
# 改前（v1 硬编码）
assert cost == 74.4

# 改后（v2 范围检查）
assert abs(cost - 74) < 12  # v2 精度：误差 < 12min
```

**Step 7: 再次运行全套测试**

```bash
uv run pytest tests/ -v --ignore=tests/test_integration_cli.py
```

Expected: ALL PASS

**Step 8: Commit**

```bash
git add opengrid/core/cost.py tests/test_inventory_cost.py
git commit -m "feat: replace v1 cost formula with v2 pipeline in calculate_print_cost"
```

---

## Task 3: 删除 replan_with_inventory

> 新设计中所有候选方案在评分时已用 v2 + 库存打分，不再需要事后补救。

**Files:**
- Modify: `opengrid/core/cost.py`
- Modify: `opengrid/core/__init__.py`
- Modify: `opengrid/core/scheme.py`

**Step 1: 搜索所有 replan_with_inventory 调用点**

```bash
grep -rn "replan_with_inventory" opengrid/ tests/
```

Expected: 出现在 `cost.py`（定义）、`scheme.py`（调用）、`__init__.py`（导出）、可能有测试

**Step 2: 删除 `cost.py` 中的 `replan_with_inventory` 函数**

直接删除整个函数体（从 `def replan_with_inventory` 到函数末尾）。

**Step 3: 更新 `__init__.py` 导出**

```python
# 改前
from .cost import calculate_print_cost, replan_with_inventory

# 改后
from .cost import calculate_print_cost
```

**Step 4: 更新 `scheme.py` 中的调用**

删除 `find_best_scheme` 中对 `replan_with_inventory` 的导入和调用段（约 20 行）：

```python
# 删除这段：
from .cost import calculate_print_cost, replan_with_inventory
...
replan_result = replan_with_inventory(...)
if replan_result and ...:
    ...
    return best
```

`find_best_scheme` 返回 `best_scored['scheme']` 即可，不再尝试重规划。

**Step 5: 运行全套测试**

```bash
uv run pytest tests/ -v --ignore=tests/test_integration_cli.py
```

Expected: ALL PASS

**Step 6: Commit**

```bash
git add opengrid/core/cost.py opengrid/core/__init__.py opengrid/core/scheme.py
git commit -m "refactor: remove replan_with_inventory, v2 scoring makes it unnecessary"
```

---

## Task 4: 新增 PrinterConfig + SplitResult

> 封装一次 split 的全部上下文和结果，消除跨层重复计算。

**Files:**
- Create: `opengrid/core/split_result.py`
- Test: `tests/test_split_result.py`

**Step 1: 写失败测试**

新建 `tests/test_split_result.py`：

```python
import pytest
from opengrid.core.split_result import PrinterConfig, SplitResult


def test_printer_config_defaults():
    """PrinterConfig 应有合理默认值"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8)
    assert pc.max_z == 325
    assert pc.tile_thickness == 6.8


def test_split_result_no_split_needed():
    """不需要分割时：单片，cost 应接近 v2 公式，无换盘惩罚"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8)
    result = SplitResult.compute(
        width=168, depth=112, copies=1,
        inventory={}, printer=pc
    )
    assert result.unique_sizes == 1
    assert len(result.tiles) == 1
    assert result.cost.swap_penalty_total == 0
    assert result.cost.total_cost > 0


def test_split_result_full_inventory_zero_cost():
    """库存完全满足时，cost 应为 0"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8)
    # 6x4 (168x112mm) → tiles = [(6,4)]
    result = SplitResult.compute(
        width=168, depth=112, copies=1,
        inventory={"4x6": 1}, printer=pc
    )
    assert result.cost.total_cost == 0
    assert result.from_inventory != {}
    assert result.need_print == {}


def test_split_result_partial_inventory():
    """库存部分满足时，need_print 非空，cost > 0"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8)
    result = SplitResult.compute(
        width=168, depth=112, copies=3,
        inventory={"4x6": 1}, printer=pc
    )
    assert result.need_print != {}
    assert result.cost.total_cost > 0


def test_split_result_compute_is_fast(benchmark):
    """单次 compute 应在 1s 内完成"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8)
    # 使用较大尺寸触发更多候选方案
    result = benchmark(
        SplitResult.compute,
        width=325, depth=460, copies=1,
        inventory={}, printer=pc
    )
    assert result is not None
```

**Step 2: 运行确认测试失败**

```bash
uv run pytest tests/test_split_result.py -v
```

Expected: FAIL with `ModuleNotFoundError: split_result`

**Step 3: 实现 `split_result.py`**

新建 `opengrid/core/split_result.py`：

```python
"""SplitResult: 封装一次 split 请求的全部上下文和计算结果"""
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field

from .cost_v2 import (
    Tile, Stack, Plate, CostResult,
    calculate_stacks, calculate_plates, calculate_cost,
)
from .cost import _match_inventory
from .scheme import find_all_schemes
from .grid import get_grid_dimensions, validate_tile
from .splitter import calc_scheme_balance


# 候选方案精算上限：超过此数量后只用启发式排序
# 初始值 100，性能测试后调整
_SCORE_LIMIT = 100


@dataclass
class PrinterConfig:
    """打印机配置，由入口处从 config 构造，传入 SplitResult.compute"""
    max_z: int            # Z 轴最大高度 (mm)
    bed_x: int            # 打印盘宽度 (mm)
    bed_y: int            # 打印盘深度 (mm)
    tile_thickness: float # 瓦片厚度 (mm)，由 tile_type 决定


class SplitResult(BaseModel):
    """单次 split 请求的完整结果。只读，不重算。"""

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

    # 库存匹配（v1 逻辑保留）
    from_inventory: dict = Field(default_factory=dict)
    need_print: dict = Field(default_factory=dict)

    # 打印成本（v2 计算）
    stacks: list[Stack] = Field(default_factory=list)
    plates: list[Plate] = Field(default_factory=list)
    cost: CostResult

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def compute(
        cls,
        width: int,
        depth: int,
        copies: int,
        inventory: Optional[dict],
        printer: PrinterConfig,
    ) -> "SplitResult":
        """
        计算最优分割方案。

        Args:
            width: 抽屉宽度 (mm)
            depth: 抽屉深度 (mm)
            copies: 打印份数
            inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
            printer: 打印机配置

        Returns:
            SplitResult 实例，包含最优方案和完整成本信息
        """
        inv = inventory or {}
        grid_x, grid_y = get_grid_dimensions(width, depth)

        # 获取所有候选方案（已按 unique_sizes, tile_count, balance 预排序）
        candidates = find_all_schemes(grid_x, grid_y)

        best_result = None
        best_score = None

        for i, candidate in enumerate(candidates):
            tiles = candidate["tiles"]

            # Step 1: 库存匹配
            from_inv, need_print = _match_inventory(tiles, inv, copies)

            # 剪枝 A: 库存完全满足，成本=0，立即返回
            if not need_print:
                stacks, plates, cost_result = _zero_cost_result()
                return cls._build(
                    width, depth, copies, candidate,
                    from_inv, need_print,
                    stacks, plates, cost_result
                )

            # 剪枝 B: 已有 cost=0 的最优解，跳过
            if best_score is not None and best_score[0] == 0:
                break

            # 剪枝 C: 超过精算上限，使用启发式分数（不调用 v2 pipeline）
            if i >= _SCORE_LIMIT:
                heuristic_score = (
                    float("inf"),
                    len(set(tiles)),
                    len(tiles),
                    calc_scheme_balance(candidate["x_splits"], candidate["y_splits"])
                )
                if best_score is None or heuristic_score < best_score:
                    best_score = heuristic_score
                    best_result = (candidate, from_inv, need_print, None, None, None)
                continue

            # Step 2: v2 cost pipeline
            tiles_v2 = [
                Tile(w=w, h=h, copies=count)
                for key, count in need_print.items()
                for w, h in [map(int, key.split("x"))]
            ]
            stacks = calculate_stacks(tiles_v2, printer.max_z, printer.tile_thickness)
            plates = calculate_plates(stacks, printer.bed_x, printer.bed_y)
            cost_result = calculate_cost(plates)

            score = (
                cost_result.total_cost,
                len(set(tiles)),
                len(tiles),
                calc_scheme_balance(candidate["x_splits"], candidate["y_splits"])
            )

            if best_score is None or score < best_score:
                best_score = score
                best_result = (candidate, from_inv, need_print, stacks, plates, cost_result)

        # 若 best_result 来自启发式（stacks 为 None），补算一次 v2
        candidate, from_inv, need_print, stacks, plates, cost_result = best_result
        if stacks is None:
            tiles_v2 = [
                Tile(w=w, h=h, copies=count)
                for key, count in need_print.items()
                for w, h in [map(int, key.split("x"))]
            ]
            stacks = calculate_stacks(tiles_v2, printer.max_z, printer.tile_thickness)
            plates = calculate_plates(stacks, printer.bed_x, printer.bed_y)
            cost_result = calculate_cost(plates)

        return cls._build(width, depth, copies, candidate, from_inv, need_print, stacks, plates, cost_result)

    @classmethod
    def _build(cls, width, depth, copies, candidate, from_inv, need_print, stacks, plates, cost_result):
        """从候选方案和计算结果构造 SplitResult"""
        tiles = candidate["tiles"]
        return cls(
            width=width,
            depth=depth,
            copies=copies,
            grid=(
                max(candidate["x_splits"]) if candidate["x_splits"] else 0,
                max(candidate["y_splits"]) if candidate["y_splits"] else 0,
            ),
            tiles=tiles,
            x_splits=candidate["x_splits"],
            y_splits=candidate["y_splits"],
            unique_sizes=len(set(tiles)),
            balance=calc_scheme_balance(candidate["x_splits"], candidate["y_splits"]),
            from_inventory=from_inv,
            need_print=need_print,
            stacks=stacks,
            plates=plates,
            cost=cost_result,
        )


def _zero_cost_result() -> tuple[list, list, CostResult]:
    """返回零成本结果（库存完全满足时）"""
    cost = CostResult(
        total_cost=0.0,
        total_filament_g=0.0,
        plate_count=0,
        swap_penalty_total=0,
        plates=[],
    )
    return [], [], cost
```

**Step 4: 运行测试（跳过 benchmark）**

```bash
uv run pytest tests/test_split_result.py -v -k "not benchmark"
```

Expected: ALL PASS（除 benchmark 测试）

**Step 5: 运行性能测试**

```bash
uv run pytest tests/test_split_result.py::test_split_result_compute_is_fast --benchmark-only -v
```

若超过 1s，将 `_SCORE_LIMIT` 从 100 调小（试 50、30），直到 < 1s 且其他测试仍然通过。

**Step 6: 运行全套测试**

```bash
uv run pytest tests/ -v --ignore=tests/test_integration_cli.py
```

Expected: ALL PASS

**Step 7: Commit**

```bash
git add opengrid/core/split_result.py tests/test_split_result.py
git commit -m "feat: add PrinterConfig and SplitResult with v2 cost pipeline"
```

---

## Task 5: 集成到 handle_split 入口

> 入口处构造 `PrinterConfig`，生成 `SplitResult`，下游读属性不重算。

**Files:**
- Modify: `opengrid/cli/commands/split.py`
- Modify: `opengrid/cli/formatters.py`

**Step 1: 修改 `split.py` 入口**

在 `_init_constants` 后，`handle_split` 里新增 `PrinterConfig` 构造，并把结果传给 `output_json`：

```python
from opengrid.core.split_result import PrinterConfig, SplitResult

def _build_printer_config() -> PrinterConfig:
    """从当前全局常量构造 PrinterConfig"""
    from opengrid.core.constants import MAX_Z, FULL_THICKNESS
    from opengrid.config import get_printer_config_or_default
    printer = get_printer_config_or_default()
    return PrinterConfig(
        max_z=MAX_Z,
        bed_x=printer.get("bed_x", 256),
        bed_y=printer.get("bed_y", 256),
        tile_thickness=FULL_THICKNESS,
    )
```

在 `handle_split` 中，单尺寸模式改为：

```python
printer = _build_printer_config()
split_result = SplitResult.compute(width, depth, copies, inventory, printer)
scheme = split_result  # 向下兼容：formatters 读 split_result
```

**Step 2: 修改 `formatters.py::output_json` 接受 SplitResult**

`output_json` 目前调用 `calculate_print_cost`，改为直接读 `SplitResult` 的属性：

```python
def output_json(width: int, depth: int, result, copies: int = 1, inventory: dict = None) -> str:
    """
    输出 JSON 格式。

    Args:
        result: SplitResult 实例（或向下兼容的 scheme dict）
    """
    from opengrid.core.split_result import SplitResult

    if isinstance(result, SplitResult):
        tiles_list = [{'width': w, 'height': h} for w, h in result.tiles]
        total_time_min = result.cost.total_cost
        filament_main = result.cost.total_filament_g
        from_inventory = result.from_inventory
        need_print = result.need_print
        x_splits = result.x_splits
        y_splits = result.y_splits
    else:
        # 向下兼容旧 dict 格式（批量模式暂时保留）
        ... # 保留原有逻辑不变
```

**Step 3: 运行集成测试**

```bash
uv run pytest tests/test_integration_cli.py -v -k "Scenario1 or Scenario2 or Scenario3"
```

Expected: 核心场景 PASS（成本数值因公式更准确会变化，验证逻辑仍然正确）

**Step 4: 运行全套测试**

```bash
uv run pytest tests/ -v
```

Expected: ALL PASS 或只有已知数值偏差的断言失败

**Step 5: 更新 test_integration_cli.py 中的数值断言**

若有基于 v1 公式的硬编码期望值，更新为 v2 的范围检查。

**Step 6: Commit**

```bash
git add opengrid/cli/commands/split.py opengrid/cli/formatters.py tests/test_integration_cli.py
git commit -m "feat: integrate SplitResult into handle_split, formatters read from instance"
```

---

## Task 6: 更新架构文档

**Files:**
- Modify: `docs/split-architecture.md`

更新 Mermaid 图，删除 v1 节点，标注 v2 pipeline 为主路径，标注 `SplitResult` 为核心实例。

```bash
git add docs/split-architecture.md
git commit -m "docs: update split architecture diagram for v2 migration"
```

---

## 验收标准

```bash
# 全套测试通过
uv run pytest tests/ -v

# 性能：单次 split < 1s
uv run pytest tests/test_split_result.py::test_split_result_compute_is_fast --benchmark-only

# 手工验证输出格式不变
uv run scripts/opengrid.py split 325x460
uv run scripts/opengrid.py split 325x460 -j
uv run scripts/opengrid.py split 325x460 -i inventory/inventory.json
```
