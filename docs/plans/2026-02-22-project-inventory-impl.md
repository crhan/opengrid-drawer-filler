# 项目库存分离实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除全局库存，改为项目级库存管理，并保留全局项目索引

**Architecture:** 使用 JSON 文件存储项目索引 (`~/.opengrid/projects.json`)，项目级库存通过 `inventory_path` 配置指定

**Tech Stack:** Python, JSON, YAML

---

## Task 1: 创建项目索引管理模块

**Files:**
- Create: `opengrid/projects.py` (新文件)

**Step 1: 创建项目索引模块**

```python
"""项目索引管理模块"""

import json
import os
from pathlib import Path
from datetime import datetime

PROJECTS_FILE = Path.home() / ".opengrid" / "projects.json"


def _ensure_projects_dir():
    """确保 ~/.opengrid 目录存在"""
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_projects():
    """加载项目索引"""
    _ensure_projects_dir()
    if not PROJECTS_FILE.exists():
        return {"projects": [], "last_active": None}
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def _save_projects(data):
    """保存项目索引"""
    _ensure_projects_dir()
    with open(PJROJECTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_project(name: str, path: str):
    """注册新项目到索引"""
    data = _load_projects()

    # 检查是否已存在
    for p in data["projects"]:
        if p["path"] == path:
            p["name"] = name  # 更新名称
            data["last_active"] = path
            _save_projects(data)
            return

    # 新增项目
    data["projects"].append({
        "name": name,
        "path": path,
        "created": datetime.now().isoformat()
    })
    data["last_active"] = path
    _save_projects(data)


def list_projects():
    """列出所有已注册项目"""
    data = _load_projects()
    return data["projects"]


def get_last_active():
    """获取上次活跃项目路径"""
    data = _load_projects()
    return data.get("last_active")


def set_last_active(path: str):
    """设置上次活跃项目"""
    data = _load_projects()
    data["last_active"] = path
    _save_projects(data)


def is_project_registered(path: str) -> bool:
    """检查路径是否为已注册项目"""
    data = _load_projects()
    return any(p["path"] == path for p in data["projects"])
```

**Step 2: 运行测试验证语法**

Run: `python -c "from opengrid.projects import *; print('OK')"`
Expected: 正常输出

**Step 3: 提交**

```bash
git add opengrid/projects.py
git commit -m "feat: 添加项目索引管理模块"
```

---

## Task 2: 修改 setup skill 实现项目注册

**Files:**
- Modify: `skills/setup/SKILL.md`
- Create: `skills/setup/references/project-registration.md` (新文件)

**Step 1: 更新 setup skill 文档，添加项目注册步骤**

在 SKILL.md 的 "Step 2: 配置 config.yaml" 部分之后添加：

```markdown
### Step 2.5: 注册项目到索引

首次配置项目时，运行以下命令注册项目：

```bash
python -c "
from opengrid.projects import register_project
import os
register_project('项目名称', os.getcwd())
print('项目已注册')
```

这会将当前目录注册到全局项目索引。
```

**Step 2: 提交**

```bash
git add skills/setup/SKILL.md
git commit -m "docs: setup skill 添加项目注册说明"
```

---

## Task 3: 实现项目检测和提示逻辑

**Files:**
- Modify: `opengrid/projects.py` (添加检测函数)
- Create: `tests/test_projects.py` (新测试文件)

**Step 1: 编写测试**

```python
import pytest
import os
import tempfile
from pathlib import Path
from opengrid import projects


def test_is_project_registered():
    """测试项目注册检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 未注册时应返回 False
        assert projects.is_project_registered(tmpdir) is False

        # 注册后应返回 True
        projects.register_project("测试项目", tmpdir)
        assert projects.is_project_registered(tmpdir) is True
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_projects.py::test_is_project_registered -v`
Expected: FAIL (功能尚未实现完整)

**Step 3: 完善实现**

在 `opengrid/projects.py` 中添加缺失的函数实现。

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_projects.py::test_is_project_registered -v`
Expected: PASS

**Step 5: 提交**

```bash
git add opengrid/projects.py tests/test_projects.py
git commit -m "feat: 实现项目注册检测功能"
```

---

## Task 4: 实现项目切换功能

**Files:**
- Modify: `opengrid/projects.py`
- Modify: `scripts/inventory.py`

**Step 1: 在 projects.py 添加切换功能**

```python
def switch_project(path: str) -> bool:
    """切换到指定项目

    Args:
        path: 项目目录路径

    Returns:
        bool: 是否切换成功
    """
    if not is_project_registered(path):
        return False
    set_last_active(path)
    return True
```

**Step 2: 提交**

```bash
git add opengrid/projects.py
git commit -m "feat: 添加项目切换功能"
```

---

## Task 5: 实现 Agent 提示逻辑

**Files:**
- Modify: `skills/opengrid-drawer-filler/SKILL.md`

**Step 1: 更新主 skill 文档，添加项目检测逻辑**

在 SKILL.md 开头添加：

```markdown
## 入口检测

每次调用 skill 时：

1. 获取当前工作目录
2. 检查是否为已注册项目
3. 如果不是，提示用户选择：
   - 初始化新项目（调用 setup skill）
   - 切换到已有项目
```

**Step 2: 提交**

```bash
git add skills/opengrid-drawer-filler/SKILL.md
git commit -m "docs: 主 skill 添加项目检测说明"
```

---

## Task 6: 清理全局库存文件

**Files:**
- Delete: `inventory/inventory.json`

**Step 1: 确认无使用后删除**

检查是否有代码依赖全局 inventory：

```bash
grep -r "inventory/inventory.json" --include="*.py" .
```

如果无依赖，执行：

```bash
rm inventory/inventory.json
git add -A
git commit -m "chore: 移除全局库存文件"
```

---

## 验证清单

完成所有任务后，验证：

- [ ] `python -c "from opengrid.projects import *; print(list_projects())"` 正常工作
- [ ] setup skill 可以注册新项目
- [ ] 主 skill 检测到非项目目录时提示用户
- [ ] 库存操作使用项目级 `inventory.json`
