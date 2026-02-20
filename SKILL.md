---
name: opengrid-drawer-filler
description: Calculates optimal openGrid tile layout for drawer bottom filling with end-to-end STL generation
---

# openGrid 抽屉铺满

根据抽屉尺寸计算最优瓦片分割方案，并可自动生成 STL 文件用于 3D 打印。

## 核心原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不应有 `input()` 交互代码
- Agent 询问用户需求，调用脚本获取结果，展示给用户

## Agent 工作流

### Step 1: 检查配置并展示状态

1. 首先加载配置（使用 Python 直接读取或调用 config 模块）
2. 直接向用户输出当前状态：

   **openGrid 抽屉铺满**

   | | |
   |---|---|
   | 🖨️ 打印机 | **[型号]** ([bed_x]×[bed_y]×[max_z]mm) |
   | 📁 输出目录 | `[stl_dir]` |
   | 📦 库存 | [库存列表或"无库存"] |
   | 🔧 瓦片类型 | [tile_type] \| 堆叠: [stacking_method] |

3. 读取 `config.yaml` 检查 `initialized` 状态
4. 如果未初始化，引导用户配置：
   - 复制配置文件：`cp config.example.yaml config.yaml`
   - 编辑设置 `initialized: true` 和打印机型号

### Step 2: 询问需求

1. 询问抽屉尺寸和份数
2. 解析尺寸格式：
   - `"265x360:2"` = 265×360mm，2份
   - `"265x360"` = 265×360mm，1份
   - `"265 360 2"` = 空格分隔格式

### Step 3: 确认库存

**注意：这个环节你必须要和用户交互来确认库存数量是否正确，如果不正确就引导用户更新库存**

1. 检查库存文件 `scripts/inventory.json`
2. 列出库存瓦片（如有库存）
3. 询问用户是否使用库存计算

**库存为空时**：提示用户并询问是继续计算还是先入库

### Step 4: 计算方案

根据用户选择执行：

- **不使用库存**：按原有逻辑计算最优方案
- **使用库存**：计算并展示两种方案：
  1. 不考虑库存的最优方案
  2. 考虑库存的方案（显示节省多少打印）

展示两种方案供用户选择

调用 `split_calc.py`：

```bash
# 批量模式（自动合并优化）
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# 单尺寸模式
python3 scripts/split_calc.py 485 425

# 使用预设
python3 scripts/split_calc.py -p klean

# JSON 输出（便于解析）
python3 scripts/split_calc.py 485 425 -j
```

### Step 5: 展示方案

将脚本输出展示给用户，询问选择。

#### 展示内容规范

**1. 可视化布局**（风格2：带尺寸标注）

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

**2. 详细统计**

| 项目     | 值                 |
| -------- | ------------------ |
| 抽屉尺寸 | 265×365mm × 2份    |
| 分割方案 | 7×5 × 2 + 3×5 × 2  |
| 瓦片数量 | 4 stack            |
| 打印时间 | 12.4 分钟          |
| 预估耗材 | 45.2g              |
| 库存使用 | 7×5 × 2 (从库存取) |
| 节省     | 50% (如有库存)     |

**3. 对比表格**（当展示两种方案时）

| 项目     | 方案 A        | 方案 B        |
| -------- | ------------- | ------------- |
| 分割     | 7×5×2 + 3×5×2 | 7×5×2 + 3×5×2 |
| 需打印   | 4 stack       | 2 stack       |
| 打印时间 | 12.4 min      | 6.2 min       |
| 耗材     | 45.2g         | 22.6g         |

**4. 用户引导**

```
请选择方案：
[ A ] 方案 A - 标准分割
[ B ] 方案 B - 使用库存（节省 50%）
[ Q ] 退出
```

### Step 6: 生成文件

1. 调用 `slicer.py` 生成 STL
2. 调用 `visualizer.py` 生成 HTML 打印计划

## 脚本职责

| 脚本                  | 功能             | 修改状态      |
| --------------------- | ---------------- | ------------- |
| `split_calc.py`       | 批量计算分割方案 | ✅ 已移除交互 |
| `scheme_generator.py` | 生成多方案       | 保留          |
| `scheme_presenter.py` | 格式化方案输出   | 保留          |
| `slicer.py`           | STL 生成         | 保留          |
| `project_manager.py`  | 项目管理         | 保留          |
| `visualizer.py`       | HTML 生成        | 保留          |
| `config.py`           | 配置加载         | ✅ 已简化     |
| `interactive.py`      | 入口             | ❌ 已删除     |

## 命令参考

### 批量计算

```bash
# 格式1: 宽x高:份数（推荐）
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# 格式2: 宽x高（默认1份）
python3 scripts/split_calc.py -b "265x365 325x365"

# 格式3: 宽 高 份数（空格分隔）
python3 scripts/split_calc.py -b "265 365 2 325 365 2"
```

### 单尺寸计算

```bash
python3 scripts/split_calc.py 485 425        # 指定尺寸
python3 scripts/split_calc.py 485 425 -c 3   # 指定份数
python3 scripts/split_calc.py -p klean      # 使用预设
python3 scripts/split_calc.py 485 425 -j    # JSON 输出
```

### 预设尺寸

```bash
--list-presets                          # 列出所有预设
-p klean                                # Klean件盒 270×170mm
-p ikea-sunda                           # IKEA Sunda 360×500mm
-p ikea-kal                             # IKEA KAL 360×500mm
-p ikea-alex                            # IKEA Alex 360×500mm
-p standard                             # 标准抽屉 400×400mm
```

### 生成 STL

```bash
# 假设方案输出 7x5:3 和 10x5:3
python3 scripts/slicer.py -g 7x5x3 10x5x3
```

### 在 slicer 中打开

```bash
python3 scripts/slicer.py -o file.stl --slicer orca
python3 scripts/slicer.py -o file.stl --slicer bambu
```

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

## 配置文件 (config.yaml)

```yaml
# 基本设置
initialized: true
printer:
  model: p1s # 打印机型号 (a1_mini, a1, p1p, p1s, x1c, x1e, h2d)
  bed_x: 256 # 热床宽度 mm
  bed_y: 256 # 热床深度 mm
  max_z: 256 # 最大打印高度 mm

# openGrid 参数
opengrid:
  tile_type: Full # 瓦片类型 (Full, Half)
  stacking_method: Ironing # 堆叠方式 (Ironing, Flat)

# 输出设置
output:
  stl_dir: "~/Documents/opengrid/stls/"
  projects_dir: "~/Documents/opengrid/projects/"

# 库存管理（可选）
inventory:
  enabled: true
  file: "inventory.yaml"
```

## 算法规则

- **最大瓦片**: 10×11格
- **最小瓦片**: 2×2格
- **优先级**: 独特尺寸最少 → 瓦片数最少 → 均衡度最好
- **搜索终止**: 找到1种尺寸时提前终止

## 耗材估算

| 常量     | 值     | 说明                    |
| -------- | ------ | ----------------------- |
| 单格耗材 | 1.13g  | 主耗材/格/层            |
| 单格支撑 | 0.06g  | 支撑耗材/格/层          |
| 单格时间 | 3.1min | 打印时间/格/层          |
| 层高     | 7.2mm  | Full 6.8mm + 0.4mm 间距 |
| Z轴限制  | 325mm  | 约 45 stack             |

## 故障排除

**Q: 脚本运行失败？**

- 重新运行安装脚本：`./scripts/setup.sh`
- 确保配置文件存在

**Q: 无法生成有效方案？**

- 抽屉尺寸可能太小或太大
- 尝试增加分割数（当前最多 20 块瓦片）

**Q: STL 生成失败？**

- 检查 OpenSCAD 是否已安装
- 确认 SCAD 文件路径正确

## Slicer 集成

### Orca Slicer CLI

**注意**: Orca Slicer CLI 在 macOS 上需要显示上下文（OpenGL），无法无头运行。

**已测试的功能**:

- `--arrange 1` - 自动排列模型
- `--load-settings` - 加载机器/工艺设置
- `--load-filaments` - 加载耗材设置
- `--export-3mf` - 导出 3MF 项目

**当前限制**: CLI 需要 GUI 环境运行，无法在服务器/无界面环境使用。

### 替代方案

1. **直接打开 STL**: 使用 `-o` 选项在 OrcaSlicer/BambuStudio 中打开生成的 STL
2. **手动排版**: 在 slicer 中手动排列模型并选择预设
3. **使用 3MF 模板**: 手动创建包含预设的 3MF 项目，后续复用

## 模块调用

```python
# 方案计算
from scripts.split_calc import find_best_scheme, get_grid_dimensions

x, y = get_grid_dimensions(485, 425)
scheme = find_best_scheme(x, y)

# STL 生成
from scripts.slicer import generate_stl, generate_all_stls

path, err = generate_stl(7, 5, 3, verbose=True, force=False)

# 项目管理
from scripts.project_manager import ProjectManager

pm = ProjectManager("~/opengrid_projects/")
project_path = pm.create_project("my-project", drawers)

# HTML 生成
from scripts.visualizer import Visualizer

v = Visualizer()
v.generate_html(project_path, scheme, tiles)
```
