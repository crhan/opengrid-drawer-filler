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

运行 `opengrid status` 命令展示当前项目状态：

```bash
# 在项目目录下运行
cd ${项目目录}
python scripts/opengrid.py status
```

输出示例：
```
========== openGrid 状态 ==========

╔════════════════════════════════════════╗
║  📦 库存状态                          ║
╚════════════════════════════════════════╝

┌──────────┬──────────┐
│ 瓦片尺寸  │   数量   │
├──────────┼──────────┤
│   8×8   │    9    │
│   6×7   │    5    │
└──────────┴──────────┘

共 **2 种尺寸**, **14 stack** (可用)

🖨️ 打印机: P1P (256×256×256mm)
📁 输出目录: ~/3D打印/opengrid/
🔧 瓦片类型: Full | 堆叠: Ironing
```

如果当前目录没有 `opengrid_config.yaml`，需要先配置项目。

### 库存管理

**项目级库存**：每个项目独立管理自己的库存（通过 `inventory_path` 配置指定）。

**严格禁止直接编辑库存文件。**

所有库存修改使用 `opengrid inventory` 命令：

```bash
# 查看库存
python scripts/opengrid.py inventory list

# 添加库存 (格式: 宽x高:数量)
python scripts/opengrid.py inventory add 8x8:5 6x7:3 "入库原因"

# 扣减库存
python scripts/opengrid.py inventory deduct 8x8:2 "扣减原因"

# 撤销上次操作
python scripts/opengrid.py inventory undo
```

**重要**：执行 inventory 命令时必须：

1. **切换到项目目录**（有 `opengrid_config.yaml` 的目录）
2. 使用绝对路径调用 `.venv` 和 `scripts/inventory.py`

如果不在项目目录下，会报错找不到配置文件。

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

1. 方案 A：不考虑库存（最优打印次数）
2. 方案 B：使用库存

**无库存时**：只计算方案 A（标准最优方案）

使用 `opengrid split` 命令：

```bash
# 方案 A：不使用库存
python scripts/opengrid.py split 265x365:2 325x365:2

# 方案 B：使用库存（通过 -i 指定库存文件）
python scripts/opengrid.py split 265x365:2 325x365:2 -i inventory.json
```

### Step 4: 展示方案

将脚本输出展示给用户，询问选择。可选：使用 `present` 命令生成 HTML 对比页面。

#### 使用 present 命令（可选）

```bash
# 先生成两个方案的 JSON
python scripts/opengrid.py split 325x460 -j > scheme_no_inv.json
python scripts/opengrid.py split 325x460 -i inventory.json -j > scheme_with_inv.json

# 生成 HTML 对比页面
python scripts/opengrid.py present scheme_no_inv.json scheme_with_inv.json -o comparison.html
```

生成的 HTML 页面包含：
- 两种方案并排对比
- SVG 瓦片布局示意图（显示每片规格）
- 打印时间、耗材、瓦片数统计
- 节省百分比高亮显示

#### 展示内容规范

> **重要**: 展示方案时必须包含以下全部内容，使用 emoji + 框线表格突出库存价值：

**1. 库存覆盖率表格**（必须展示）

脚本已输出增强版库存展示，包含框线表格：

```
╔════════════════════════════════════════╗
║  📦 库存利用                            ║
╚════════════════════════════════════════╝

┌──────────┬──────────┬──────────┬──────────┐
│ 瓦片尺寸  │ 库存数量  │ 需要数量  │   状态   │
├──────────┼──────────┼──────────┼──────────┤
│  8×8    │   9      │   4      │ ✅ 充足  │
│  6×7    │   5      │   2      │ ✅ 充足  │
│  8×4    │   0      │   4      │ ❌ 需打印 │
└──────────┴──────────┴──────────┴──────────┘

📊 库存覆盖率: 3/5 种尺寸 (60%)
💰 节省: 18 分钟 (45%打印时间)
```

**2. 可视化布局**（风格2：带尺寸标注）

```
┌───────────┬─────────┐
│   7×5     │   3×5   │
│ ┌───────┐ │ ┌─────┐ │
│ │       │ │ │     │ │
│ └───────┘ │ └─────┘ │
├───────────┼─────────┤
│   7×5     │   3×5   │
│ ┌───────┐ │ ┌─────┐ │
│ │       │ │ │     │ │
│ └───────┘ │ └─────┘ │
└───────────┴─────────┘
```

**3. 详细统计**

| 项目     | 值                 |
| -------- | ------------------ |
| 抽屉尺寸 | 265×365mm × 2份    |
| 分割方案 | 7×5 × 2 + 3×5 × 2  |
| 瓦片数量 | 4 stack            |
| 打印时间 | 12.4 分钟          |
| 预估耗材 | 45.2g              |
| 库存使用 | 7×5 × 2 (从库存取) |
| 节省     | 50% (如有库存)     |

**4. 对比表格**（当展示两种方案时）

| 项目     | 方案 A        | 方案 B        |
| -------- | ------------- | ------------- |
| 分割     | 7×5×2 + 3×5×2 | 7×5×2 + 3×5×2 |
| 需打印   | 4 stack       | 2 stack       |
| 打印时间 | 12.4 min      | 6.2 min       |
| 耗材     | 45.2g         | 22.6g         |

**5. 用户引导**

```
[ A ] 方案 A - 不考虑库存 (X次打印, Xh, Xg)
[ B ] 方案 B - 使用库存 (X次打印, Xh, Xg, 节省库存)
[ G ] 生成 STL 文件（默认方案 B）
[ Q ] 退出
```

### Step 5: 生成 STL 文件

用户选择方案后，生成 STL 文件。

#### 5.1 获取方案 JSON

获取方案的 JSON 输出：

```bash
python scripts/opengrid.py split 265x365 -j > scheme.json
```

#### 5.2 提取需要打印的瓦片

从 JSON 中提取需要打印的瓦片（不含从库存取的瓦片）。

#### 5.3 调用 STL 生成

使用 `opengrid slicer generate` 命令：

```bash
python scripts/opengrid.py slicer generate 7x5x2
python scripts/opengrid.py slicer generate 3x5x2
```

#### 5.4 展示生成结果

STL 生成完成后，向用户展示结果。

```
--- STL 生成完成 ---
输出目录: ~/3D打印/opengrid/

生成的文件:
  7×5: 2 stack (~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl)
  3×5: 2 stack (~/3D打印/opengrid/3x5_Full/opengrid_3x5_Full_s2.stl)
```

#### 5.5 后续操作

询问用户是否需要后续操作：

```
生成完成！

[ O ] 在 slicer 中打开 STL
[ S ] 切片 STL (生成 3MF)
[ D ] 在文件夹中显示
[ Q ] 退出
```

**打开 slicer**:

```python
# 在 OrcaSlicer 中打开
from scripts.slicer import open_in_slicer
stl_files = [
    "~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl",
    "~/3D打印/opengrid/3x5_Full/opengrid_3x5_Full_s2.stl"
]
open_in_slicer(stl_files, slicer="orca")
```

**切片 STL** (可选):

```bash
# 切片单个文件
uv run scripts/slicer.py -s "~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl" --slicer orca

# 切片多个文件
uv run scripts/slicer.py -s "file1.stl" "file2.stl" --slicer orca --output my_drawer
```

## 快速命令

使用 `${CLAUDE_PLUGIN_ROOT}` 变量引用插件根目录：

```bash
# 查看项目状态
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py status

# 批量计算
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py split 265x365:2 325x365:2

# 单尺寸计算
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py split 485 425

# 使用库存
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py split 265x365:2 -i inventory.json

# 生成 STL
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py slicer generate 7x5x2
```

详细命令、配置说明、算法规则等请参考 [references/](references/) 目录。

## 配置文件

openGrid 使用项目级配置文件，必须在项目目录下存在 `opengrid_config.yaml`。

### 项目配置

位置：`{当前目录}/opengrid_config.yaml`

项目配置示例：

```yaml
initialized: true
printer:
  model: h2d
inventory_path: ./inventory.json  # 项目库存文件路径
output:
  stl_dir: ./stl_output/  # 项目输出目录
```

**注意**：脚本必须在有 `opengrid_config.yaml` 的目录下运行，否则会报错。

## 初始化

首次使用前完成配置，运行一次安装脚本即可完成所有设置：

```bash
cd ${CLAUDE_PLUGIN_ROOT}
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
uv run scripts/split_calc.py 485 425
```
