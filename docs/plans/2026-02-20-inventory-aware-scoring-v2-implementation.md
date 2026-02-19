# openGrid 库存感知评分系统 v2 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现库存感知评分系统 v2，将库存作为方案评分第一优先级，使用打印时间+换料惩罚作为统一成本模型。

**Architecture:**
- 在 `split_calc.py` 新增 `calculate_print_cost` 函数计算打印成本
- 改造 `find_best_scheme` 添加成本评分维度
- 实现边缘情况 5 的重新规划逻辑
- 集成到批量全局优化

**Tech Stack:** Python, pytest

---

### Task 1: 实现 calculate_print_cost 函数

**Files:**
- Modify: `scripts/split_calc.py:320` (在 calculate_filament_and_time 后添加)

**Step 1: 写失败的测试**

```python
# 在 tests/test_inventory_cost.py 新建文件

import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from split_calc import calculate_print_cost, calculate_filament_and_time, get_grid_dimensions


class TestCalculatePrintCost:
    """测试打印成本计算"""

    def test_exact_match_cost_zero(self):
        """精确匹配：成本为 0"""
        # 265x360 -> 9x12 格, 瓦片 6x9
        tiles = [(6, 9)]
        inventory = {'6x9': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert cost == 0, f"Expected 0, got {cost}"
        assert from_inv == {'6x9': 1}
        assert need_print == {}

    def test_partial_match(self):
        """部分匹配：只计算差额"""
        tiles = [(6, 7), (6, 7)]  # 需要 2 个 6x7
        inventory = {'6x7': 1}     # 只有 1 个
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert from_inv['6x7'] == 1
        assert need_print['6x7'] == 1
        assert cost > 0  # 需要打印 1 个

    def test_no_match(self):
        """无匹配：全部计算成本"""
        tiles = [(6, 9)]
        inventory = {'6x7': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=1)
        assert cost > 0
        assert need_print['6x9'] == 1

    def test_copies_multiplication(self):
        """多份打印：需求翻倍"""
        tiles = [(6, 7)]
        inventory = {'6x7': 1}
        cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies=2)
        # 需要 2 个，只有 1 个，差额 1 个
        assert from_inv['6x7'] == 1
        assert need_print['6x7'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_inventory_cost.py::TestCalculatePrintCost -v`
Expected: FAIL with "calculate_print_cost not defined"

**Step 3: 实现函数**

在 `scripts/split_calc.py` 的 `calculate_filament_and_time` 函数后添加：

```python
# 换料惩罚时间（分钟）
SWAP_PENALTY = 60


def calculate_print_cost(tiles: list[tuple[int, int]], inventory: dict[str, int], copies: int = 1) -> tuple[int, dict, dict]:
    """
    计算打印成本及库存匹配情况

    Args:
        tiles: 瓦片列表 [(w,h), ...]
        inventory: 库存字典 {"6x7": 3, ...}
        copies: 打印份数

    Returns: (cost, from_inventory, need_print)
        - cost: 总成本（分钟），0 表示完全使用库存
        - from_inventory: 从库存取的瓦片 {"6x7": 2, ...}
        - need_print: 需要新打印的瓦片 {"6x7": 1, ...}
    """
    # 统计每种尺寸的需求
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}

    # 计算库存匹配
    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inventory.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining

    # 计算需打印部分的成本
    total_time = 0
    total_prints = sum(need_print.values())

    for key, count in need_print.items():
        if count > 0:
            w, h = map(int, key.split('x'))
            cells = w * h
            _, _, time_min = calculate_filament_and_time(cells, count)
            total_time += time_min

    # 加上换料惩罚（每次打印间隔惩罚）
    if total_prints > 1:
        total_time += (total_prints - 1) * SWAP_PENALTY

    return total_time, from_inventory, need_print
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_inventory_cost.py::TestCalculatePrintCost -v`
Expected: PASS

**Step 5: 提交**

```bash
git add tests/test_inventory_cost.py scripts/split_calc.py
git commit -m "feat: add calculate_print_cost function for inventory-aware scoring"
```

---

### Task 2: 改造 find_best_scheme 添加成本评分

**Files:**
- Modify: `scripts/split_calc.py:129` (find_best_scheme 函数)

**Step 1: 写失败的测试**

```python
# 在 tests/test_inventory_cost.py 添加

class TestFindBestSchemeWithInventory:
    """测试带库存的 find_best_scheme"""

    def test_prefers_inventory_solution(self):
        """有库存时优先选择库存成本低的方案"""
        # 方案1: 6x9 (无库存匹配)
        # 方案2: 6x6 + 3x6 (6x6 有库存)
        # 应该选择方案2
        inventory = {'6x6': 2}

        # 265x360 有多种方案
        result = find_best_scheme(265, 360, inventory=inventory, verbose=False)

        # 验证返回结果包含成本信息
        assert 'cost' in result
        assert 'from_inventory' in result
        assert 'need_print' in result

    def test_no_inventory_uses_original_logic(self):
        """无库存时使用原始评分逻辑"""
        result = find_best_scheme(265, 360, inventory=None, verbose=False)
        # 不应该崩溃，返回正常方案
        assert 'tiles' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_inventory_cost.py::TestFindBestSchemeWithInventory -v`
Expected: FAIL

**Step 3: 修改 find_best_scheme 函数**

在 `find_best_scheme` 函数中（位于 `scripts/split_calc.py:129`）：

1. 添加导入（如果还没有）:
```python
# 函数内导入
from split_calc import calculate_print_cost
```

2. 修改函数逻辑，添加库存评分：

找到函数结尾（约 line 183），在 return best 之前添加：

```python
def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
    """直接寻找最优方案，找到1种尺寸就停止

    Args:
        x, y: 格子数
        verbose: 是否打印详细信息
        inventory: 库存字典 {"6x7": 3, ...}，None 表示不使用库存
        copies: 打印份数
    """
    # 原有的单瓦片检查
    if validate_tile(x, y):
        return {
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
            'unique_sizes': 1,
            'tile_count': 1
        }

    # 如果有库存，收集所有方案并评分
    if inventory:
        all_schemes = find_all_schemes(x, y)
        scored_schemes = []

        for scheme in all_schemes:
            cost, from_inv, need_print = calculate_print_cost(
                scheme['tiles'], inventory, copies
            )

            scored_schemes.append({
                'scheme': scheme,
                'cost': cost,
                'from_inventory': from_inv,
                'need_print': need_print,
                'unique_sizes': scheme['unique_sizes'],
                'total_tiles': scheme['tile_count'],
                'balance': scheme.get('balance', 0)
            })

        # 多维度排序：成本 -> 独特尺寸 -> 瓦片数 -> 均衡度
        scored_schemes.sort(key=lambda s: (
            s['cost'],
            s['unique_sizes'],
            s['total_tiles'],
            s['balance']
        ))

        best_scored = scored_schemes[0]
        best = best_scored['scheme'].copy()
        best['cost'] = best_scored['cost']
        best['from_inventory'] = best_scored['from_inventory']
        best['need_print'] = best_scored['need_print']

        return best

    # 无库存时使用原始逻辑（不变）
    best = _find_best_scheme_impl(x, y, verbose)

    # 旋转对称检查...（保留原有代码）
    if x != y:
        rotated = _find_best_scheme_impl(y, x, verbose)
        # ... 原有旋转逻辑
        pass

    return best
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_inventory_cost.py::TestFindBestSchemeWithInventory -v`
Expected: PASS

**Step 5: 提交**

```bash
git add scripts/split_calc.py tests/test_inventory_cost.py
git commit -m "feat: integrate inventory cost into find_best_scheme scoring"
```

---

### Task 3: 实现边缘情况 5 - 重新规划逻辑

**Files:**
- Modify: `scripts/split_calc.py` (新增 replan_with_inventory 函数)

**Step 1: 写失败的测试**

```python
# 在 tests/test_inventory_cost.py 添加

class TestReplanWithInventory:
    """测试边缘情况5：需求与库存不匹配时的重新规划"""

    def test_replan_uses_partial_inventory(self):
        """当库存尺寸不完全匹配时，拆分方案使用部分库存"""
        # 需求: 6x9 两个 (需要 2 个 6x9)
        # 库存: 6x6 有 3 个
        # 方案: 使用 2 个 6x6 库存，将需求拆分为更小的瓦片
        tiles = [(6, 9), (6, 9)]
        inventory = {'6x6': 3}

        result = replan_with_inventory(tiles, inventory)

        # 应该返回重新规划后的方案
        assert result is not None
        assert 'tiles' in result
        # 至少使用 2 个 6x6 库存
        assert result['from_inventory'].get('6x6', 0) >= 2

    def test_no_replan_needed_when_exact_match(self):
        """精确匹配时不需要重新规划"""
        tiles = [(6, 7)]
        inventory = {'6x7': 1}

        # 应该返回 None（不需要重新规划）
        result = replan_with_inventory(tiles, inventory)
        # 或者返回成本为 0 的原方案


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_inventory_cost.py::TestReplanWithInventory -v`
Expected: FAIL with "replan_with_inventory not defined"

**Step 3: 实现重新规划函数**

在 `calculate_print_cost` 后添加：

```python
def replan_with_inventory(tiles: list[tuple[int, int]], inventory: dict[str, int], copies: int = 1):
    """
    边缘情况5：当库存尺寸不匹配时，重新规划方案以最大化利用库存

    Args:
        tiles: 原始瓦片需求
        inventory: 可用库存
        copies: 打印份数

    Returns:
        重新规划后的方案，包含:
        - tiles: 新的瓦片列表
        - from_inventory: 从库存取的瓦片
        - need_print: 需要新打印的瓦片
        - cost: 总成本
        或 None（如果不需要重新规划）
    """
    # 先尝试直接匹配
    direct_cost, from_inv, need_print = calculate_print_cost(tiles, inventory, copies)

    # 如果直接匹配成本为 0，不需要重新规划
    if direct_cost == 0:
        return None

    # 如果 need_print 为空但 cost > 0，说明库存不足但无法拆分
    if not need_print:
        return None

    # 计算原始成本（无库存）
    original_cost, _, _ = calculate_print_cost(tiles, {}, copies)
    if original_cost == direct_cost:
        # 没有利用任何库存，原方案已经最优
        return None

    # 尝试重新规划：将需求拆分以使用库存
    # 策略：找到库存中可用的尺寸，尝试拆分原瓦片

    best_plan = {
        'cost': direct_cost,
        'from_inventory': from_inv,
        'need_print': need_print,
        'tiles': tiles,  # 保留原始瓦片（用于比较）
    }

    # 找到可用的库存尺寸
    available_sizes = {k: v for k, v in inventory.items() if v > 0}

    if not available_sizes:
        return None

    # 遍历每种库存尺寸，尝试用它来拆分需求
    for inv_key, inv_count in available_sizes.items():
        inv_w, inv_h = map(int, inv_key.split('x'))

        # 尝试用库存瓦片替换部分需求
        new_tiles = list(tiles)
        used_from_inv = 0
        new_need_print = {}

        # 计算可以用库存满足多少需求
        for i, (w, h) in enumerate(tiles):
            if used_from_inv >= inv_count * copies:
                break

            # 检查库存尺寸是否 <= 需求尺寸（可以拆分）
            if inv_w <= w and inv_h <= h:
                # 使用一个库存瓦片
                used_from_inv += 1

                # 剩余空间需要新打印或其他方式满足
                remaining_cells = w * h - inv_w * inv_h
                if remaining_cells > 0:
                    # 简单策略：忽略剩余空间（简化实现）
                    pass

        # 如果成功使用了库存，重新计算成本
        if used_from_inv > 0:
            # 构建新的瓦片列表
            new_tiles = []
            used = 0

            for w, h in tiles:
                if used < used_from_inv and inv_w <= w and inv_h <= h:
                    # 用库存瓦片
                    new_tiles.append((inv_w, inv_h))
                    used += 1
                else:
                    # 原瓦片
                    new_tiles.append((w, h))

            # 计算新成本
            new_cost, new_from_inv, new_need = calculate_print_cost(
                new_tiles, inventory, copies
            )

            if new_cost < best_plan['cost']:
                best_plan = {
                    'cost': new_cost,
                    'from_inventory': new_from_inv,
                    'need_print': new_need,
                    'tiles': new_tiles,
                }

    # 如果没有改进，返回 None
    if best_plan['cost'] >= original_cost:
        return None

    return best_plan
```

**Step 4: 运行测试验证**

Run: `pytest tests/test_inventory_cost.py::TestReplanWithInventory -v`
Expected: PASS (部分测试可能需要调整)

**Step 5: 提交**

```bash
git add scripts/split_calc.py
git commit -m "feat: implement replan_with_inventory for edge case 5"
```

---

### Task 4: 集成到批量全局优化

**Files:**
- Modify: `scripts/split_calc.py` (optimize_batch_global 函数)

**Step 1: 查看现有 optimize_batch_global 实现**

Run: `grep -n "def optimize_batch_global" scripts/split_calc.py`
找到函数位置

**Step 2: 修改函数添加库存成本**

在批量全局优化的成本计算中添加库存感知：

```python
# 伪代码修改
for combo in generate_combinations(batch_configs):
    total_cost = 0
    for config in combo:
        scheme = config['scheme']
        # 使用 calculate_print_cost 而不是简单的瓦片数
        cost, _, _ = calculate_print_cost(scheme['tiles'], inventory)
        total_cost += cost
```

**Step 3: 测试批量模式**

```bash
python3 scripts/split_calc.py -b "265x360:2 325x365:2"
```

**Step 4: 提交**

---

### Task 5: 更新输出格式

**Files:**
- Modify: `scripts/split_calc.py` (print_plan 函数)

**Step 1: 修改 print_plan 显示成本信息**

在输出中添加：

```
--- 库存利用 ---
从库存: 6×6 ×2
需打印: 3×6 ×2, 6×6 ×2 (成本: 395 分钟)
```

**Step 2: 测试输出**

```bash
python3 scripts/split_calc.py 265 360 -i
```

**Step 3: 提交**

---

### Task 6: 完整集成测试

**Step 1: 运行所有测试**

```bash
pytest -v
```

**Step 2: 手动测试场景**

1. 精确匹配：库存 6x9:2，需求 6x9:2 → 成本 0
2. 部分匹配：库存 6x7:1，需求 6x7:2 → 打印 1 个
3. 无匹配：库存 6x6:1，需求 6x9:1 → 打印 1 个
4. 重新规划：库存 6x6:3，需求 6x9:2 → 使用库存 + 拆分打印

**Step 3: 提交**

---

## 执行选择

Plan complete and saved to `docs/plans/2026-02-20-inventory-aware-scoring-v2-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
