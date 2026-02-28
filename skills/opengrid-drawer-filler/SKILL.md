---
name: opengrid-drawer-filler
description: 计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。根据抽屉尺寸计算最优 openGrid 瓦片布局，支持库存管理和批量计算。当用户需要为抽屉创建 3D 打印瓦片铺满方案时使用此技能。
compatibility: 需要 Python 3.12+, OpenSCAD, Python 依赖 (pyyaml, Pillow, pytest)
---

# openGrid 抽屉铺满

## 核心原则

**Agent 负责用户交互，脚本负责计算和生成。**

- Agent 询问用户需求，调用脚本获取结果，展示给用户

## Agent 工作流

```mermaid
flowchart TD
    A[Step 1: 查找配置文件和库存文件\n通过 -c 和 -i 参数传给脚本] --> B{配置存在?}
    B -- 否 --> C[提示运行 /setup]
    B -- 是 --> D[Step 2: 询问需求\n用户输入尺寸]
    D --> E{重复尺寸?}
    E -- 是 --> F[命名抽屉: 抽屉A, 抽屉B...]
    E -- 否 --> G[Step 3: 计算方案\n生成方案A和方案B JSON]
    F --> G
    G --> H[Step 4: 展示方案\n终端对比展示]
    H --> I{用户选择}
    I --> J[方案A]
    I --> K[方案B]
    I --> L[HTML对比]
    L --> M[opengrid compare\n生成并打开HTML]
    M --> H
    J --> N[Step 5: 确认库存扣减]
    K --> N
    N --> O{是否扣减库存?}
    O -- 是 --> P[调用 inventory deduct]
    O -- 否 --> Q[Step 6: 生成STL]
    P --> Q
```

### Step 1: 查找配置文件和库存文件

**强制要求**: 必须先查找配置文件和库存文件位置，然后通过参数传给脚本确认现状。

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

#### 1.2 定位配置文件和库存文件

**关键原则**：库存文件在**当前项目目录**，不是 skill 目录！

查找顺序：
1. **首先检查当前目录**是否有 `opengrid_config.yaml`
2. 根据配置中的 `inventory_path` 定位库存文件（通常是 `./inventory.json`）

如果当前目录没有配置文件，说明不是 opengrid 项目，需要先初始化。

#### 1.3 运行 status 命令确认现状

传入配置文件和库存文件路径：

```bash
# 传入配置文件和库存文件路径
uv run scripts/opengrid.py -c ./opengrid_config.yaml -i ./inventory.json status
```

**如果配置文件不在当前目录**，使用 `--config` 参数指定：

```bash
# 配置文件在父目录
uv run scripts/opengrid.py -c ../opengrid_config.yaml status

# 使用绝对路径
uv run scripts/opengrid.py -c /path/to/opengrid_config.yaml status
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
uv run scripts/opengrid.py inventory list

# 添加库存 (格式: 宽x高:数量)
uv run scripts/opengrid.py inventory add 8x8:5 6x7:3 "入库原因"

# 扣减库存
uv run scripts/opengrid.py inventory deduct 8x8:2 "扣减原因"

# 撤销上次操作
uv run scripts/opengrid.py inventory undo
```

**重要**：执行 inventory 命令时必须：

1. **指定配置文件路径**（使用 `-c` 参数）
2. 使用绝对路径或相对于当前目录的路径

```bash
# 指定配置文件
uv run scripts/opengrid.py -c ./opengrid_config.yaml inventory list
```

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

**抽屉命名**: 用户输入尺寸后，按首次出现顺序命名。例如：

- 抽屉A = 第一个尺寸
- 抽屉B = 第二个尺寸（以此类推）
  后续统一使用抽屉名称（如"抽屉A"）进行展示和交互。

### Step 3: 计算方案

**自动双方案**：当检测到有库存时，自动计算两种方案：

1. 方案 A：不考虑库存（最优打印次数）
2. 方案 B：使用库存

**无库存时**：只计算方案 A（标准最优方案）

同时计算方案A（无库存）和方案B（有库存），同时生成两个 JSON 文件保存到当前目录，供后续使用。

使用 `opengrid split` 命令：

```bash
# 方案 A：不使用库存
uv run scripts/opengrid.py split 265x365:2 325x365:2

# 方案 B：使用库存（通过 -i 指定库存文件）
uv run scripts/opengrid.py -i inventory.json split 265x365:2 325x365:2
```

### Step 4: 展示方案

终端简洁格式：

```
=== 抽屉A: 265x365mm x2 ===

[A] 方案A: 2次打印, ~25分钟, ~95g
[B] 方案B: 1次打印, ~12分钟, ~45g (节省52%)

瓦片对比:
    7x5: A=x4(打印), B=x2(库)+x2(打印)
    3x5: A=x4(打印), B=x4(打印)

[H] 生成HTML对比页面
[Q] 退出
```

将脚本输出展示给用户，询问选择。可选：使用 `present` 命令生成 HTML 对比页面。

#### 使用 present 命令（可选）

```bash
# 先生成两个方案的 JSON
uv run scripts/opengrid.py split 325x460 -j > scheme_no_inv.json
uv run scripts/opengrid.py -i inventory.json split 325x460 -j > scheme_with_inv.json

# 生成 HTML 对比页面
uv run scripts/opengrid.py present scheme_no_inv.json scheme_with_inv.json -o comparison.html
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

用户选择方案后询问：

- `[Y] 确认扣减库存并生成 STL`
- `[N] 只生成 STL，不扣减库存`

确认后，生成 STL 文件。

#### 5.1 获取方案 JSON

获取方案的 JSON 输出：

```bash
uv run scripts/opengrid.py split 265x365 -j > scheme.json
```

#### 5.2 提取需要打印的瓦片

从 JSON 中提取需要打印的瓦片（不含从库存取的瓦片）。

#### 5.3 调用 STL 生成

使用 `opengrid slicer generate` 命令：

```bash
uv run scripts/opengrid.py slicer generate 7x5x2
uv run scripts/opengrid.py slicer generate 3x5x2
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
uv run scripts/opengrid.py slicer slice -s "~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl" --slicer orca

# 切片多个文件
uv run scripts/opengrid.py slicer slice -s "file1.stl" "file2.stl" --slicer orca --output my_drawer
```

## 快速命令

使用 `${CLAUDE_PLUGIN_ROOT}` 变量引用插件根目录：

```bash
# 查看项目状态（自动查找配置）
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py status

# 指定配置文件和库存
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py -c ./opengrid_config.yaml -i ./inventory.json status

# 批量计算
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py split 265x365:2 325x365:2

# 单尺寸计算
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py split 485 425

# 使用库存
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py -i inventory.json split 265x365:2

# 生成 STL
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py slicer generate 7x5x2

# 生成 HTML 对比并打开
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/opengrid.py compare scheme_a.json scheme_b.json -o comparison.html
```

详细命令、配置说明、算法规则等请参考以下文档：

- [references/CONFIG.md](references/CONFIG.md) - 配置文件详解（打印机预设、瓦片类型）
- [references/ALGORITHM.md](references/ALGORITHM.md) - 算法规则（优先级、分割约束）
- [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) - 故障排除指南
- [references/SLICER.md](references/SLICER.md) - Slicer 集成说明

## 配置文件

openGrid 使用项目级配置文件，必须在项目目录下存在 `opengrid_config.yaml`。

### 项目配置

位置：`{当前目录}/opengrid_config.yaml`

项目配置示例：

```yaml
initialized: true
printer:
  model: h2d
inventory_path: ./inventory.json # 项目库存文件路径
output:
  stl_dir: ./stl_output/ # 项目输出目录
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
uv run scripts/opengrid.py split 485 425
```
