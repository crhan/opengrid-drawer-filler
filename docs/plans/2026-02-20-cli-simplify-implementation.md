# CLI 参数简化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 简化 split_calc.py CLI 参数语法，统一单尺寸和批量模式的入口

**Architecture:** 创建统一解析器处理位置参数，根据尺寸数量自动选择单尺寸或批量模式

**Tech Stack:** Python, argparse

---

## 概述

本计划将 split_calc.py 重构为使用统一的 CLI 参数格式：
- `python split_calc.py 485x425` (单尺寸)
- `python split_calc.py 485x425 265x365:2 325x365` (批量)

---

### Task 1: 创建测试文件

**Files:**
- Create: `tests/test_cli_parser.py`

**Step 1: 编写测试**

```python
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.split_calc import parse_dimensions, parse_preset

class TestParseDimensions:
    """测试尺寸参数解析"""

    def test_single_dimension(self):
        """测试单个尺寸解析"""
        result = parse_dimensions(['485x425'])
        assert result == [(485, 425, 1)]

    def test_dimension_with_copies(self):
        """测试带份数的尺寸"""
        result = parse_dimensions(['265x365:2'])
        assert result == [(265, 365, 2)]

    def test_multiple_dimensions(self):
        """测试多个尺寸"""
        result = parse_dimensions(['485x425', '265x365:2', '325x365'])
        assert result == [(485, 425, 1), (265, 365, 2), (325, 365, 1)]

    def test_empty_input(self):
        """测试空输入"""
        result = parse_dimensions([])
        assert result == []

    def test_invalid_format_ignored(self):
        """测试无效格式被忽略"""
        result = parse_dimensions(['invalid', '485x425'])
        assert result == [(485, 425, 1)]

    def test_preset_klean(self):
        """测试预设解析"""
        result = parse_preset('klean')
        assert result == [(270, 170, 1)]

    def test_preset_with_copies(self):
        """测试预设带份数"""
        result = parse_preset('klean', copies=3)
        assert result == [(270, 170, 3)]
```

**Step 2: 运行测试验证失败**

```bash
.venv/bin/python -m pytest tests/test_cli_parser.py -v
```
Expected: FAIL (parse_dimensions 和 parse_preset 未定义)

**Step 3: 提交**
```bash
git add tests/test_cli_parser.py
git commit -m "test: add CLI parser tests"
```

---

### Task 2: 实现统一解析器

**Files:**
- Modify: `scripts/split_calc.py:1-50` (在文件顶部添加解析函数)

**Step 1: 添加解析函数**

在文件顶部 `import` 之后添加：

```python
def parse_dimensions(args):
    """解析位置参数为尺寸列表

    支持格式:
    - 485x425 -> (485, 425, 1)
    - 265x365:2 -> (265, 365, 2)

    Args:
        args: 位置参数列表

    Returns:
        [(width, depth, copies), ...]
    """
    import re
    items = []

    for arg in args:
        # 支持 x 或 × 符号
        match = re.match(r'(\d+)[x×](\d+)(?::(\d+))?', arg)
        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            c = int(match.group(3)) if match.group(3) else 1
            items.append((w, h, c))

    return items


def parse_preset(preset_name, copies=1):
    """解析预设名称为尺寸

    Args:
        preset_name: 预设名称
        copies: 份数

    Returns:
        [(width, depth, copies), ...] 或 None 如果预设不存在
    """
    if preset_name in PRESETS:
        w, h, _ = PRESETS[preset_name]
        return [(w, h, copies)]
    return None
```

**Step 2: 运行测试验证通过**

```bash
.venv/bin/python -m pytest tests/test_cli_parser.py -v
```
Expected: PASS

**Step 3: 提交**
```bash
git add scripts/split_calc.py
git commit -m "feat: add parse_dimensions and parse_preset functions"
```

---

### Task 3: 重构 main 函数

**Files:**
- Modify: `scripts/split_calc.py:1913-2049` (main 函数)

**Step 1: 修改 argparse 参数定义**

找到:
```python
parser.add_argument('width', nargs='?', type=int, help='抽屉宽度(mm)')
parser.add_argument('depth', nargs='?', type=int, help='抽屉深度(mm)')
```

改为:
```python
parser.add_argument('dimensions', nargs='*', type=str,
                   help='尺寸列表，如 485x425 或 265x365:2')
```

**Step 2: 修改 main 函数逻辑**

找到:
```python
# 批量模式处理
if args.batch:
    batch_mode(args.batch, args.verbose, inventory=inventory, json_output=args.json)
    return

# 列出预设
if args.list_presets:
    list_presets()
    return

# 无参数时显示帮助
if args.width is None and args.preset is None:
    parser.print_help()
    sys.exit(0)

# 预设模式
if args.preset:
    if args.preset not in PRESETS:
        print(f"错误: 未知预设 '{args.preset}'")
        print("\n可用预设:")
        list_presets()
        sys.exit(1)
    width, depth, _ = PRESETS[args.preset]
    copies = args.copies
else:
    width = args.width
    depth = args.depth
    copies = args.copies
```

改为:
```python
# 列出预设
if args.list_presets:
    list_presets()
    return

# 解析尺寸参数
dims = parse_dimensions(args.dimensions)

# 如果有预设，加入列表
if args.preset:
    preset_dims = parse_preset(args.preset, args.copies)
    if preset_dims:
        dims.extend(preset_dims)

# 全局份数覆盖
if args.copies and dims:
    dims = [(w, h, args.copies) for w, h, c in dims]

# 无参数时显示帮助
if not dims:
    parser.print_help()
    sys.exit(0)

# 根据尺寸数量选择模式
if len(dims) == 1:
    # 单尺寸模式
    width, depth, copies = dims[0]
    # ... 现有的单尺寸逻辑 ...
else:
    # 批量模式
    batch_items = ['{}x{}:{}'.format(w, d, c) for w, d, c in dims]
    batch_mode(' '.join(batch_items), args.verbose, inventory=inventory, json_output=args.json)
    return
```

**Step 3: 简化单尺寸模式代码**

将现有的单尺寸逻辑（验证参数、调用 find_best_scheme、输出）保留在 if len(dims) == 1 分支内。

**Step 4: 提交**
```bash
git add scripts/split_calc.py
git commit -m "refactor: unify CLI args parsing for single and batch mode"
```

---

### Task 4: 测试新 CLI 语法

**Step 1: 测试单尺寸模式**

```bash
.venv/bin/python scripts/split_calc.py 485x425
```
Expected: 正常输出分割方案

```bash
.venv/bin/python scripts/split_calc.py 485x425 -c 3 -j
```
Expected: JSON 输出，copies=3

**Step 2: 测试批量模式**

```bash
.venv/bin/python scripts/split_calc.py 485x425 265x365:2
```
Expected: 输出批量打印计划

```bash
.venv/bin/python scripts/split_calc.py 265x365 325x365 -j
```
Expected: JSON 批量输出

**Step 3: 测试预设**

```bash
.venv/bin/python scripts/split_calc.py -p klean
```
Expected: 输出 Klean 件盒的分割方案

```bash
.venv/bin/python scripts/split_calc.py -p klean -c 2 -j
```
Expected: JSON 输出，copies=2

**Step 4: 测试无效输入**

```bash
.venv/bin/python scripts/split_calc.py
```
Expected: 显示帮助信息

```bash
.venv/bin/python scripts/split_calc.py invalid
```
Expected: 显示帮助信息或错误

**Step 5: 提交**
```bash
git commit -m "test: verify new CLI syntax works correctly"
```

---

### Task 5: 更新文档

**Files:**
- Modify: `scripts/split_calc.py:1913-1940` (main 函数的 epilog)

**Step 1: 更新帮助信息**

将 epilog 中的示例更新为新语法：

```python
epilog="""
示例:
  python3 split_calc.py 485x425              # 单尺寸
  python3 split_calc.py 485x425 -c 3         # 指定份数
  python3 split_calc.py 485x425 -j          # JSON 输出
  python3 split_calc.py 485x425 265x365:2   # 批量
  python3 split_calc.py -p klean             # 预设
  python3 split_calc.py -p klean -c 2       # 预设+份数

预设尺寸:
  klean       Klean件盒 270×170mm
  ikea-sunda  IKEA Sunda 360×500mm
  ikea-kal    IKEA KAL 360×500mm
  ikea-alex   IKEA Alex 360×500mm
  standard    标准抽屉 400×400mm
        """
```

**Step 2: 提交**
```bash
git add scripts/split_calc.py
git commit -m "docs: update CLI help examples"
```

---

## 执行方式

计划完成，保存为 `docs/plans/2026-02-20-cli-simplify-implementation.md`。

两个执行选项：

1. **Subagent-Driven (当前会话)** - 我调度子任务逐个执行，任务间审查
2. **Parallel Session (新会话)** - 在新会话中执行

选择哪种方式？
