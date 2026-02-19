# Batch 模式全局优化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 batch 模式下增加全局优化功能，考虑跨抽屉的分割方案选择，最小化总打印次数。

**Architecture:** 新增三个核心函数：find_all_schemes 生成所有可行方案，calculate_total_prints 计算打印次数，optimize_batch_global 作为主优化入口。

**Tech Stack:** Python, pytest

---

## Task 1: find_all_schemes 函数

**Files:**
- Modify: `scripts/split_calc.py` (在 find_best_scheme 函数后添加)
- Test: `tests/test_split_calc.py` (新增 TestFindAllSchemes 类)

**Step 1: 写失败的测试**

```python
class TestFindAllSchemes:
    def test_returns_list(self):
        schemes = find_all_schemes(17, 15)
        assert isinstance(schemes, list)
        assert len(schemes) > 0

    def test_all_schemes_valid(self):
        schemes = find_all_schemes(17, 15)
        for scheme in schemes:
            for w, h in scheme['tiles']:
                assert validate_tile(w, h)

    def test_scheme_completeness(self):
        schemes = find_all_schemes(10, 10)
        # 10x10 不需要分割，应该返回空列表（只有原始尺寸）
        # 或者返回包含原始方案的特殊列表
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_split_calc.py::TestFindAllSchemes -v`
Expected: FAIL with "find_all_schemes not defined"

**Step 3: 写最小实现**

```python
def find_all_schemes(x, y):
    """生成某个抽屉的所有有效分割方案"""
    # 先检查是否需要分割
    if validate_tile(x, y):
        return [{
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
        }]

    all_schemes = []

    # 遍历所有分割组合
    for x_parts in range(2, 8):
        for y_parts in range(1, 5):
            total_tiles = x_parts * y_parts
            if total_tiles > 20:
                continue

            x_splits = split_with_limit(x, x_parts, MAX_X)
            if not x_splits:
                continue

            y_splits = split_with_limit(y, y_parts, MAX_Y)
            if not y_splits:
                continue

            for xs in x_splits:
                for ys in y_splits:
                    tiles = []
                    valid = True
                    for xd in xs:
                        for yd in ys:
                            if not validate_tile(xd, yd):
                                valid = False
                                break
                            tiles.append((xd, yd))

                    if not valid:
                        continue

                    all_schemes.append({
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': tiles,
                    })

    return all_schemes
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_split_calc.py::TestFindAllSchemes -v`
Expected: PASS

**Step 5: 提交**

```bash
git add scripts/split_calc.py tests/test_split_calc.py
git commit -m "feat: add find_all_schemes function"
```

---

## Task 2: calculate_total_prints 函数

**Files:**
- Modify: `scripts/split_calc.py`
- Test: `tests/test_split_calc.py`

**Step 1: 写失败的测试**

```python
def test_calculate_total_prints_basic():
    # 模拟两个抽屉，各一个瓦片
    batch_results = [
        {'width': 400, 'depth': 400, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
    ]
    schemes = [batch_results[0]['scheme']]

    total, details = calculate_total_prints(batch_results, schemes)
    assert total >= 1
    assert 'prints' in details

def test_calculate_total_prints_multiple(self):
    # 两个抽屉共享瓦片尺寸
    batch_results = [
        {'width': 400, 'depth': 400, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
        {'width': 280, 'depth': 280, 'copies': 1, 'scheme': {'tiles': [(10, 10)]}},
    ]
    schemes = [r['scheme'] for r in batch_results]

    total, details = calculate_total_prints(batch_results, schemes)
    # 共享瓦片应该只打印一次
    assert details[(10, 10)]['print_count'] == 1
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_split_calc.py::test_calculate_total_prints_basic -v`
Expected: FAIL with "calculate_total_prints not defined"

**Step 3: 写最小实现**

```python
def calculate_total_prints(batch_results, schemes):
    """计算给定方案组合的总打印次数"""
    # 合并所有瓦片
    all_tiles = {}
    for result, scheme in zip(batch_results, schemes):
        if result is None or scheme is None:
            continue
        copies = result['copies']
        for w, h in scheme['tiles']:
            key = (w, h)
            if key not in all_tiles:
                all_tiles[key] = 0
            all_tiles[key] += copies

    # 计算每个尺寸的打印次数
    max_stacks = get_max_stacks()
    total_prints = 0
    details = {}

    for (w, h), stacks in all_tiles.items():
        prints_needed = (stacks + max_stacks - 1) // max_stacks
        total_prints += prints_needed
        details[(w, h)] = {
            'stacks': stacks,
            'print_count': prints_needed
        }

    return total_prints, details
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_split_calc.py::test_calculate_total_prints_basic -v`
Expected: PASS

**Step 5: 提交**

```bash
git add scripts/split_calc.py tests/test_split_calc.py
git commit -m "feat: add calculate_total_prints function"
```

---

## Task 3: optimize_batch_global 函数

**Files:**
- Modify: `scripts/split_calc.py`
- Test: `tests/test_split_calc.py` (新增 TestOptimizeBatchGlobal 类)

**Step 1: 写失败的测试**

```python
class TestOptimizeBatchGlobal:
    def test_basic_functionality(self):
        results = [
            calculate_single(265, 365, copies=1),
            calculate_single(325, 365, copies=1),
        ]
        optimized = optimize_batch_global(results)
        assert optimized is not None
        assert 'schemes' in optimized
        assert 'total_prints' in optimized

    def test_print_count_reduced_or_equal(self):
        # 优化后的打印次数应该 <= 优化前
        results = [
            calculate_single(265, 365, copies=2),
            calculate_single(325, 365, copies=2),
            calculate_single(315, 365, copies=2),
        ]

        # 计算优化前的打印次数
        _, before_details = calculate_total_prints(
            results,
            [r['scheme'] for r in results]
        )
        before_total = sum(d['print_count'] for d in before_details.values())

        # 优化后
        optimized = optimize_batch_global(results)
        after_total = optimized['total_prints']

        assert after_total <= before_total

    def test_same_as_original_when_already_optimal(self):
        # 如果独立最优就是全局最优，应该返回相同方案
        results = [calculate_single(400, 400, copies=1)]

        optimized = optimize_batch_global(results)
        assert optimized['total_prints'] == 1
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_split_calc.py::TestOptimizeBatchGlobal -v`
Expected: FAIL with "optimize_batch_global not defined"

**Step 3: 写最小实现**

```python
def optimize_batch_global(batch_results):
    """贪心 + 局部搜索优化"""
    if not batch_results:
        return None

    # 步骤1：各自找最优作为初始解
    initial_schemes = [r['scheme'] if r else None for r in batch_results]

    # 计算初始解的打印次数
    initial_total, _ = calculate_total_prints(batch_results, initial_schemes)

    # 步骤2：为每个抽屉生成所有方案
    all_options = []
    for result in batch_results:
        if result is None:
            all_options.append([None])
            continue
        x, y = result['grid']
        schemes = find_all_schemes(x, y)
        all_options.append(schemes)

    # 步骤3：找最优组合（简化版：只尝试交换相邻抽屉的方案）
    best_schemes = initial_schemes
    best_total = initial_total

    # 对每个抽屉，尝试其他方案，看能否减少打印次数
    for i, options in enumerate(all_options):
        if len(options) <= 1:
            continue

        for option in options:
            # 构建新组合
            test_schemes = best_schemes.copy()
            test_schemes[i] = option

            # 检查是否有效（不能有 None）
            if None in test_schemes:
                continue

            total, _ = calculate_total_prints(batch_results, test_schemes)
            if total < best_total:
                best_schemes = test_schemes
                best_total = total

    # 返回优化结果
    return {
        'schemes': best_schemes,
        'total_prints': best_total,
        'initial_prints': initial_total,
        'improved': best_total < initial_total
    }
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_split_calc.py::TestOptimizeBatchGlobal -v`
Expected: PASS

**Step 5: 提交**

```bash
git add scripts/split_calc.py tests/test_split_calc.py
git commit -m "feat: add optimize_batch_global function"
```

---

## Task 4: 集成测试与边界情况

**Files:**
- Test: `tests/test_split_calc.py`

**Step 1: 写测试**

```python
def test_empty_batch():
    result = optimize_batch_global([])
    assert result is None

def test_single_drawer():
    results = [calculate_single(400, 400, copies=1)]
    optimized = optimize_batch_global(results)
    assert optimized['total_prints'] == 1

def test_performance_small_batch():
    import time
    results = [
        calculate_single(265, 365, copies=1),
        calculate_single(325, 365, copies=1),
        calculate_single(315, 365, copies=1),
    ]
    start = time.time()
    optimize_batch_global(results)
    elapsed = time.time() - start
    assert elapsed < 1.0  # 应该在1秒内完成
```

**Step 2: 运行测试**

Run: `pytest tests/test_split_calc.py -k "optimize" -v`

**Step 3: 提交**

```bash
git add tests/test_split_calc.py
git commit -m "test: add integration tests for batch optimization"
```

---

## Plan Complete

**Two execution options:**

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
