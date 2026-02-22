# CLI 重构计划：统一入口 + Subcommand 模式

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 scripts 目录下的多个 CLI 入口脚本合并成一个统一入口，使用 subcommand 模式组织不同领域操作，并实现职责分离。

**Architecture:** 创建 `opengrid/cli/` 模块包含所有 CLI 相关逻辑（参数解析、格式化、子命令实现），`scripts/` 目录只保留一个入口文件。核心计算逻辑保留在 `opengrid/core/` 中。

**Tech Stack:** Python, argparse (subcommand), pytest

---

## 背景

当前 `scripts/` 目录包含多个独立的 CLI 入口脚本：
- `split_calc.py` (77KB) - 抽屉分割计算
- `slicer.py` (17KB) - STL 生成和切片
- `inventory.py` - 库存管理

新目录结构：
```
scripts/
└── opengrid.py                   # 唯一入口文件

opengrid/
├── core/                          # 核心算法（已有）
├── cli/                          # CLI 模块
│   ├── __init__.py
│   ├── __main__.py
│   ├── formatters.py
│   ├── utils.py
│   └── commands/
│       ├── __init__.py
│       ├── project.py
│       ├── inventory.py
│       ├── split.py
│       └── slicer.py
├── stl/, ui/, project/           # 已有
├── inventory.py, config.py        # 已有
```

---

## Task 1: 创建 scripts/opengrid.py 入口文件

**Files:**
- Create: `scripts/opengrid.py`

**Step 1: 创建入口文件**

```python
#!/usr/bin/env python3
"""统一 CLI 入口"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opengrid.cli import main

if __name__ == "__main__":
    main()
```

**Step 2: 验证文件创建**

Run: `ls -la scripts/opengrid.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add scripts/opengrid.py
git commit -m "feat: 添加统一 CLI 入口文件"
```

---

## Task 2: 创建 opengrid/cli/__init__.py

**Files:**
- Create: `opengrid/cli/__init__.py`

**Step 1: 创建 CLI 模块初始化文件**

```python
"""CLI 模块 - 统一入口"""

from . import commands


def main():
    """CLI 主入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # 注册子命令
    commands.project.add_parser(subparsers)
    commands.inventory.add_parser(subparsers)
    commands.split.add_parser(subparsers)
    commands.slicer.add_parser(subparsers)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


__all__ = ['main']
```

**Step 2: Commit**

```bash
git add opengrid/cli/__init__.py
git commit -m "feat: 添加 opengrid/cli 模块初始化文件"
```

---

## Task 3: 创建 opengrid/cli/commands/__init__.py

**Files:**
- Create: `opengrid/cli/commands/__init__.py`

**Step 1: 创建 commands 子模块**

```python
"""子命令模块"""

from . import project, inventory, split, slicer

__all__ = ['project', 'inventory', 'split', 'slicer']
```

**Step 2: Commit**

```bash
git add opengrid/cli/commands/__init__.py
git commit -m "feat: 添加 CLI commands 子模块"
```

---

## Task 4: 验证 CLI 骨架工作

**Step 1: 运行 CLI 验证**

Run: `python scripts/opengrid.py --help`
Expected: 显示帮助信息，包含 subcommands

**Step 2: 如果失败，调试并修复**

---

## Task 5: 实现 split 子命令 - 迁移 parse_dimensions

**Files:**
- Create: `opengrid/cli/utils.py`
- Modify: `opengrid/cli/commands/split.py`

**Step 1: 创建 utils.py 包含解析函数**

```python
"""CLI 工具函数"""
import re
from typing import List, Tuple


def parse_dimensions(args: List[str]) -> List[Tuple[int, int, int]]:
    """解析位置参数为尺寸列表

    支持格式:
    - 485x425 -> (485, 425, 1)
    - 265x365:2 -> (265, 365, 2)
    - 265 365 -> (265, 365, 1)
    - 265 365 2 -> (265, 365, 2)
    """
    items = []
    for arg in args:
        # 支持 x 或 × 符号
        match = re.match(r'(\d+)[x×](\d+)(?::(\d+))?', arg)
        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            c = int(match.group(3)) if match.group(3) else 1
            items.append((w, h, c))
            continue

        # 空格分隔格式
        parts = arg.split()
        if len(parts) == 2:
            try:
                items.append((int(parts[0]), int(parts[1]), 1))
            except ValueError:
                pass
        elif len(parts) == 3:
            try:
                items.append((int(parts[0]), int(parts[1]), int(parts[2])))
            except ValueError:
                pass

    return items


def parse_batch_input(input_str: str) -> List[Tuple[int, int, int]]:
    """解析批量输入字符串"""
    return parse_dimensions(input_str.split())


__all__ = ['parse_dimensions', 'parse_batch_input']
```

**Step 2: 运行测试验证**

Run: `python -c "from opengrid.cli.utils import parse_dimensions; print(parse_dimensions(['485x425']))"`
Expected: `[(485, 425, 1)]`

**Step 3: Commit**

```bash
git add opengrid/cli/utils.py
git commit -m "feat: 添加 CLI 工具函数 parse_dimensions"
```

---

## Task 6: 实现 split 子命令 - 迁移 formatters

**Files:**
- Create: `opengrid/cli/formatters.py`

**Step 1: 创建 formatters.py 包含输出格式化函数**

```python
"""CLI 输出格式化函数"""
from typing import Any, Dict


def print_plan(width: int, depth: int, scheme: Any, copies: int = 1):
    """打印人类可读的方案"""
    print(f"抽屉尺寸: {width} x {depth} mm (x{copies})")
    print(f"网格: {scheme.get('grid_w')} x {scheme.get('grid_h')}")
    print("瓦片分割:")
    for tile in scheme.get('tiles', []):
        print(f"  {tile[0]}x{tile[1]}")
    print(f"总打印次数: {scheme.get('prints', 1)}")


def output_json(width: int, depth: int, scheme: Any, copies: int = 1) -> str:
    """输出 JSON 格式"""
    import json
    data = {
        'dimensions': {'width': width, 'depth': depth, 'copies': copies},
        'grid': scheme.get('grid'),
        'tiles': scheme.get('tiles', []),
        'prints': scheme.get('prints', 1)
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


__all__ = ['print_plan', 'output_json']
```

**Step 2: Commit**

```bash
git add opengrid/cli/formatters.py
git commit -m "feat: 添加 CLI 格式化函数"
```

---

## Task 7: 实现 split 子命令 - 创建 commands/split.py

**Files:**
- Create: `opengrid/cli/commands/split.py`

**Step 1: 创建 split 子命令实现**

```python
"""split 子命令实现"""
from opengrid.cli.utils import parse_dimensions
from opengrid.cli.formatters import print_plan, output_json
from opengrid.core import find_best_scheme, get_grid_dimensions


def add_parser(subparsers):
    parser = subparsers.add_parser('split', help='抽屉分割计算')
    parser.add_argument('dimensions', nargs='*', help='尺寸列表')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数')
    parser.add_argument('-j', '--json', action='store_true', help='JSON 输出')
    parser.add_argument('-b', '--batch', help='批量输入')
    parser.set_defaults(func=handle_split)
    return parser


def handle_split(args):
    """处理 split 命令"""
    # 解析输入
    dims = parse_dimensions(args.dimensions)

    if not dims:
        print("错误: 请提供尺寸参数")
        return

    width, depth, copies = dims[0]

    # 计算网格
    grid_w, grid_h = get_grid_dimensions(width, depth)

    # 找最优方案
    scheme = find_best_scheme(grid_w, grid_h)

    # 输出
    if args.json:
        print(output_json(width, depth, scheme, copies))
    else:
        print_plan(width, depth, scheme, copies)


__all__ = ['add_parser']
```

**Step 2: 更新 commands/__init__.py 导出**

```python
from . import project, inventory, split, slicer

__all__ = ['project', 'inventory', 'split', 'slicer']
```

**Step 3: 测试 split 命令**

Run: `python scripts/opengrid.py split 485x425`
Expected: 显示分割方案

**Step 4: Commit**

```bash
git add opengrid/cli/commands/split.py
git commit -m "feat: 实现 split 子命令"
```

---

## Task 8: 验证基本功能

**Step 1: 测试基本命令**

```bash
# 测试 help
python scripts/opengrid.py --help

# 测试 split 子命令
python scripts/opengrid.py split 485x425
python scripts/opengrid.py split 485x425 -j

# 测试 preset
python scripts/opengrid.py split --preset klean
```

**Step 2: 如果有问题，修复**

---

## Task 9: 迁移 split_calc.py 中的批量计算逻辑

**Files:**
- Modify: `opengrid/cli/commands/split.py`

**Step 1: 添加批量计算函数**

从 `scripts/split_calc.py` 迁移以下函数到 `opengrid/cli/commands/split.py`:
- `batch_mode()`
- `optimize_batch_global()`
- `merge_and_optimize()`
- `calculate_single()`
- `calculate_total_prints()`
- `calculate_batch_cost_with_inventory()`
- `build_scheme_data()`
- `build_batch_data()`
- `print_batch_plan()`

**Step 2: 测试批量计算**

Run: `python scripts/opengrid.py split -b "265x365:2 325x365:2"`
Expected: 批量计算结果

**Step 3: Commit**

```bash
git add opengrid/cli/commands/split.py
git commit -m "feat: 迁移批量计算逻辑到 split 子命令"
```

---

## Task 10: 实现 inventory 子命令

**Files:**
- Create: `opengrid/cli/commands/inventory.py`

**Step 1: 创建 inventory 子命令**

```python
"""inventory 子命令实现"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from opengrid.config import load_config
from opengrid.inventory import (
    load_inventory,
    add_inventory,
    deduct_inventory,
    undo_last,
    print_inventory
)


def add_parser(subparsers):
    parser = subparsers.add_parser('inventory', help='库存管理')
    sub = parser.add_subparsers(dest='inventory_command', required=True)

    # list
    sub.add_parser('list', help='列出库存')

    # add
    add_p = sub.add_parser('add', help='添加库存')
    add_p.add_argument('items', help='物品列表')
    add_p.add_argument('reason', nargs='?', default='', help='原因')

    # deduct
    deduct_p = sub.add_parser('deduct', help='扣减库存')
    deduct_p.add_argument('items', help='物品列表')
    deduct_p.add_argument('reason', nargs='?', default='', help='原因')

    # undo
    sub.add_parser('undo', help='撤销操作')

    parser.set_defaults(func=handle_inventory)
    return parser


def handle_inventory(args):
    """处理 inventory 命令"""
    config = load_config()

    cmd = args.inventory_command

    if cmd == 'list':
        inventory = load_inventory(config)
        print_inventory(inventory)

    elif cmd == 'add':
        from opengrid.inventory import parse_items
        items = parse_items([args.items])
        add_inventory(items, args.reason, config)
        print("添加成功")

    elif cmd == 'deduct':
        from opengrid.inventory import parse_items
        items = parse_items([args.items])
        deduct_inventory(items, args.reason, config)
        print("扣减成功")

    elif cmd == 'undo':
        undo_last(config)
        print("撤销成功")


__all__ = ['add_parser']
```

**Step 2: 测试 inventory 命令**

```bash
python scripts/opengrid.py inventory list
python scripts/opengrid.py inventory add 8x8:5 "测试"
python scripts/opengrid.py inventory deduct 8x8:1 "测试"
python scripts/opengrid.py inventory undo
```

**Step 3: Commit**

```bash
git add opengrid/cli/commands/inventory.py
git commit -m "feat: 实现 inventory 子命令"
```

---

## Task 11: 实现 slicer 子命令

**Files:**
- Create: `opengrid/cli/commands/slicer.py`

**Step 1: 创建 slicer 子命令**

```python
"""slicer 子命令实现"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from opengrid.stl import generator as stl_generator


def add_parser(subparsers):
    parser = subparsers.add_parser('slicer', help='STL 生成和切片')
    sub = parser.add_subparsers(dest='slicer_command', required=True)

    # generate
    gen_p = sub.add_parser('generate', help='生成 STL')
    gen_p.add_argument('dimensions', help='尺寸 WxHxS')
    gen_p.add_argument('-f', '--force', action='store_true', help='强制重新生成')

    # slice
    slice_p = sub.add_parser('slice', help='切片 STL')
    slice_p.add_argument('file', help='STL 文件')
    slice_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    # open
    open_p = sub.add_parser('open', help='在切片器中打开')
    open_p.add_argument('file', help='STL 文件')
    open_p.add_argument('--slicer', default='bambu', choices=['bambu', 'orca'], help='切片器')

    parser.set_defaults(func=handle_slicer)
    return parser


def handle_slicer(args):
    """处理 slicer 命令"""
    cmd = args.slicer_command

    if cmd == 'generate':
        # 解析尺寸
        dims = args.dimensions.split('x')
        if len(dims) != 3:
            print("错误: 尺寸格式应为 WxHxS")
            return
        w, h, s = map(int, dims)

        # 生成 STL
        output = stl_generator.generate_stl(w, h, s, force=args.force)
        print(f"生成: {output}")

    elif cmd == 'slice':
        # TODO: 实现切片逻辑
        print(f"切片: {args.file} (slicer={args.slicer})")

    elif cmd == 'open':
        # TODO: 实现打开逻辑
        print(f"打开: {args.file} (slicer={args.slicer})")


__all__ = ['add_parser']
```

**Step 2: 测试 slicer 命令**

```bash
python scripts/opengrid.py slicer generate 7x5x3
```

**Step 3: Commit**

```bash
git add opengrid/cli/commands/slicer.py
git commit -m "feat: 实现 slicer 子命令"
```

---

## Task 12: 实现 project 子命令

**Files:**
- Create: `opengrid/cli/commands/project.py`

**Step 1: 创建 project 子命令**

```python
"""project 子命令实现"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from opengrid.project.manager import ProjectManager


def add_parser(subparsers):
    parser = subparsers.add_parser('project', help='项目管理')
    sub = parser.add_subparsers(dest='project_command', required=True)

    # list
    sub.add_parser('list', help='列出项目')

    # create
    create_p = sub.add_parser('create', help='创建项目')
    create_p.add_argument('name', help='项目名称')
    create_p.add_argument('dimensions', help='尺寸')

    # show
    show_p = sub.add_parser('show', help='显示项目')
    show_p.add_argument('name', help='项目名称')

    parser.set_defaults(func=handle_project)
    return parser


def handle_project(args):
    """处理 project 命令"""
    cmd = args.project_command
    mgr = ProjectManager()

    if cmd == 'list':
        projects = mgr.list_projects()
        for p in projects:
            print(p)

    elif cmd == 'create':
        # 解析尺寸并创建项目
        print(f"创建项目: {args.name} (尺寸: {args.dimensions})")

    elif cmd == 'show':
        print(f"显示项目: {args.name}")


__all__ = ['add_parser']
```

**Step 2: 测试 project 命令**

```bash
python scripts/opengrid.py project list
```

**Step 3: Commit**

```bash
git add opengrid/cli/commands/project.py
git commit -m "feat: 实现 project 子命令"
```

---

## Task 13: 清理旧脚本

**Files:**
- Delete: `scripts/split_calc.py`
- Delete: `scripts/slicer.py`
- Delete: `scripts/inventory.py`
- Modify: `scripts/__init__.py`

**Step 1: 删除旧脚本（或改为转发脚本）**

```bash
rm scripts/split_calc.py
rm scripts/slicer.py
rm scripts/inventory.py
```

**Step 2: 更新 scripts/__init__.py**

```python
# 保留兼容导入
from opengrid.cli import main

__all__ = ['main']
```

**Step 3: Commit**

```bash
git add scripts/
git commit -m "refactor: 移除旧 CLI 脚本，统一使用新入口"
```

---

## Task 14: 更新测试用例

**Files:**
- Modify: `tests/test_cli_parser.py`

**Step 1: 更新导入路径**

```python
# 旧
from scripts.split_calc import parse_dimensions, parse_preset

# 新
from opengrid.cli.utils import parse_dimensions
```

**Step 2: 运行测试**

Run: `.venv/bin/python -m pytest tests/test_cli_parser.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli_parser.py
git commit -m "test: 更新测试导入路径"
```

---

## Task 15: 最终验证

**Step 1: 运行所有测试**

```bash
.venv/bin/python -m pytest -v
```

**Step 2: 测试所有子命令**

```bash
python scripts/opengrid.py --help
python scripts/opengrid.py split 485x425
python scripts/opengrid.py split 485x425 -j
python scripts/opengrid.py split -b "265x365:2 325x365:2"
python scripts/opengrid.py inventory list
python scripts/opengrid.py project list
python scripts/opengrid.py slicer generate 7x5x3
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: 完成 CLI 重构"
```

---

## 验证方式

```bash
# 测试新 CLI
python scripts/opengrid.py split 485x425
python scripts/opengrid.py split 485x425 -j
python scripts/opengrid.py split -b "265x365:2 325x365:2"
python scripts/opengrid.py inventory list
python scripts/opengrid.py project list
python scripts/opengrid.py slicer generate 7x5x3

# 确保原有测试通过
.venv/bin/python -m pytest
```
