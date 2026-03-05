---
name: opengrid-drawer-filler
description: 计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。根据抽屉尺寸计算最优 openGrid 瓦片布局，支持库存管理和批量计算。当用户需要为抽屉创建 3D 打印瓦片铺满方案时使用此技能。
compatibility: 需要 Python 3.12+, OpenSCAD, Python 依赖 (pyyaml, Pillow, pytest)
---

# openGrid 抽屉铺满

根据抽屉尺寸计算最优瓦片分割方案，并可自动生成 STL 文件用于 3D 打印。

## 核心原则

**Agent 负责用户交互，脚本负责计算和生成。**

- Agent 询问用户需求，调用脚本获取结果，展示给用户

## Agent 工作流

### Step 1: 检查配置、加载库存、展示状态

1. 检查配置级别（全局/项目）
   - 项目级：当前目录存在 `opengrid_config.yaml`
   - 全局：技能目录的 `config/config.yaml`
2. 加载对应级别的配置
3. 从配置的 `inventory_path` 读取库存位置
4. 检查 `config.yaml` 的 `initialized` 状态
5. 如未初始化，引导用户配置：
   - 复制配置文件：`cp config/config.example.yaml config/config.yaml`
   - 编辑设置 `initialized: true` 和打印机型号
6. 加载配置（使用 Python 直接读取或调用 config 模块）
7. 加载库存文件（从配置的 `inventory_path` 读取）
8. 向用户输出当前状态（库存信息突出展示）：

   **openGrid 抽屉铺满**

   🖨️ 打印机: **[型号]** ([bed_x]×[bed_y]×[max_z]mm)

   📁 输出目录: `[stl_dir]`

   🔧 瓦片类型: [tile_type] | 堆叠: [stacking_method]

   使用 `format_inventory_for_display()` 函数展示库存（带框线表格）：

   ```
   ╔════════════════════════════════════════╗
   ║  📦 库存状态                          ║
   ╚════════════════════════════════════════╝

   ┌──────────┬──────────┐
   │ 瓦片尺寸  │   数量   │
   ├──────────┼──────────┤
   │   8×8   │    9    │
   │   6×7   │    5    │
   │   5×5   │    3    │
   └──────────┴──────────┘

   共 **3 种尺寸**, **17 stack** (可用)
   ```

9. **确认库存数量是否正确**，如不正确引导用户更新库存：

### 库存管理

**严格禁止直接编辑 `inventory/inventory.json` 文件。**

所有库存修改必须通过脚本进行，并记录修改原因：

```bash
# 变量定义
PLUGIN_ROOT=/Users/ruohanc/Documents/projects/opengrid_plugin
PROJECT_ROOT=$(pwd)  # 有 opengrid_config.yaml 的目录

# 查看当前库存
uv run $PLUGIN_ROOT/scripts/opengrid.py -c $PROJECT_ROOT/opengrid_config.yaml inventory list

# 添加库存 (格式: 宽x高:数量)
uv run $PLUGIN_ROOT/scripts/opengrid.py -c $PROJECT_ROOT/opengrid_config.yaml inventory add 8x8:5 6x7:3 --reason "入库原因：购买新材料"

# 扣减库存
uv run $PLUGIN_ROOT/scripts/opengrid.py -c $PROJECT_ROOT/opengrid_config.yaml inventory deduct 8x8:2 --reason "扣减原因：打印使用"

# 撤销上次操作
uv run $PLUGIN_ROOT/scripts/opengrid.py -c $PROJECT_ROOT/opengrid_config.yaml inventory undo
```

**重要**：执行 inventory 命令时必须：

1. **指定配置文件路径**（使用 `-c` 参数）
2. 使用绝对路径或相对于当前目录的路径

如果不在项目目录下，会使用全局配置，无法找到项目库存。

**关键约束**：

- 禁止直接编辑 inventory.json
- 必须提供原因说明
- 每次操作自动记录到日志

### Step 2: 询问需求

1. 询问抽屉尺寸和份数
2. 解析尺寸格式：
   - `"265x360:2"` = 265×360mm，2份
   - `"265x360"` = 265×360mm，1份
   - `"265 360 2"` = 空格分隔格式

### Step 3: 计算方案

**自动双方案**：当检测到有库存时，自动计算两种方案：

1. 方案 A：不考虑库存（追求最优切割，平衡度高）
2. 方案 B：使用库存（追求最少打印，节省耗材）

**无库存时**：只计算方案 A。

调用 `scripts/opengrid.py`：

```bash
# 方案 A：不使用库存 (获取 JSON)
python3 scripts/opengrid.py split 325x460 --json > no_inv.json

# 方案 B：使用库存 (获取 JSON)
python3 scripts/opengrid.py split 325x460 -i inventory.json --json > with_inv.json
```

### Step 4: 方案对比与决策

使用 `compare` 命令生成可视化的**网格填充蓝图**进行对比决策：

```bash
python3 scripts/opengrid.py compare no_inv.json with_inv.json -o comparison.html
```

**对比报告 (`comparison.html`) 特点**：
- **网格铺满蓝图**：基于抽屉真实坐标（如 11×16）的拼图视图。
- **色彩语义**：青色代表库存，橙色代表需打印。
- **节省统计**：直观显示节省的打印时间和克数。

### Step 5: 生成施工项目

用户选定方案后，生成正式的施工文件夹。

```bash
# 快速预览 (不生成 STL)
python3 scripts/opengrid.py split 325x460 -i inventory.json -H preview.html

# 正式施工 (创建项目，生成 STL 并建立施工单)
python3 scripts/opengrid.py split 325x460 -i inventory.json -P ./projects/my_drawer
```

#### 施工单 (`print_plan.html`) 逻辑规范：

> **重要**: 施工单必须严格区分任务类型，防止误打印：

1.  **🖨️ 打印任务**：仅列出需要 3D 打印的瓦片尺寸和数量（背景为橙色）。
2.  **📦 现有库存提取**：仅列出直接从库存取用的瓦片（背景为青色）。
3.  **安装蓝图**：显示完整的网格位置索引，指导用户将库存件与打印件拼接。
4.  **STL 获取**：提供直接指向项目内 STL 文件的链接。

### Step 6: 打印与同步

1. 根据施工单的“打印任务”进行切片和打印。
2. 施工完成后，手动通过 CLI 更新库存：
```bash
python3 scripts/opengrid.py inventory deduct 8x8:2 --reason "完成 325x460 项目施工"
```

## 快速命令

```bash
# 批量计算
python3 scripts/split_calc.py 265x365:2 325x365:2

# 单尺寸计算
python3 scripts/split_calc.py 485 425

# 使用预设
python3 scripts/split_calc.py -p klean

# 使用项目级配置
python3 scripts/split_calc.py 265x365:2 -l project

# 使用全局配置
python3 scripts/split_calc.py 265x365:2 -l global

# 生成 STL
python3 scripts/slicer.py -g 7x5x3 10x5x3
```

详细命令、配置说明、算法规则等请参考 [references/](references/) 目录。

## 配置文件

openGrid 支持两级配置文件：全局配置和项目配置。项目配置会覆盖全局配置的同名字段。

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

配置级别检测顺序：
1. 检查当前目录是否存在 `opengrid_config.yaml`（项目级）
2. 如不存在，使用技能目录的 `config/config.yaml`（全局级）

## 初始化

首次使用前完成配置，运行一次安装脚本即可完成所有设置：

```bash
cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
./scripts/setup.sh
```

脚本自动完成：

1. 创建 Python venv (`.venv`)
2. 安装 Python 依赖 (pyyaml, pytest, Pillow)
3. 安装 OpenSCAD
4. 克隆 QuackWorks
5. 安装 BOSL2

之后运行脚本：

```bash
.venv/bin/python scripts/split_calc.py 485 425
```
