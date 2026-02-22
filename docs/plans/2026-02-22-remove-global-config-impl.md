# 移除全局配置实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完全移除全局配置，只保留项目级配置和库存

**Architecture:** 删除 config/ 目录，简化 config.py 只支持项目级配置，简化 inventory.py 移除默认值，简化 CLI 移除 -l/--level 参数

**Tech Stack:** Python, YAML, JSON

---

## Task 1: 删除 config/ 目录

**Files:**
- Delete: `config/` 目录

**Step 1: 删除 config 目录**

Run: `rm -rf /Users/ruohanc/Documents/projects/opengrid_plugin/config/`

Expected: 目录已删除

**Step 2: 验证无引用**

Run: `grep -r "config/config.yaml" --include="*.py" .`
Expected: 无结果

**Step 3: 提交**

```bash
git add -A
git commit -m "chore: 删除全局 config 目录"
```

---

## Task 2: 简化 config.py

**Files:**
- Modify: `opengrid/config.py`

**Step 1: 修改 config.py**

移除以下功能：
- `scope="global"` 支持
- `get_config_path("global")`
- `get_inventory()` 函数
- 默认配置回退

修改后的代码结构：

```python
"""配置管理模块 - 仅支持项目级配置"""

import copy
import os
import yaml
from pathlib import Path

# 默认配置（仅用于测试/开发）
DEFAULTS = {
    "initialized": False,
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "printer": {"model": "p1p"},
    "opengrid": {
        "tile_type": "Full",
        "stacking_method": "Ironing",
        "interface_separation": 0.2,
        "tile_size": 28
    },
}

PRINTER_PRESETS = {...}

_config = {}


def get_config_path():
    """获取配置文件路径（仅项目级）"""
    project_config = Path.cwd() / "opengrid_config.yaml"
    if not project_config.exists():
        raise FileNotFoundError(
            "未找到 opengrid_config.yaml\n"
            "请在项目目录下运行，或先初始化项目（调用 setup skill）"
        )
    return project_config


def load_config():
    """加载项目级配置"""
    global _config
    config_path = get_config_path()
    config = _load_single_config(config_path)
    _config = config
    return config


def _load_single_config(config_path):
    """加载配置文件"""
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        config = copy.deepcopy(DEFAULTS)
        for section, values in user_config.items():
            if section in config and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values
        return config
    return copy.deepcopy(DEFAULTS)


def get_printer_config():
    """获取打印机配置"""
    config = load_config()
    printer = config.get("printer", {})
    model = printer.get("model", "p1p")
    if model == "custom":
        return printer.get("custom", PRINTER_PRESETS["p1p"])
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])


def reload_config():
    """重新加载配置"""
    global _config
    _config = {}
    return load_config()


def is_initialized():
    """检查是否已初始化"""
    try:
        config_path = get_config_path()
    except FileNotFoundError:
        return False
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("initialized", False)


def ensure_initialized():
    """检查初始化状态"""
    if is_initialized():
        return
    print("\n错误: 项目未初始化")
    print("请编辑 opengrid_config.yaml 设置 initialized: true")
    raise SystemExit(1)
```

**Step 2: 运行测试验证**

Run: `python -c "from opengrid.config import load_config"`
Expected: 在非项目目录应报错

**Step 3: 提交**

```bash
git add opengrid/config.py
git commit -m "refactor: 简化 config.py 只支持项目级配置"
```

---

## Task 3: 简化 inventory.py

**Files:**
- Modify: `opengrid/inventory.py`

**Step 1: 修改 inventory.py**

移除 `INVENTORY_FILE` 常量和默认值逻辑：

```python
# 移除以下代码:
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# INVENTORY_FILE = os.path.join(SCRIPT_DIR, '..', 'inventory', 'inventory.json')

def get_inventory_path(config):
    """从配置获取库存文件路径"""
    inventory_path = config.get("inventory_path")
    if not inventory_path:
        raise ValueError(
            "未配置 inventory_path\n"
            "请在 opengrid_config.yaml 中设置 inventory_path"
        )

    p = Path(inventory_path)
    if p.is_absolute():
        return p
    # 相对路径相对于当前工作目录
    return Path.cwd() / p


def _load_data(config=None):
    """Load inventory data"""
    if config is None:
        raise ValueError("必须提供 config 参数指定库存文件路径")

    inv_file = get_inventory_path(config)
    if not os.path.exists(inv_file):
        return {"inventory": {}, "log": []}
    with open(inv_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_data(data, config=None):
    """Save inventory data"""
    if config is None:
        raise ValueError("必须提供 config 参数指定库存文件路径")

    inv_file = get_inventory_path(config)
    with open(inv_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

**Step 2: 提交**

```bash
git add opengrid/inventory.py
git commit -m "refactor: 简化 inventory.py 移除默认值"
```

---

## Task 4: 修改 scripts/inventory.py

**Files:**
- Modify: `scripts/inventory.py`

**Step 1: 移除 -l/--level 参数**

修改后的代码：

```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument('command', ...)
    parser.add_argument('items', ...)
    parser.add_argument('reason', ...)
    args = parser.parse_args()

    # 直接加载项目配置
    from opengrid.config import load_config
    config = load_config()

    # 构建 config 字典用于库存操作
    from opengrid.inventory import get_inventory_path
    inv_path = get_inventory_path(config)
    inventory_config = {"inventory_path": str(inv_path)}

    # 剩余代码不变...
```

**Step 2: 提交**

```bash
git add scripts/inventory.py
git commit -m "refactor: 移除 inventory.py 的 -l 参数"
```

---

## Task 5: 修改 scripts/split_calc.py

**Files:**
- Modify: `scripts/split_calc.py`

**Step 1: 移除 -l/--level 参数和自动加载库存**

```python
# 移除 load_config, get_inventory 的导入
# 改为显式通过 -i/--inventory 指定库存

parser.add_argument('-i', '--inventory', type=str,
                    help='库存文件路径 (JSON格式)')
parser.add_argument('-l', '--level', ...)  # 删除此行
```

**Step 2: 修改库存加载逻辑**

```python
if args.inventory is not None:
    # 显式指定库存文件
    with open(args.inventory) as f:
        inventory = json.load(f).get('inventory', {})
else:
    # 不自动加载库存
    inventory = None
```

**Step 3: 提交**

```bash
git add scripts/split_calc.py
git commit -m "refactor: 移除 split_calc.py 的 -l 参数"
```

---

## Task 6: 修改 scripts/slicer.py

**Files:**
- Modify: `scripts/slicer.py`

**Step 1: 移除 ensure_initialized 调用**

找到并删除:
```python
from opengrid.config import ensure_initialized
ensure_initialized()
```

**Step 2: 提交**

```bash
git add scripts/slicer.py
git commit -m "refactor: 移除 slicer.py 的 ensure_initialized 调用"
```

---

## Task 7: 修改 conftest.py

**Files:**
- Modify: `tests/conftest.py`

**Step 1: 移除全局 inventory 隔离**

删除:
```python
# === Inventory 隔离机制 ===
import inventory as inventory_module
_SCRIPT_DIR = os.path.dirname(os.path.abspath(inventory_module.__file__))
_ORIGINAL_INVENTORY_FILE = os.path.join(_SCRIPT_DIR, '..', 'inventory', 'inventory.json')
# ... 备份/恢复逻辑
```

保留 Config 隔离（因为 split_calc 测试仍需要 mock 配置）。

**Step 2: 提交**

```bash
git add tests/conftest.py
git commit -m "test: 移除 conftest.py 的全局 inventory 隔离"
```

---

## Task 8: 修改 test_inventory.py

**Files:**
- Modify: `tests/test_inventory.py`

**Step 1: 修改 tmp_inventory fixture**

```python
@pytest.fixture
def tmp_inventory(tmp_path, monkeypatch):
    """Create a temp inventory file and return config"""
    inv_file = tmp_path / "inventory.json"
    inv_file.write_text(json.dumps({"inventory": {}, "log": []}))
    # 返回 config 而不是修改模块常量
    return {"inventory_path": str(inv_file)}
```

**Step 2: 修改所有测试使用 config 参数**

将所有:
```python
load_inventory()  → load_inventory(config)
add_inventory({"7x5": 6}, "reason")  → add_inventory({"7x5": 6}, "reason", config)
deduct_inventory({"7x5": 3}, "reason")  → deduct_inventory({"7x5": 3}, "reason", config)
undo_last()  → undo_last(config)
```

**Step 3: 提交**

```bash
git add tests/test_inventory.py
git commit -m "test: 修改 test_inventory.py 使用 config 参数"
```

---

## Task 9: 修改 test_scheme_generator.py

**Files:**
- Modify: `tests/test_scheme_generator.py`

**Step 1: 同 Task 8，修改 fixture 和测试**

**Step 2: 提交**

```bash
git add tests/test_scheme_generator.py
git commit -m "test: 修改 test_scheme_generator.py 使用 config 参数"
```

---

## Task 10: 修改 test_config_scope.py

**Files:**
- Modify: `tests/test_config_scope.py`

**Step 1: 删除/修改测试**

删除:
- `test_get_config_path_global`
- `test_get_config_path_auto_returns_global_when_no_project_config`
- `test_default_inventory_path`
- `test_add_inventory_with_global_config`
- `test_separate_global_and_project_inventory`

保留:
- `test_config_scope_detection`（修改为只检查项目级）
- `test_custom_inventory_path`
- `TestInventoryOperationsWithConfig` 类（修改为不使用 "global" 概念）

**Step 2: 提交**

```bash
git add tests/test_config_scope.py
git commit -m "test: 修改 test_config_scope.py 适配新架构"
```

---

## Task 11: 修改 test_inventory_cli_scope.py

**Files:**
- Modify: `tests/test_inventory_cli_scope.py`

**Step 1: 删除/修改测试**

删除:
- `test_inventory_help_shows_level_option`
- `test_list_with_global_level`
- `TestInventoryCLIDefaultScope` 类

修改（移除 `-l project`）:
- `test_add_with_project_level`
- `test_add_to_global_creates_log_entry`
- `test_deduct_inventory_with_level`
- `test_undo_with_level`

**Step 2: 提交**

```bash
git add tests/test_inventory_cli_scope.py
git commit -m "test: 修改 test_inventory_cli_scope.py 移除 -l 参数"
```

---

## Task 12: 修改 test_inventory_cli_integration.py

**Files:**
- Modify: `tests/test_inventory_cli_integration.py`

**Step 1: 修改 run_inventory_cli 函数**

```python
def run_inventory_cli(args, cwd):
    result = subprocess.run(
        # 移除 "-l", "project"
        [sys.executable, str(PROJECT_ROOT / "scripts" / "inventory.py")] + args,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    return result
```

**Step 2: 提交**

```bash
git add tests/test_inventory_cli_integration.py
git commit -m "test: 修改 test_inventory_cli_integration.py 移除 -l 参数"
```

---

## Task 13: 运行测试验证

**Step 1: 运行所有测试**

Run: `.venv/bin/python -m pytest tests/ -v`

Expected: 所有测试通过（可能需要根据实际情况调整）

**Step 2: 提交**

```bash
git add -A
git commit -m "test: 修复所有测试适配新架构"
```

---

## 验证清单

- [ ] config/ 目录已删除
- [ ] config.py 只支持项目级配置
- [ ] inventory.py 移除默认值
- [ ] scripts/inventory.py 移除 -l 参数
- [ ] scripts/split_calc.py 移除 -l 参数
- [ ] scripts/slicer.py 移除 ensure_initialized
- [ ] 所有测试通过
