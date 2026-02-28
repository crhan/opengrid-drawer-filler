# opengrid-drawer-filler 工作流优化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 优化 skill 工作流，新增 compare 命令，解决库存扣减、方案展示等问题

**Architecture:** 新增 CLI compare 子命令，复用现有 present 模块生成 HTML 并自动打开

**Tech Stack:** Python, argparse (与项目现有 CLI 一致), subprocess

---

## 设计说明

### 关于"库存扣减只有文档"的澄清

Qwen 审查指出"库存扣减只有文档没有实现"。这是**误解**，解释如下：

1. **compare 命令（Task 1）**是脚本实现
2. **SKILL.md 更新（Task 2）**是 Agent 工作流描述
3. **库存扣减逻辑**是 Agent 与用户的交互行为：
   - Agent 展示方案后询问用户："是否扣减库存？"
   - 用户确认后，Agent 调用已存在的 `inventory deduct` 命令
   - 命令格式：`opengrid inventory deduct 7x5:2 "打印使用"`
   - 这是 Agent 层面的交互逻辑，无需新代码

**关于方案可比性**：
- `generate_comparison_html` 函数内部已验证方案数据，抛出 `ValueError` 时 compare 命令捕获并友好退出
- 这是被调用模块的责任，不需要在 compare 命令中重复验证

**架构设计原则**：
- 脚本层：计算、生成 STL
- Agent 层：用户交互、调用脚本
- 现有命令复用：`inventory deduct`

---

## Task 1: 新增 compare 子命令

**Step 0: 验证依赖函数**

Run:
```bash
grep -A 10 "def generate_comparison_html" opengrid/ui/presenter.py
```

确认：
- 函数存在于 `opengrid/ui/presenter.py:226`
- 签名: `generate_comparison_html(scheme_no_inv, scheme_with_inv)` → 返回 HTML 字符串
- 参数类型: 两个 dict
- 错误处理: 空数据会抛出 `ValueError`

**Step 1: 创建 compare.py**

```python
"""compare 子命令实现 - 生成 HTML 对比并打开"""
import json
import os
import sys
import webbrowser
from pathlib import Path
from argparse import Namespace

from opengrid.ui.presenter import generate_comparison_html

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _load_scheme(path_str: str) -> dict:
    """加载方案 JSON 文件"""
    path = Path(path_str)
    if not path.exists():
        print(f"错误: 文件不存在: {path.absolute()}", file=sys.stderr)
        sys.exit(1)
    # 文件大小限制
    if path.stat().st_size > MAX_FILE_SIZE:
        print(f"错误: 文件过大 (最大 {MAX_FILE_SIZE // 1024 // 1024}MB)", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)


def _generate_html(scheme_a: dict, scheme_b: dict) -> str:
    """生成 HTML 对比页面"""
    try:
        return generate_comparison_html(scheme_a, scheme_b)
    except ValueError as e:
        print(f"错误: 方案数据无效: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 生成 HTML 失败: {e}", file=sys.stderr)
        sys.exit(1)


def _resolve_output_path(output: str, force: bool) -> Path:
    """解析并验证输出路径"""
    path = Path(output).resolve()
    if path.exists() and not force:
        print(f"错误: 文件已存在: {path}，使用 --force 覆盖", file=sys.stderr)
        sys.exit(1)
    return path


def _write_html(html: str, output_path: Path) -> None:
    """写入 HTML 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"已生成: {output_path.absolute()}")


def _open_html(path: Path) -> None:
    """用系统默认浏览器打开 HTML 文件"""
    try:
        webbrowser.open(f"file://{path.absolute()}")
    except Exception as e:
        print(f"警告: 无法打开浏览器: {e}", file=sys.stderr)


def add_parser(subparsers):
    parser = subparsers.add_parser('compare', help='生成方案对比 HTML 并打开')
    parser.add_argument('scheme_a', help='方案A的JSON文件路径')
    parser.add_argument('scheme_b', help='方案B的JSON文件路径')
    parser.add_argument('-o', '--output', default='comparison.html', help='输出文件路径')
    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖已存在的文件')
    parser.add_argument('--no-open', action='store_true', help='不自动打开 HTML')
    parser.set_defaults(func=handle_compare)
    return parser


def handle_compare(args: Namespace) -> None:
    """处理 compare 命令"""
    # 加载并验证方案
    scheme_a = _load_scheme(args.scheme_a)
    scheme_b = _load_scheme(args.scheme_b)

    # 生成 HTML
    html = _generate_html(scheme_a, scheme_b)

    # 写入文件
    output_path = _resolve_output_path(args.output, args.force)
    _write_html(html, output_path)

    # 打开 HTML
    if not args.no_open:
        _open_html(output_path)


__all__ = ['add_parser']
```

**Step 2: 注册子命令**

修改 `opengrid/cli/__init__.py`，添加 compare 命令导入：

```python
from opengrid.cli.commands.compare import add_parser as add_compare_parser
```

在 `create_parser` 函数中添加：
```python
add_compare_parser(subparsers)
```

**Step 3: 测试 compare 命令**

Run:
```bash
# 测试 --help
uv run scripts/opengrid.py compare --help

# 测试文件不存在错误
uv run scripts/opengrid.py compare not_exist.json scheme_b.json 2>&1 | grep "文件不存在"

# 测试完整流程
uv run scripts/opengrid.py split 265x365 -j > /tmp/scheme_a.json
uv run scripts/opengrid.py split 265x365 -i inventory.json -j > /tmp/scheme_b.json
uv run scripts/opengrid.py compare /tmp/scheme_a.json /tmp/scheme_b.json -o /tmp/comparison.html

# 测试 --no-open
uv run scripts/opengrid.py compare /tmp/scheme_a.json /tmp/scheme_b.json -o /tmp/c2.html --no-open

**Step 4: Commit**

```bash
git add opengrid/cli/commands/compare.py opengrid/cli/__init__.py
git commit -m "feat: add compare command for HTML comparison"
```

---

## Task 2: 修改 SKILL.md 流程描述

**Files:**
- Modify: `skills/opengrid-drawer-filler/SKILL.md`

**Step 1: 更新 Step 1 描述**

在 "### Step 1:" 部分添加：
> **强制要求**: 必须先运行 status 命令检查配置和库存状态。

**Step 2: 更新 Step 2 描述**

在 "### Step 2: 询问需求" 部分添加抽屉命名逻辑：
> **抽屉命名**: 用户输入尺寸后，按首次出现顺序命名。例如：
> - 抽屉A = 第一个尺寸
> - 抽屉B = 第二个尺寸（以此类推）
> 后续统一使用抽屉名称（如"抽屉A"）进行展示和交互。

**Step 3: 更新 Step 3 描述**

在 "### Step 3: 计算方案" 部分添加：
> - 同时计算方案A（无库存）和方案B（有库存）
> - 同时生成两个 JSON 文件保存到当前目录，供后续使用

**Step 4: 更新 Step 4 描述**

替换现有的方案展示格式为：
> 终端简洁格式：
> ```
> === 抽屉A: 265x365mm x2 ===
>
> [A] 方案A: 2次打印, ~25分钟, ~95g
> [B] 方案B: 1次打印, ~12分钟, ~45g (节省52%)
>
> 瓦片对比:
>     7x5: A=x4(打印), B=x2(库)+x2(打印)
>     3x5: A=x4(打印), B=x4(打印)
>
> [H] 生成HTML对比页面
> [Q] 退出
> ```

**Step 5: 更新 Step 5 描述**

在 STL 生成前添加库存扣减确认：
> 用户选择方案后询问：
> - `[Y] 确认扣减库存并生成 STL`
> - `[N] 只生成 STL，不扣减库存`

**Step 6: 添加 compare 命令说明**

在"快速命令"部分添加：
```bash
# 生成 HTML 对比并打开
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py compare scheme_a.json scheme_b.json -o comparison.html
```

**Step 7: Commit**

```bash
git add skills/opengrid-drawer-filler/SKILL.md
git commit -m "docs: update SKILL.md workflow description"
```

---

## 执行方式

**Plan complete and saved to `docs/plans/2026-02-27-skill-workflow-optimization-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
