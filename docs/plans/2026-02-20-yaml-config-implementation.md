# YAML 配置系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 为 skill 添加 YAML 配置文件系统，支持用户自定义输出路径、打印机参数等。

**Architecture:** 创建 `config.py` 模块统一管理配置加载，提供 `get_config()` 函数供其他模块使用。

**Tech Stack:** Python, PyYAML

---

## Task 1: 创建配置模块框架

**Files:** Create `scripts/config.py`

```python
"""配置管理模块"""

import os
import yaml
from pathlib import Path

# 默认配置
DEFAULTS = {
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "printer": {"model": "p1p"},
    "opengrid": {
        "tile_type": "Full",
        "stacking_method": "Ironing",
        "interface_separation": 0.2,
        "tile_size": 28
    },
    "software": {
        "openscad": "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "bambustudio": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
        "orca": "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
    }
}

# Bambu 机型预设
PRINTER_PRESETS = {
    "a1_mini": {"bed_x": 120, "bed_y": 120, "max_z": 120},
    "a1": {"bed_x": 180, "bed_y": 180, "max_z": 180},
    "p1p": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "p1s": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1c": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1e": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "h2d": {"bed_x": 300, "bed_y": 300, "max_z": 300},
}

def get_config_path():
    """获取配置文件路径"""
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "config.yaml"

def load_config():
    """加载配置，优先使用 config.yaml，缺失则使用默认值"""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        # 合并默认配置
        config = DEFAULTS.copy()
        for section, values in user_config.items():
            if section in config:
                config[section].update(values)
            else:
                config[section] = values
        return config
    return DEFAULTS.copy()

def get_printer_config():
    """获取打印机配置，处理预设"""
    config = load_config()
    printer = config.get("printer", {})
    model = printer.get("model", "p1p")

    if model == "custom":
        return printer.get("custom", PRINTER_PRESETS["p1p"])
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])

# 测试
if __name__ == "__main__":
    print(load_config())
    print(get_printer_config())
```

**验证:** `python3 scripts/config.py`

---

## Task 2: 创建配置模板文件

**Files:** Create `config.example.yaml`

```yaml
# === 必需配置 ===
output:
  stl_dir: "~/3D打印/opengrid/"

# === 打印机配置 ===
printer:
  # 机型预设: a1_mini / a1 / p1p / p1s / x1c / x1e / h2d / custom
  model: "p1p"

  # 自定义参数（当 model=custom 时使用）
  custom:
    bed_x: 256
    bed_y: 256
    max_z: 256

# === openGrid 参数（可选）===
opengrid:
  tile_type: "Full"           # Full / Lite / Heavy
  stacking_method: "Ironing"   # Ironing / Interface Layer
  interface_separation: 0.2
  tile_size: 28

# === 软件路径（可选）===
software:
  openscad: "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
  bambustudio: "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
  orca: "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
```

---

## Task 3: 更新 slicer.py 使用配置

**Files:** Modify `scripts/slicer.py:1-40`

**Step 1: 添加导入**

```python
from config import load_config, get_printer_config
```

**Step 2: 替换硬编码路径**

替换：
```python
OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE = os.path.join(VENDOR_DIR, "QuackWorks", "openGrid", "openGrid.scad")
OUTPUT_DIR = "/Users/ruohanc/..."
```

为：
```python
_config = load_config()
OPENSCAD_PATH = _config["software"]["openscad"]
SCAD_FILE = os.path.join(VENDOR_DIR, "QuackWorks", "openGrid", "openGrid.scad")
OUTPUT_DIR = os.path.expanduser(_config["output"]["stl_dir"])
```

**Step 3: 使用打印机配置**

在需要的地方调用 `get_printer_config()` 获取 bed_x, bed_y, max_z。

---

## Task 4: 更新 split_calc.py 使用配置

**Files:** Modify `scripts/split_calc.py:13-40`

**Step 1: 添加导入**

```python
from config import load_config, get_printer_config
```

**Step 2: 添加配置加载**

```python
_config = load_config()
_printer = get_printer_config()
MAX_X = _printer["bed_x"] // TILE_SIZE
MAX_Y = _printer["bed_y"] // TILE_SIZE
MAX_Z = _printer["max_z"]
```

---

## Task 5: 添加 config.yaml 到 .gitignore

**Files:** Modify `.gitignore`

添加：
```
config.yaml
```

---

## Task 6: 更新 CLAUDE.md

**Files:** Modify `CLAUDE.md`

添加配置说明：
```markdown
## 配置文件

首次使用需要配置 `config.yaml`：

1. 复制模板：`cp config.example.yaml config.yaml`
2. 编辑配置：设置 STL 输出路径、打印机型号等
```

---

**Plan complete. Two execution options:**

**1. Subagent-Driven** - 我为每个任务派遣 subagent，任务间审查

**2. Parallel Session** - 新会话使用 executing-plans

**Which approach?**
