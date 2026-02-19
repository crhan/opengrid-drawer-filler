---
name: opengrid-drawer-filler
description: Calculates optimal openGrid tile layout for drawer bottom filling with end-to-end STL generation
---

# openGrid 抽屉铺满

根据抽屉尺寸计算最优瓦片分割方案，并可自动生成 STL 文件。

## 快速开始

```bash
# 方式 1：交互式（推荐）
python3 scripts/split_calc.py

# 方式 2：指定尺寸
python3 scripts/split_calc.py 485 425

# 方式 3：指定份数
python3 scripts/split_calc.py 485 425 -c 3

# 方式 4：批量计算（自动合并优化）
python3 scripts/split_calc.py -b "265x365:2 325x365:2 315x365:2"

# 方式 5：生成 STL（使用 slicer.py）
python3 scripts/slicer.py -g 7x5x3 10x5x3 --force
```

## 初始化

首次使用前完成配置：

1. 运行 setup.sh：
   ```bash
   cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
   ./scripts/setup.sh
   ```

2. 复制配置文件：
   ```bash
   cp config.example.yaml config.yaml
   ```

3. 编辑 config.yaml，设置 `initialized: true` 和打印机型号

未配置时运行会显示详细步骤。

## 批量计算模式

支持一次输入多个尺寸和份数，系统会自动：
1. 分别计算每个尺寸的最优分割方案
2. 合并所有尺寸，统计共用瓦片
3. 输出优化后的打印计划（减少总打印次数）

### 输入格式

支持多种格式：
```bash
# 格式1: 宽x高:份数（推荐）
-b "265x365:2 325x365:2 315x365:2"

# 格式2: 宽x高（默认1份）
-b "265x365 325x365 315x365"

# 格式3: 宽 高 份数（空格分隔）
-b "265 365 2 325 365 2 315 365 2"
```

### 输出示例

```
解析到 3 个尺寸:
  265×365mm × 2份
  325×365mm × 2份
  315×365mm × 2份

--- 合并后的瓦片清单（可一起打印）---

6×7 格:
  来源: 325×365 × 2份 = 2 stack
  来源: 315×365 × 2份 = 2 stack
  需打印: 1次 (4 stack, 29mm)

...

--- 总计 ---
总耗材: ~959g
总打印次数: 6次
总打印时间: ~41h38m
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| width | 抽屉内部宽度 (mm) | 交互询问 |
| depth | 抽屉内部深度 (mm) | 交互询问 |
| -c, --copies | 打印份数 | 1 |
| -b, --batch | 批量计算（自动合并优化） | 无 |
| -p, --preset | 预设尺寸 | 无 |
| -j, --json | JSON 格式输出 | false |
| -v, --verbose | 详细输出 | false |

## 预设尺寸

```bash
# 常用抽屉尺寸预设
-p klean       # Klean件盒 270×170mm
-p ikea-sunda  # IKEA Sunda 36×50cm
-p ikea-kal    # IKEA KAL 36×50cm
-p ikea alex   # IKEA Alex 36×50cm
-p standard    # 标准 400×400mm
```

## 输出示例

```
抽屉尺寸: 485mm × 425mm
有效格子: 17 × 15 = 255格
打印份数: 1套

--- 分割方案 ---
分割: 2×3
X方向: 17 = 7 + 10
Y方向: 15 = 5 + 5 + 5

排布:
7×5 10×5
7×5 10×5
7×5 10×5

--- 瓦片清单 ---
7×5: 3块 (高度 71mm)
       耗材: 119.7g, 时间: 47m
10×5: 3块 (高度 71mm)
       耗材: 170.9g, 时间: 67m

--- 耗材估算 ---
主耗材: ~291g
支撑耗材: ~16g
总耗材: ~307g (1份)

--- 打印时间估算 ---
预计总时间: ~3h31m (6次打印)
```

## 端到端工作流

### 方式 1：计算方案

```bash
python3 scripts/split_calc.py 485 425 -j
```

### 方式 2：生成 STL（使用 slicer.py）

根据上一步输出的方案，生成对应的 STL：

```bash
# 假设方案输出 7x5:3 和 10x5:3
python3 scripts/slicer.py -g 7x5x3 10x5x3
```

### 方式 3：在 slicer 中打开或切片

```bash
# 在 Orca Slicer 中打开
python3 scripts/slicer.py -o path/to/file.stl --slicer orca

# 或者切片
python3 scripts/slicer.py -s path/to/file.stl --slicer orca --output my_project
```

### JSON 输出示例

```json
{
  "drawer": { "width": 485, "depth": 425 },
  "grid": { "x": 17, "y": 15 },
  "scheme": {
    "x_parts": 2,
    "y_parts": 3,
    "x_splits": [7, 10],
    "y_splits": [5, 5, 5],
    "tiles": [
      {"width": 7, "height": 5, "count": 3},
      {"width": 10, "height": 5, "count": 3}
    ]
  },
  "stats": {
    "unique_sizes": 2,
    "total_tiles": 6,
    "total_filament_g": 307,
    "total_time_min": 211
  }
}
```

## 算法规则

- **最大瓦片**: 10×11格
- **最小瓦片**: 2×2格
- **优先级**: 独特尺寸最少 → 瓦片数最少 → 均衡度最好
- **搜索终止**: 找到1种尺寸时提前终止

## 耗材估算

| 常量 | 值 | 说明 |
|------|-----|------|
| 单格耗材 | 1.13g | 主耗材/格/层 |
| 单格支撑 | 0.06g | 支撑耗材/格/层 |
| 单格时间 | 3.1min | 打印时间/格/层 |
| 层高 | 7.2mm | Full 6.8mm + 0.4mm 间距 |
| Z轴限制 | 325mm | 约 45 stack |

## 故障排除

**Q: 无法生成有效方案？**
- 抽屉尺寸可能太小或太大
- 尝试增加分割数（当前最多 20 块瓦片）

**Q: 打印次数太多？**
- 使用 `-c 1` 先打印一份测试
- 考虑分批打印

**Q: STL 生成失败？**
- 检查 OpenSCAD 是否已安装
- 确认 SCAD 文件路径正确

## Slicer 集成

### Orca Slicer CLI 研究结果

**注意**: Orca Slicer CLI 在 macOS 上需要显示上下文（OpenGL），无法无头运行。

**已测试的功能**:
- `--arrange 1` - 自动排列模型
- `--load-settings` - 加载机器/工艺设置
- `--load-filaments` - 加载耗材设置
- `--export-3mf` - 导出 3MF 项目

**需要的配置文件**:
```bash
# 机器配置（需要 nozzle-specific）
--load-settings "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/machine/Bambu Lab P1P 0.4 nozzle.json"

# 工艺配置
--load-settings "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/process/0.20mm Standard @BBL P1P.json"

# 耗材配置
--load-filaments "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/filament/P1P/Bambu PLA Basic @BBL P1P.json"
```

**当前限制**: CLI 需要 GUI 环境运行，无法在服务器/无界面环境使用。

### 替代方案

1. **直接打开 STL**: 使用 `-o` 选项在 OrcaSlicer/BambuStudio 中打开生成的 STL
2. **手动排版**: 在 slicer 中手动排列模型并选择预设
3. **使用 3MF 模板**: 手动创建包含预设的 3MF 项目，后续复用

## STL 生成工具 (slicer.py)

`scripts/slicer.py` 负责 STL 文件生成和切片。

### 使用方式

```bash
# 生成单个 STL
python3 scripts/slicer.py -g 7x5x3          # 格式: 宽x高x层数
python3 scripts/slicer.py -g 7x5x3 --force  # 强制重新生成

# 批量生成多个 STL
python3 scripts/slicer.py -g 7x5x3 10x5x3 5x5x1

# 在 slicer 中打开 STL
python3 scripts/slicer.py -o file.stl --slicer orca
python3 scripts/slicer.py -o file1.stl file2.stl --slicer bambu

# 切片 STL 文件
python3 scripts/slicer.py -s file.stl --slicer orca --output my_project
```

### Python 模块调用

```python
from scripts.slicer import (
    generate_stl,
    generate_all_stls,
    slice_with_bambu,
    slice_with_orca,
    open_in_slicer,
)

# 生成单个 STL
path, err = generate_stl(7, 5, 3, verbose=True, force=False)

# 批量生成
stl_files = generate_all_stls(scheme, copies=2, verbose=True)

# 切片
result, err = slice_with_orca(stl_files, "my_project")

# 在 slicer 中打开
open_in_slicer(stl_files, slicer="orca")
```

### 分步工作流

1. **计算分割方案** → `scripts/split_calc.py`
2. **生成 STL** → `scripts/slicer.py -g`
3. **切片或打开** → `scripts/slicer.py -s` 或 `scripts/slicer.py -o`
