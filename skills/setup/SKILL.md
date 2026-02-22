---
name: setup
description: 初始化 openGrid 抽屉铺满环境。包括运行安装脚本、配置 config.yaml、验证配置级别和初始化状态。当用户首次使用或需要重新初始化环境时使用此技能。
compatibility: 需要 Python 3.12+, OpenSCAD, Homebrew
---

# openGrid 抽屉铺满 - 初始化

首次使用 openGrid 前完成环境配置。

## 工作流程

### Step 1: 运行安装脚本

```bash
cd ${CLAUDE_PLUGIN_ROOT}
./scripts/setup.sh
```

脚本自动完成：

1. 创建 Python venv (`.venv`)
2. 安装 Python 依赖 (pyyaml, pytest, Pillow)
3. 安装 OpenSCAD (通过 Homebrew)
4. 克隆 QuackWorks 源码
5. 安装 BOSL2 库

### Step 2: 配置 config.yaml

首次配置需要复制模板并编辑：

```bash
# 复制配置模板
cp config/config.example.yaml config/config.yaml

# 编辑配置
# 关键配置项:
# - initialized: true  # 标记为已初始化
# - printer.model     # 打印机型号 (h2d, x1c, etc)
# - output.stl_dir   # STL 输出目录
```

#### 完整配置项说明

```yaml
# 打印机配置
printer:
  model: h2d        # 机型: h2d, x1c, p1p 等
  bed_x: 256        # 打印床 X (mm)
  bed_y:256         # 打印床 Y (mm)
  max_z: 270        # 最大 Z 轴 (mm)

# 输出配置
output:
  stl_dir: ~/3D打印/opengrid/  # STL 输出目录

# 库存配置
inventory_path: ./inventory.json  # 项目专属库存文件

# 瓦片配置
tiles:
  type: Full        # 瓦片类型: Full, Hole, Tray
  stacking: stack  # 堆叠方式: stack, nest

# 初始化状态 (首次配置后设为 true)
initialized: true
```

### Step 2.5: 注册项目到索引

首次配置项目时，运行以下命令注册项目：

```bash
.venv/bin/python -c "
from opengrid.projects import register_project
import os
name = input('请输入项目名称（如"厨房抽屉"）: ')
register_project(name, os.getcwd())
print('项目已注册到索引')
"
```

这会将当前目录注册到全局项目索引 (`~/.opengrid/projects.json`)。

### Step 3: 配置级别检测

openGrid 支持两级配置，按优先级：

1. **项目级**: 当前目录的 `opengrid_config.yaml`
2. **全局级**: 技能目录的 `config/config.yaml`

检测逻辑：

```
if exists("opengrid_config.yaml"):
    use 项目级配置
else:
    use 全局配置
```

#### 项目配置示例

在项目目录创建 `opengrid_config.yaml` 可覆盖全局配置：

```yaml
printer:
  model: x1c # 覆盖全局
inventory_path: ./inventory.json # 项目专属库存
output:
  stl_dir: ./stl_output/ # 项目专属输出
```

### Step 4: 验证初始化状态

每次启动时检查配置：

1. 加载对应级别的配置文件
2. 检查 `initialized` 字段
3. 如未初始化，引导用户完成配置

#### 配置加载代码示例

```python
import yaml
import os

SKILL_DIR = "/path/to/opengrid-drawer-filler"

def load_config():
    """加载配置，优先使用项目级配置"""
    # 检查项目级配置
    if os.path.exists("opengrid_config.yaml"):
        with open("opengrid_config.yaml") as f:
            config = yaml.safe_load(f)
        print("使用项目级配置")
    else:
        config_path = os.path.join(SKILL_DIR, "config/config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print("使用全局配置")

    return config

def check_initialized(config):
    """检查初始化状态"""
    if not config.get("initialized", False):
        print("错误: 尚未初始化")
        print("请运行: cp config/config.example.yaml config/config.yaml")
        print("然后编辑 config.yaml 设置 initialized: true")
        return False
    return True
```

### 验证命令

配置完成后验证：

```bash
# 测试配置加载
.venv/bin/python -c "from opengrid.config import load_config; c = load_config(); print('initialized:', c.get('initialized'))"

# 测试方案计算
.venv/bin/python scripts/split_calc.py 485 425
```

## 快速检查清单

- [ ] 运行 `./scripts/setup.sh` 完成安装
- [ ] 复制 `config/config.example.yaml` → `opengrid_config.yaml`（项目级）或 `config/config.yaml`（全局级）
- [ ] 编辑配置: 设置 `initialized: true`、打印机型号、项目库存路径
- [ ] 注册项目到索引（项目级配置必需）
- [ ] 验证: 运行 `split_calc.py 485 425` 确认配置正确
