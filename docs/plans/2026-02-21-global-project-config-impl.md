# 全局/项目级配置与库存分离实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 支持配置和库存的全局（技能目录）和项目（当前工作目录）两级管理，通过 `opengrid_config.yaml` 文件名自动检测。

**Architecture:** 重构 config.py 和 inventory.py，添加 scope 参数支持全局/项目级加载，配置中通过 `inventory_path` 字段指定库存位置。

**Tech Stack:** Python, YAML, JSON

---

## Task 1: 重构 config.py 添加 scope 支持

**Files:**
- Modify: `opengrid/config.py:40-96`

**Step 1: 添加 scope 检测函数和配置路径函数**

在 `config.py` 中添加以下函数：

```python
def _is_project_mode():
    """检测是否为项目模式（当前目录存在 opengrid_config.yaml）"""
    return (Path.cwd() / "opengrid_config.yaml").exists()


def get_config_path(scope="auto"):
    """获取配置文件路径

    Args:
        scope: "global" | "project" | "auto" (默认自动检测)
    """
    skill_dir = Path(__file__).parent.parent
    if scope == "global":
        return skill_dir / "config" / "config.yaml"

    # auto 或 project
    project_config = Path.cwd() / "opengrid_config.yaml"
    if scope == "project" or (scope == "auto" and project_config.exists()):
        return project_config

    return skill_dir / "config" / "config.yaml"


def get_config_scope():
    """获取当前配置级别"""
    if _is_project_mode():
        return "project"
    return "global"
```

**Step 2: 重构 load_config 函数支持 scope 参数**

修改现有的 `load_config` 函数，添加 `scope` 参数：

```python
def load_config(scope="auto"):
    """加载配置，支持全局/项目级

    Args:
        scope: "global" | "project" | "auto" (默认自动检测)
    """
    global _config
    if _config is not None:
        return _config

    config_path = get_config_path(scope)
    config = _load_single_config(config_path)

    # 如果是 auto 模式且存在项目配置，合并
    if scope == "auto" and _is_project_mode():
        project_path = get_config_path("project")
        project_config = _load_single_config(project_path)
        config = _merge_config(config, project_config)

    _config = config
    return config


def _load_single_config(config_path):
    """加载单个配置文件"""
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        config = DEFAULTS.copy()
        for section, values in user_config.items():
            if section in config and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values
        return config
    return DEFAULTS.copy()


def _merge_config(global_config, project_config):
    """合并配置，项目级覆盖全局"""
    result = global_config.copy()
    for section, values in project_config.items():
        if section in result and isinstance(result[section], dict):
            result[section].update(values)
        else:
            result[section] = values
    return result
```

**Step 3: 修改 reload_config 支持 scope**

```python
def reload_config(scope="auto"):
    """重新加载配置"""
    global _config
    _config = None
    return load_config(scope)
```

**Step 4: 运行测试验证**

```bash
.venv/bin/python -m pytest tests/test_config.py -v -k "load"
```

Expected: PASS (现有测试通过)

**Step 5: 提交**

```bash
git add opengrid/config.py
git commit -m "feat: add scope support to config loading"
```

---

## Task 2: 重构 inventory.py 支持配置驱动路径

**Files:**
- Modify: `opengrid/inventory.py:1-50`

**Step 1: 添加 get_inventory_path 函数**

在 inventory.py 中添加：

```python
import sys
from pathlib import Path

def get_inventory_path(config=None):
    """从配置获取库存文件路径

    Args:
        config: 配置字典，如为 None 则自动加载

    Returns:
        Path: 库存文件路径
    """
    if config is None:
        from opengrid.config import load_config
        config = load_config()

    inventory_path = config.get("inventory_path")
    if inventory_path:
        p = Path(inventory_path)
        if p.is_absolute():
            return p
        # 相对路径相对于配置文件所在目录
        config_dir = Path.cwd()
        return config_dir / p

    # 默认使用全局 inventory
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "inventory" / "inventory.json"


def _get_inventory_file(config=None):
    """Get inventory file path - 支持配置指定"""
    return str(get_inventory_path(config))
```

**Step 2: 替换现有的 _get_inventory_file 函数调用**

将现有的：
```python
def _get_inventory_file():
    """Get inventory file path - can be overridden for testing"""
    if hasattr(sys.modules.get('inventory', None), 'INVENTORY_FILE'):
        return sys.modules['inventory'].INVENTORY_FILE
    return INVENTORY_FILE
```

改为使用新的 `get_inventory_path` 函数：

```python
def _get_inventory_file(config=None):
    """Get inventory file path - 支持配置指定"""
    return str(get_inventory_path(config))
```

**Step 3: 修改 _load_data 支持 config 参数**

```python
def _load_data(config=None):
    """Load inventory data with log"""
    inv_file = get_inventory_path(config)
    if not os.path.exists(inv_file):
        return {"inventory": {}, "log": []}
    with open(inv_file, 'r', encoding='utf-8') as f:
        return json.load(f)
```

**Step 4: 测试新功能**

```bash
# 测试全局模式
.venv/bin/python -c "
from opengrid.config import load_config, get_config_scope
from opengrid.inventory import get_inventory_path

print('Scope:', get_config_scope())
config = load_config()
print('Config:', config.get('printer'))
print('Inventory path:', get_inventory_path())
"
```

Expected: 输出 global scope 和全局 inventory 路径

**Step 5: 提交**

```bash
git add opengrid/inventory.py
git commit -m "feat: support config-driven inventory path"
```

---

## Task 3: 添加 CLI 参数支持 scope 选择

**Files:**
- Modify: `scripts/split_calc.py`

**Step 1: 添加 -l/--level 参数**

在 split_calc.py 的 argparse 部分添加：

```python
parser.add_argument(
    '-l', '--level',
    choices=['auto', 'global', 'project'],
    default='auto',
    help='配置级别: auto (自动检测), global (全局), project (项目)'
)
```

**Step 2: 传递 level 参数到配置加载**

在 main 函数中获取 level 参数，并传递给配置和库存加载函数：

```python
def main():
    args = parser.parse_args()

    # 设置 scope
    scope = args.level

    # 加载配置（带 scope）
    from opengrid.config import load_config, reload_config
    reload_config(scope)
    config = load_config(scope)

    # ... 其他逻辑
```

**Step 3: 测试 CLI 参数**

```bash
.venv/bin/python scripts/split_calc.py --help | grep -A2 "\-l"
```

Expected: 显示 -l/--level 参数说明

**Step 4: 提交**

```bash
git add scripts/split_calc.py
git commit -m "feat: add -l/--level CLI parameter for scope selection"
```

---

## Task 4: 添加集成测试

**Files:**
- Create: `tests/test_config_scope.py`

**Step 1: 编写测试用例**

```python
"""测试配置和库存的全局/项目级分离"""

import os
import tempfile
import pytest
from pathlib import Path


class TestConfigScope:
    """测试配置 scope 功能"""

    def test_get_config_path_global(self):
        """测试获取全局配置路径"""
        from opengrid.config import get_config_path, reload_config
        reload_config("global")
        path = get_config_path("global")
        assert "config.yaml" in str(path)

    def test_get_config_path_project_nonexistent(self):
        """测试项目配置不存在时返回全局"""
        from opengrid.config import get_config_path, reload_config
        reload_config("auto")
        path = get_config_path("auto")
        # 应该返回全局配置（因为当前目录没有 opengrid_config.yaml）
        assert "config.yaml" in str(path)

    def test_config_scope_detection(self):
        """测试 scope 检测功能"""
        from opengrid.config import get_config_scope, reload_config
        reload_config("global")
        scope = get_config_scope()
        assert scope in ["global", "project"]


class TestInventoryPath:
    """测试库存路径功能"""

    def test_default_inventory_path(self):
        """测试默认库存路径"""
        from opengrid.config import load_config, reload_config
        from opengrid.inventory import get_inventory_path

        reload_config("global")
        config = load_config("global")
        path = get_inventory_path(config)
        assert "inventory.json" in str(path)

    def test_custom_inventory_path(self):
        """测试自定义库存路径"""
        from opengrid.config import load_config, reload_config
        from opengrid.inventory import get_inventory_path

        # 模拟项目配置中指定了自定义路径
        config = {"inventory_path": "/tmp/test_inventory.json"}
        path = get_inventory_path(config)
        assert str(path) == "/tmp/test_inventory.json"
```

**Step 2: 运行测试**

```bash
.venv/bin/python -m pytest tests/test_config_scope.py -v
```

Expected: PASS

**Step 3: 提交**

```bash
git add tests/test_config_scope.py
git commit -m "test: add integration tests for config scope"
```

---

## Task 5: 更新 SKILL.md 文档

**Files:**
- Modify: `SKILL.md`

**Step 1: 更新 Step 1 部分**

添加项目级配置说明：

```markdown
### Step 1: 检查配置、加载库存、展示状态

1. 检查配置级别（全局/项目）
   - 项目级：当前目录存在 `opengrid_config.yaml`
   - 全局：技能目录的 `config/config.yaml`
2. 加载对应级别的配置
3. 从配置的 `inventory_path` 读取库存位置
4. ... (其余不变)
```

**Step 2: 添加配置文件示例**

在 SKILL.md 中添加"配置文件"章节：

```markdown
## 配置文件

### 全局配置

位置：`{skill_dir}/config/config.yaml`

### 项目配置

位置：`{当前目录}/opengrid_config.yaml`

项目配置示例：

```yaml
printer:
  model: h2d  # 覆盖全局
inventory_path: ./my_project/inventory.json  # 项目库存
output:
  stl_dir: ./stl_output/  # 项目输出目录
```
```

**Step 3: 提交**

```bash
git add SKILL.md
git commit -m "docs: document global/project config support"
```

---

## 执行方式

**计划完成，保存到 `docs/plans/2026-02-21-global-project-config-design.md`。两种执行方式：**

1. **Subagent-Driven (本会话)** - 每任务派遣新子 agent，任务间代码审查，快速迭代
2. **Parallel Session (新会话)** - 在新会话中使用 executing-plans，批量执行带检查点

**选择哪种方式？**
