# 全局 -i 参数实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `-i` 参数做成全局参数，优先从 `-i` 获取，如果未提供则从配置文件读取。

**Architecture:** 参考已有的 `-c` 全局参数模式，在 CLI 入口添加 `-i` 参数，存储到 config 模块，inventory.py 优先读取 CLI 指定路径。

**Tech Stack:** Python argparse, opengrid/cli, opengrid/config, opengrid/inventory

---

### Task 1: config.py 添加全局 inventory 路径支持

**Files:**
- Modify: `opengrid/config.py:35-47`

**Step 1: 添加全局变量和 getter/setter**

在 `_cli_config_path = None` 后添加：

```python
# 全局变量存储命令行指定的库存文件路径
_cli_inventory_path = None


def set_cli_inventory_path(path):
    """设置命令行指定的库存文件路径"""
    global _cli_inventory_path
    _cli_inventory_path = path


def get_cli_inventory_path():
    """获取命令行指定的库存文件路径"""
    global _cli_inventory_path
    return _cli_inventory_path
```

**Step 2: Commit**

```bash
git add opengrid/config.py
git commit -m "feat: add global inventory path CLI support"
```

---

### Task 2: cli/__init__.py 添加 -i 全局参数

**Files:**
- Modify: `opengrid/cli/__init__.py:19-35`

**Step 1: 添加 -i 参数**

在 `parser.add_argument('-c', '--config'...` 后添加：

```python
parser.add_argument('-i', '--inventory', help='库存文件路径（默认从配置文件读取）')
```

**Step 2: 添加同步到 config 模块**

在 `config.set_cli_config_path(args.config)` 后添加：

```python
    config.set_cli_inventory_path(args.inventory)
```

**Step 3: Commit**

```bash
git add opengrid/cli/__init__.py
git commit -m "feat: add -i global argument to CLI"
```

---

### Task 3: inventory.py 优先使用 CLI 指定路径

**Files:**
- Modify: `opengrid/inventory.py:25-54`

**Step 1: 修改 get_inventory_path 函数**

在函数开头添加 CLI 路径检查：

```python
def get_inventory_path(config):
    """从配置获取库存文件路径

    Args:
        config: 配置字典，必须包含 inventory_path

    Returns:
        Path: 库存文件路径

    Raises:
        ValueError: 如果未配置 inventory_path
    """
    # 优先使用命令行指定的路径
    from opengrid import config as config_module
    cli_path = config_module.get_cli_inventory_path()
    if cli_path:
        p = Path(cli_path)
        if p.is_absolute():
            return p
        return Path.cwd() / p

    # 以下为原有逻辑...
```

**Step 2: Commit**

```bash
git add opengrid/inventory.py
git commit -m "feat: prioritize CLI inventory path over config"
```

---

### Task 4: 更新 SKILL.md 命令

**Files:**
- Modify: `skills/opengrid-drawer-filler/SKILL.md`

**Step 1: 更新命令示例**

将所有子命令的 `-i` 改为全局参数形式：

- `uv run scripts/opengrid.py split 265x365:2 -i inventory.json` → `uv run scripts/opengrid.py -i inventory.json split 265x365:2`
- `uv run scripts/opengrid.py -c ./opengrid_config.yaml status -i ./inventory.json` → `uv run scripts/opengrid.py -c ./opengrid_config.yaml -i ./inventory.json status`

涉及行：77, 184-185, 213, 384, 393

**Step 2: Commit**

```bash
git add skills/opengrid-drawer-filler/SKILL.md
git commit -m "docs: update SKILL.md to use global -i argument"
```

---

### Task 5: 测试验证

**Files:**
- Test: 运行命令验证功能

**Step 1: 运行测试**

```bash
uv run pytest -v
```

Expected: 所有测试通过

**Step 2: 手动测试**

```bash
# 测试全局 -i 参数在 status 命令
uv run scripts/opengrid.py -i ./inventory.json status

# 测试全局 -i 参数在 split 命令
uv run scripts/opengrid.py -i ./inventory.json split 325x460
```

Expected: 命令正常执行，优先使用 -i 指定的库存文件

**Step 3: Commit**

```bash
git commit -m "test: verify global -i argument works"
```

---

**Plan complete and saved to `docs/plans/2026-03-01-global-inventory-argument.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
