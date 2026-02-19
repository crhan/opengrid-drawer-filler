# 库存感知评分系统修复计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复库存感知评分系统的两个问题：1) find_best_scheme 不会自动重新规划 2) 库存使用不检查上限

**Architecture:** 在 split_calc.py 中修改 find_best_scheme 和 optimize_batch_global 函数

**Tech Stack:** Python, pytest

---

## Task 1: 将验证场景编写为单元测试（场景 1-7 全部）

**Files:**
- Modify: `tests/test_inventory_cost.py` (添加场景 1, 2, 3, 4, 5, 6a, 6b, 7a, 7b 测试)

### Step 1: 添加所有场景测试用例

根据 `docs/verification-report.md`，添加以下测试类：

```python
# ====== 场景 1: 精确匹配 ======

class TestScenario1ExactMatch:
    """场景1: 精确匹配 - 成本 = 0"""

    def test_exact_match_full_inventory(self):
        """库存足够时，成本应为0"""
        # 库存：6x7 有 2 个，需求：2 个 6x7 瓦片
        inventory = {'6x7': 2}
        scheme = find_best_scheme(6, 7, inventory=inventory, copies=1)

        assert scheme['cost'] == 0
        assert scheme['from_inventory'] == {'6x7': 2}
        assert scheme['need_print'] == {}


# ====== 场景 2: 部分匹配 ======

class TestScenario2PartialMatch:
    """场景2: 部分匹配 - 只计算差额"""

    def test_partial_match(self):
        """库存不足时只计算差额"""
        # 库存：6x7 有 1 个，需求：2 个 6x7 瓦片
        inventory = {'6x7': 1}
        scheme = find_best_scheme(6, 7, inventory=inventory, copies=1)

        assert scheme['from_inventory'] == {'6x7': 1}
        assert scheme['need_print'] == {'6x7': 1}
        assert scheme['cost'] > 0


# ====== 场景 3: 库存方案选择 ======

class TestScenario3InventorySchemeSelection:
    """场景3: 库存方案选择 - 算法优先选择库存方案"""

    def test_prefers_inventory_scheme(self):
        """验证算法会优先选择能使用库存的方案"""
        # 抽屉：265x360 -> 格子 9x12
        # 库存：6x6 有 5 个
        inventory = {'6x6': 5}
        scheme = find_best_scheme(9, 12, inventory=inventory, copies=1)

        # 应该选择能使用库存的方案
        assert scheme['cost'] < float('inf')


# ====== 场景 4: 批量模式 ======

class TestScenario4BatchMode:
    """场景4: 批量模式 - 全局优化"""

    def test_batch_with_inventory(self):
        """批量优化时考虑库存"""
        batch_results = [
            {'grid': (9, 12), 'scheme': {'tiles': [(6, 9)], 'tile_count': 1}, 'copies': 1},
            {'grid': (11, 13), 'scheme': {'tiles': [(6, 11)], 'tile_count': 1}, 'copies': 1},
        ]
        inventory = {'6x9': 1, '6x11': 1}
        result = optimize_batch_global(batch_results, inventory=inventory)

        assert result is not None
        assert result['cost'] == 0  # 完全使用库存


# ====== 场景 5: 重新规划 ======

class TestScenario5ReplanWithInventory:
    """场景5: 重新规划 - 非精确匹配处理"""

    def test_replan_with_smaller_inventory(self):
        """需求6x9两个，库存6x6有三个 - 应该重新规划"""
        tiles = [(6, 9), (6, 9)]
        inventory = {'6x6': 3}

        result = replan_with_inventory(tiles, inventory, copies=1)

        assert result is not None
        assert result['cost'] > 0  # 仍有成本

    def test_replan_with_exact_inventory(self):
        """精确匹配不需要重新规划"""
        tiles = [(6, 7), (6, 7)]
        inventory = {'6x7': 2}

        result = replan_with_inventory(tiles, inventory, copies=1)

        assert result is None  # 精确匹配返回None


# ====== 场景 6a: 批量+重新规划(3个库存) ======

class TestScenario6a:
    """场景6a: 抽屉1+抽屉2, 库存6x6:3"""

    def test_drawer1_cost_zero(self):
        """抽屉1应使用2个库存，成本为0"""
        result = find_best_scheme(9, 12, inventory={'6x6': 3})
        cost = result.get('cost', 0)
        assert cost == 0, f"期望成本0，实际{cost}"

    def test_drawer2_uses_inventory(self):
        """抽屉2应使用1个库存"""
        result = find_best_scheme(11, 13, inventory={'6x6': 3})
        from_inv = result.get('from_inventory', {})
        assert '6x6' in from_inv, f"期望使用6x6库存，实际{from_inv}"

    def test_total_cost_reduced(self):
        """总成本应低于无库存"""
        s1 = find_best_scheme(9, 12, inventory={'6x6': 3})
        s2 = find_best_scheme(11, 13, inventory={'6x6': 3})
        cost_with = s1.get('cost', 0) + s2.get('cost', 0)

        ns1 = find_best_scheme(9, 12, inventory=None)
        ns2 = find_best_scheme(11, 13, inventory=None)
        cost_no = (calculate_print_cost(ns1['tiles'], {})[0] +
                   calculate_print_cost(ns2['tiles'], {})[0])

        assert cost_with < cost_no, f"有库存成本应更低: {cost_with} vs {cost_no}"


# ====== 场景 6b: 批量+重新规划(5个库存) ======

class TestScenario6b:
    """场景6b: 抽屉1+抽屉2, 库存6x6:5"""

    def test_drawer1_cost_zero(self):
        """抽屉1应使用2个库存，成本为0"""
        result = find_best_scheme(9, 12, inventory={'6x6': 5})
        cost = result.get('cost', 0)
        assert cost == 0, f"期望成本0，实际{cost}"

    def test_inventory_not_exceeded(self):
        """库存使用不应超过5个"""
        s1 = find_best_scheme(9, 12, inventory={'6x6': 5})
        s2 = find_best_scheme(11, 13, inventory={'6x6': 5})
        total_used = (sum(s1.get('from_inventory', {}).values()) +
                      sum(s2.get('from_inventory', {}).values()))
        assert total_used <= 5, f"库存使用不应超过5，实际{total_used}"


# ====== 场景 7a: 3抽屉+重新规划(3个库存) ======

class TestScenario7a:
    """场景7a: 抽屉1+2+3, 库存6x6:3"""

    def test_drawer1_cost_zero(self):
        """抽屉1应成本为0"""
        result = find_best_scheme(9, 12, inventory={'6x6': 3})
        assert result.get('cost', 0) == 0

    def test_inventory_usage_limited(self):
        """库存使用不应超过3个"""
        s1 = find_best_scheme(9, 12, inventory={'6x6': 3})
        s2 = find_best_scheme(11, 13, inventory={'6x6': 3})
        s3 = find_best_scheme(15, 14, inventory={'6x6': 3})
        total_used = (sum(s1.get('from_inventory', {}).values()) +
                      sum(s2.get('from_inventory', {}).values()) +
                      sum(s3.get('from_inventory', {}).values()))
        assert total_used <= 3, f"库存使用不应超过3，实际{total_used}"


# ====== 场景 7b: 3抽屉+重新规划(5个库存) ======

class TestScenario7b:
    """场景7b: 抽屉1+2+3, 库存6x6:5 (最复杂场景)"""

    def test_drawer1_cost_zero(self):
        """抽屉1应成本为0"""
        result = find_best_scheme(9, 12, inventory={'6x6': 5})
        assert result.get('cost', 0) == 0

    def test_inventory_not_exceeded(self):
        """库存使用不应超过5个"""
        s1 = find_best_scheme(9, 12, inventory={'6x6': 5})
        s2 = find_best_scheme(11, 13, inventory={'6x6': 5})
        s3 = find_best_scheme(15, 14, inventory={'6x6': 5})
        total_used = (sum(s1.get('from_inventory', {}).values()) +
                      sum(s2.get('from_inventory', {}).values()) +
                      sum(s3.get('from_inventory', {}).values()))
        assert total_used <= 5, f"库存使用不应超过5，实际{total_used}"

    def test_global_optimization(self):
        """全局优化应生效"""
        s1 = find_best_scheme(9, 12, inventory={'6x6': 5})
        s2 = find_best_scheme(11, 13, inventory={'6x6': 5})
        s3 = find_best_scheme(15, 14, inventory={'6x6': 5})
        cost_with = sum([s.get('cost', 0) for s in [s1, s2, s3]])

        ns1 = find_best_scheme(9, 12, inventory=None)
        ns2 = find_best_scheme(11, 13, inventory=None)
        ns3 = find_best_scheme(15, 14, inventory=None)
        cost_no = sum([calculate_print_cost(s['tiles'], {})[0] for s in [ns1, ns2, ns3]])

        assert cost_with < cost_no, f"全局优化应生效: {cost_with} vs {cost_no}"
```

### Step 2: 运行测试验证

```bash
# 运行所有场景测试
python3 -m pytest tests/test_inventory_cost.py -v -k "Scenario"

# 预期：场景 1-4 应该通过，场景 5-7 部分失败（需要修复）
```

### Step 3: 提交

```bash
git add tests/test_inventory_cost.py
git commit -m "test: add scenario 1-7 verification tests"
```

---

## Task 2: 修复 find_best_scheme 自动重新规划

**Files:**
- Modify: `scripts/split_calc.py` (find_best_scheme 函数，约163-320行)

### Step 1: 修改 find_best_scheme 添加重新规划尝试

在有库存分支中，找到计算成本的循环，添加重新规划逻辑：

```python
# 找到这个位置（约第240-260行）：
for scheme in all_schemes:
    cost, from_inv, need_print = calculate_print_cost(
        scheme['tiles'], inventory, copies
    )

    # 在这里添加重新规划尝试：
    if cost > 0:  # 有打印成本，尝试重新规划
        replanned = replan_with_inventory(scheme['tiles'], inventory, copies)
        if replanned and replanned['cost'] < cost:
            cost = replanned['cost']
            from_inv = replanned['from_inventory']
            need_print = replanned['need_print']
            scheme = {**scheme, 'tiles': replanned['tiles']}

    scored_schemes.append({...})
```

### Step 2: 运行测试验证

```bash
python3 -m pytest tests/test_inventory_cost.py::TestScenario6a -v
```

### Step 3: 提交

```bash
git add scripts/split_calc.py
git commit -m "feat: auto replan in find_best_scheme when inventory doesn't match exactly"
```

---

## Task 3: 修复库存上限检查

**Files:**
- Modify: `scripts/split_calc.py` (optimize_batch_global 函数)

### Step 1: 添加库存跟踪逻辑

在 optimize_batch_global 中，为每个抽屉选择方案时跟踪剩余库存：

```python
def optimize_batch_global(batch_results, inventory=None):
    # 添加库存跟踪
    remaining_inventory = dict(inventory) if inventory else None
    used_inventory = {}

    for i, options in enumerate(all_options):
        # ... 原有逻辑 ...

        # 在选择方案时，优先使用剩余库存
        if remaining_inventory:
            # 尝试每个方案，计算使用剩余库存后的成本
            for option in options:
                # ... 计算成本时使用 remaining_inventory 而非原始 inventory ...

            # 选择最优方案后，更新剩余库存
            best_scheme = selected_scheme
            for key, count in best_scheme.get('from_inventory', {}).items():
                if remaining_inventory.get(key, 0) >= count:
                    remaining_inventory[key] -= count
                    used_inventory[key] = used_inventory.get(key, 0) + count
```

### Step 2: 运行测试验证

```bash
python3 -m pytest tests/test_inventory_cost.py::TestScenario6b::test_inventory_not_exceeded -v
python3 -m pytest tests/test_inventory_cost.py::TestScenario7b::test_inventory_not_exceeded -v
```

### Step 3: 提交

```bash
git add scripts/split_calc.py
git commit -m "feat: track inventory usage in batch optimization to prevent overuse"
```

---

## Task 4: 完整测试验证

### Step 1: 运行所有测试

```bash
python3 -m pytest tests/test_inventory_cost.py -v
python3 -m pytest tests/ -v
```

### Step 2: 手动验证场景

验证所有场景是否通过：

| 场景 | 预期结果 | 实际结果 |
|------|---------|---------|
| 1 | 成本=0，完全使用库存 | ? |
| 2 | 部分匹配，只计算差额 | ? |
| 3 | 优先选择库存方案 | ? |
| 4 | 批量模式全局优化 | ? |
| 5 | 重新规划降低打印成本 | ? |
| 6a | 抽屉1成本=0，库存≤3 | ? |
| 6b | 抽屉1成本=0，库存≤5 | ? |
| 7a | 抽屉1成本=0，库存≤3 | ? |
| 7b | 抽屉1成本=0，库存≤5 | ? |

### Step 3: 提交

```bash
git commit -m "fix: inventory-aware scoring system complete"
```

---

## 执行选择

Plan complete and saved to `docs/plans/2026-02-21-inventory-scoring-fix.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
