---
name: setup
description: 初始化 openGrid 抽屉铺满环境。包括运行安装脚本、配置 opengrid_config.yaml、验证配置和初始化状态。当用户首次使用或需要重新初始化环境时使用此技能。
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

### Step 2: 配置 opengrid_config.yaml

在项目目录下创建 `opengrid_config.yaml`：

```bash
# 在项目目录下创建配置文件
cat > opengrid_config.yaml << EOF
# 初始化状态 (设为 true 表示已完成配置)
initialized: true

# 打印机配置
printer:
  model: h2d        # 机型: h2d, x1c, p1p, a1 等

# 输出目录
output:
  stl_dir: ~/3D打印/opengrid/  # STL 输出目录

# 库存文件路径
inventory_path: ./inventory.json  # 项目专属库存文件
EOF
```

#### 完整配置项说明

```yaml
# 初始化状态 (首次配置后设为 true)
initialized: true

# 打印机配置
printer:
  model: h2d        # 机型: h2d, x1c, p1p, a1 等
  # 或自定义:
  # custom:
  #   bed_x: 300
  #   bed_y: 320
  #   max_z: 325

# 输出配置
output:
  stl_dir: ~/3D打印/opengrid/  # STL 输出目录

# 库存配置 (必需)
inventory_path: ./inventory.json  # 项目专属库存文件

# openGrid 瓦片配置
opengrid:
  tile_type: Full        # 瓦片类型: Full, Lite, Heavy
  stacking_method: Ironing  # 堆叠方式: Ironing, Interface
  interface_separation: 0.2  # 层间间隙 (mm)
  tile_size: 28  # 网格单元格大小 (mm)
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

### Step 3: 创建库存文件

项目需要有自己的库存文件：

```bash
# 创建空的库存文件
echo '{"inventory": {}, "log": []}' > inventory.json
```

### Step 4: 验证初始化状态

配置完成后验证：

```bash
# 测试配置加载（在项目目录下）
.venv/bin/python -c "from opengrid.config import load_config; c = load_config(); print('initialized:', c.get('initialized'))"

# 测试方案计算
.venv/bin/python scripts/split_calc.py 485 425 -i inventory.json
```

## 快速检查清单

- [ ] 运行 `./scripts/setup.sh` 完成安装
- [ ] 在项目目录下创建 `opengrid_config.yaml`
- [ ] 编辑配置: 设置 `initialized: true`、打印机型号、库存路径
- [ ] 创建 `inventory.json` 文件
- [ ] 注册项目到索引（可选）
- [ ] 验证: 运行 `split_calc.py 485 425 -i inventory.json` 确认配置正确
