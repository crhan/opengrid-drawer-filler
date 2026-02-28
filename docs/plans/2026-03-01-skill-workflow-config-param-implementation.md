# SKILL.md 工作流优化 - 配置文件参数化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 添加 `--config` 参数支持，让 Agent 可以显式传入配置文件路径，同时保持向后兼容。

**Architecture:** 在 CLI 入口添加全局参数，通过全局变量传递给 config 模块使用。config 模块支持指定路径加载配置。

**Tech Stack:** Python argparse, YAML

---

## 实现概览

1. 修改 `opengrid/cli/__init__.py` - 添加全局 `--config` 参数
2. 修改 `opengrid/config.py` - 支持指定配置文件路径
3. 测试验证功能正常
4. 更新 `skills/opengrid-drawer-filler/SKILL.md` - 更新工作流描述

---

### Task 1: CLI 添加全局 `--config` 参数

**Files:**
- Modify: `opengrid/cli/__init__.py:1-37`

**Step 1: 添加全局参数**

当前代码：
```python
def main():
    """CLI 主入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)
```

修改为：
```python
def main():
    """CLI 主入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    # 添加全局参数
    parser.add_argument('-c', '--config', help='配置文件路径（默认在当前目录查找）')

    subparsers = parser.add_subparsers(dest='command', required=True)
```

**Step 2: 传递 config 参数到全局模块**

在 `main()` 函数中，解析 args 后，将 config 路径存入全局变量供 config 模块使用：

在 `import sys` 之后添加：
```python
# 全局变量存储命令行指定的配置文件路径
_cli_config_path = None
```

在 `args = parser.parse_args()` 之后添加：
```python
    # 将 config 路径存入全局变量
    global _cli_config_path
    _cli_config_path = args.config

    if hasattr(args, 'func'):
        args.func(args)
```

添加获取函数（在 `main()` 函数外）：
```python
def get_cli_config_path():
    """获取命令行指定的配置文件路径"""
    global _cli_config_path
    return _cli_config_path
```

完整修改后的 `opengrid/cli/__init__.py`:
```python
#!/usr/bin/env python3
"""CLI 模块 - 统一入口"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 全局变量存储命令行指定的配置文件路径
_cli_config_path = None

from opengrid.cli.commands.compare import add_parser as add_compare_parser
from . import commands


def get_cli_config_path():
    """获取命令行指定的配置文件路径"""
    global _cli_config_path
    return _cli_config_path


def main():
    """CLI 主入口"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog='opengrid',
        description='openGrid CLI - 抽屉铺满计算工具'
    )

    # 添加全局参数
    parser.add_argument('-c', '--config', help='配置文件路径（默认在当前目录查找）')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # 注册子命令
    commands.split.add_parser(subparsers)
    commands.inventory.add_parser(subparsers)
    commands.slicer.add_parser(subparsers)
    commands.project.add_parser(subparsers)
    commands.status.add_parser(subparsers)
    commands.present.add_parser(subparsers)
    add_compare_parser(subparsers)

    args = parser.parse_args()

    # 将 config 路径存入全局变量
    global _cli_config_path
    _cli_config_path = args.config

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


__all__ = ['main', 'get_cli_config_path']
```

**Step 3: 测试验证**

Run: `uv run scripts/opengrid.py --help`
Expected: 输出中应包含 `-c CONFIG, --config CONFIG` 参数说明

---

### Task 2: config 模块支持指定配置文件路径

**Files:**
- Modify: `opengrid/config.py:1-138`

**Step 1: 添加全局变量和修改 get_config_path**

在文件开头 `_config = {}` 之后添加：
```python
_cli_config_path = None


def set_cli_config_path(path):
    """设置命令行指定的配置文件路径"""
    global _cli_config_path
    _cli_config_path = path


def get_cli_config_path():
    """获取命令行指定的配置文件路径"""
    global _cli_config_path
    return _cli_config_path
```

修改 `get_config_path()` 函数：
```python
def get_config_path():
    """获取配置文件路径（支持命令行指定）"""
    # 优先使用命令行指定的路径
    cli_path = get_cli_config_path()
    if cli_path:
        config_path = Path(cli_path)
        if config_path.exists():
            return config_path
        # 如果指定的文件不存在，报错

    # 默认在当前目录查找
    project_config = Path.cwd() / "opengrid_config.yaml"
    if not project_config.exists():
        raise FileNotFoundError(
            "未找到 opengrid_config.yaml\n"
            "请在项目目录下运行，或先初始化项目（调用 setup skill）"
        )
    return project_config
```

**Step 2: 测试验证**

创建一个临时测试配置文件：
```bash
mkdir -p /tmp/opengrid_test
echo 'initialized: true
printer:
  model: h2d
inventory_path: ./inventory.json
output:
  stl_dir: ./stl_output/' > /tmp/opengrid_test/opengrid_config.yaml
```

Run: `cd /tmp/opengrid_test && uv run /Users/ruohanc/Documents/projects/opengrid_plugin/scripts/opengrid.py -c /tmp/opengrid_test/opengrid_config.yaml status`
Expected: 应显示配置信息（h2d 打印机）

---

### Task 3: 测试验证整体功能

**Step 1: 测试不带 config 参数（保持现有行为）**

Run: `uv run scripts/opengrid.py status`
Expected: 在有配置文件的项目目录下正常工作

**Step 2: 测试带 config 参数**

Run: `uv run scripts/opengrid.py -c ./opengrid_config.yaml status`
Expected: 正常工作

**Step 3: 测试带 config 和 inventory 参数**

Run: `uv run scripts/opengrid.py -c ./opengrid_config.yaml status -i ./inventory.json`
Expected: 正常工作

---

### Task 4: 更新 SKILL.md 工作流

**Files:**
- Modify: `skills/opengrid-drawer-filler/SKILL.md:43-77`

**Step 1: 更新 Step 1 部分**

找到现有的 "### Step 1: 检查配置、加载库存、展示状态" 部分，修改为：

```markdown
### Step 1: 查找配置文件和库存文件

**强制要求**: 必须先查找配置文件和库存文件位置，然后通过参数传给脚本。

#### 1.1 查找配置文件

Agent 在当前目录及父目录向上搜索 `opengrid_config.yaml`：

```bash
# 向上搜索配置文件
current_dir=$(pwd)
while [ "$current_dir" != "/" ]; do
    if [ -f "$current_dir/opengrid_config.yaml" ]; then
        echo "找到配置文件: $current_dir/opengrid_config.yaml"
        break
    fi
    current_dir=$(dirname "$current_dir")
done
```

#### 1.2 定位库存文件

根据配置中的 `inventory_path` 定位库存文件。

#### 1.3 运行 status 命令确认现状

```bash
# 传入配置文件和库存文件路径
uv run scripts/opengrid.py -c ./opengrid_config.yaml status -i ./inventory.json
```

输出示例：
```

修改输出示例部分...

#### 1.4 如果配置文件不在当前目录

如果配置文件在父目录或其他位置，使用 `--config` 参数指定：

```bash
# 指定配置文件路径
uv run scripts/opengrid.py -c ../opengrid_config.yaml status
```
```

**Step 2: 更新快速命令部分**

在 "## 快速命令" 部分更新示例：

```bash
# 查看项目状态（自动查找配置）
uv run scripts/opengrid.py status

# 指定配置文件和库存
uv run scripts/opengrid.py -c ./opengrid_config.yaml status -i ./inventory.json
```
```

---

## 执行顺序

1. Task 1: 修改 CLI 添加全局参数
2. Task 2: 修改 config 模块支持指定路径
3. Task 3: 测试验证
4. Task 4: 更新 SKILL.md
