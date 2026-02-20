---
name: opengrid-drawer-filler
description: 计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。根据抽屉尺寸计算最优 openGrid 瓦片布局，支持库存管理和批量计算。当用户需要为抽屉创建 3D 打印瓦片铺满方案时使用此技能。
compatibility: 需要 Python 3.12+, OpenSCAD, Python 依赖 (pyyaml, Pillow, pytest)
---

# openGrid 抽屉铺满

根据抽屉尺寸计算最优瓦片分割方案，并可自动生成 STL 文件用于 3D 打印。

## 核心原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不应有 `input()` 交互代码
- Agent 询问用户需求，调用脚本获取结果，展示给用户

## Agent 工作流

### Step 1: 检查配置、加载库存、展示状态

1. 加载配置（使用 Python 直接读取或调用 config 模块）
2. 加载库存文件 `inventory/inventory.json`
3. 向用户输出当前状态（库存信息突出展示）：

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

4. 检查 `config/config.yaml` 的 `initialized` 状态
5. 如未初始化，引导用户配置：
   - 复制配置文件：`cp config/config.example.yaml config/config.yaml`
   - 编辑设置 `initialized: true` 和打印机型号
6. **确认库存数量是否正确**，如不正确引导用户更新

### 库存管理

**严格禁止直接编辑 `inventory/inventory.json` 文件。**

所有库存修改必须通过脚本进行，并记录修改原因：

```bash
# 查看当前库存
.venv/bin/python scripts/inventory.py list

# 添加库存 (格式: 宽x高:数量)
.venv/bin/python scripts/inventory.py add 8x8:5 6x7:3 "入库原因：购买新材料"

# 扣减库存
.venv/bin/python scripts/inventory.py deduct 8x8:2 "扣减原因：打印使用"

# 撤销上次操作
.venv/bin/python scripts/inventory.py undo
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

### Step 3: 计算方案

**自动双方案**：当检测到有库存时，自动计算两种方案：

1. 方案 A：不考虑库存（最优打印次数）
2. 方案 B：使用库存

**无库存时**：只计算方案 A（标准最优方案）

调用 `split_calc.py`：

```bash
# 方案 A：不使用库存（用于对比）
python3 scripts/split_calc.py -b "265x365:2 325x365:2" -i ""

# 方案 B：使用库存（默认）
python3 scripts/split_calc.py -b "265x365:2 325x365:2"
```

**注意**：当库存充足时，方案 B 可能打印次数更少；当库存不匹配时，方案 A 可能反而更优。

### Step 4: 展示方案

将脚本输出展示给用户，询问选择。

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

用户选择方案后，调用 `slicer.py` 生成 STL 文件。

#### 5.1 提取需要打印的瓦片

从方案中提取需要打印的瓦片（**不含从库存取的瓦片**）：

```python
# 从 scheme 中获取需要打印的瓦片
# scheme['tiles'] 是所有瓦片 [(w, h), ...]
# scheme['need_print'] 是需要打印的瓦片 {"6x7": 2, ...}

# 构建只需要打印的瓦片列表
tiles_to_print = []
for w, h in scheme['tiles']:
    key = f"{w}x{h}"
    if key in scheme.get('need_print', {}) and scheme['need_print'][key] > 0:
        tiles_to_print.append((w, h))
        # 减少计数
        scheme['need_print'][key] -= 1
```

#### 5.2 调用 STL 生成

调用 `scripts/slicer.py` 中的 `generate_all_stls` 函数：

```bash
# 方法1：使用 Python 模块
cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
.venv/bin/python -c "
import sys
sys.path.insert(0, 'scripts')
from slicer import generate_all_stls

# 构造 scheme 字典（只包含需要打印的瓦片）
scheme = {
    'tiles': [(7, 5), (3, 5)]  # 只包含需要打印的瓦片
}

result = generate_all_stls(scheme, copies=1, verbose=True)
print('Generated:', result)
"

# 方法2：直接调用脚本
.venv/bin/python scripts/slicer.py -g 7x5x2 3x5x2
```

#### 5.3 展示生成结果

STL 生成完成后，向用户展示结果：

```
--- STL 生成完成 ---
输出目录: ~/3D打印/opengrid/

生成的文件:
  7×5: 2 stack (~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl)
  3×5: 2 stack (~/3D打印/opengrid/3x5_Full/opengrid_3x5_Full_s2.stl)
```

#### 5.4 后续操作

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
.venv/bin/python scripts/slicer.py -s "~/3D打印/opengrid/7x5_Full/opengrid_7x5_Full_s2.stl" --slicer orca

# 切片多个文件
.venv/bin/python scripts/slicer.py -s "file1.stl" "file2.stl" --slicer orca --output my_drawer
```

## 快速命令

```bash
# 批量计算
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# 单尺寸计算
python3 scripts/split_calc.py 485 425

# 使用预设
python3 scripts/split_calc.py -p klean

# 生成 STL
python3 scripts/slicer.py -g 7x5x3 10x5x3
```

详细命令、配置说明、算法规则等请参考 [references/](references/) 目录。

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
