# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 **Claude Code 插件** (Claude Plugin)，名为 `opengrid-drawer-filler`。

功能：计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。

## 插件结构

```
opengrid_plugin/                    # 插件根目录
├── .claude-plugin/
│   └── plugin.json                 # 插件清单 (必须)
│
├── skills/                         # Agent Skills
│   ├── opengrid-drawer-filler/     # 主技能：抽屉铺满计算
│   │   ├── SKILL.md               # 技能定义
│   │   └── references/            # 参考文档
│   └── opengrid-drawer-filler-setup/ # 安装配置技能
│
├── opengrid/                       # 核心 Python 库 (技能调用)
│   ├── core/                      # 核心算法
│   ├── stl/                       # STL 生成
│   └── ui/                        # 输出展示
│
├── scripts/                       # CLI 入口脚本
│   ├── split_calc.py              # 批量计算
│   ├── slicer.py                  # STL 生成
│   └── inventory.py               # 库存管理
│
└── tests/                         # 测试目录
```

### 插件清单 (plugin.json)

```json
{
  "name": "opengrid-drawer-filler",
  "skills": "./skills"
}
```

## 开发工作流

### 本地测试插件

使用 `--plugin-dir` 加载插件进行测试：

```bash
claude --plugin-dir /Users/ruohanc/Documents/projects/opengrid_plugin
```

测试技能调用：

```
/opengrid-drawer-filler 265x365
```

### 开发循环

1. 修改代码或技能定义
2. 重启 Claude Code 加载更新
3. 测试功能

### 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_scheme.py

# 运行单个测试
uv run pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed
```

## 常用命令

```bash
# 分割计算
uv run scripts/opengrid.py split 325x460
uv run scripts/opengrid.py split 325x460 -i inventory.json

# JSON 输出
uv run scripts/opengrid.py split 325x460 -j

# 方案对比（生成 HTML）
uv run scripts/opengrid.py split 325x460 -j > scheme_a.json
uv run scripts/opengrid.py split 325x460 -i inventory.json -j > scheme_b.json
uv run scripts/opengrid.py present scheme_a.json scheme_b.json -o comparison.html

# 库存管理
uv run scripts/opengrid.py inventory list
uv run scripts/opengrid.py inventory add 8x8:5 "原因"
uv run scripts/opengrid.py inventory deduct 8x8:2 "原因"
```

## 代码分析工具 (contextplus MCP)

本项目配置了 **contextplus** MCP 服务，提供基于语义理解的代码分析能力。

### 核心工具

| 工具 | 用途 |
|------|------|
| `semantic_code_search` | 按语义搜索代码，不仅仅是精确的变量名。例如搜索"抽屉分割算法"能找到相关函数 |
| `semantic_identifier_search` | 语义级别搜索标识符（函数、方法、类、变量），返回定义行和调用链 |
| `get_file_skeleton` | 获取文件的详细函数签名、类方法、类型定义，不读取完整代码体 |
| `get_context_tree` | 获取项目的结构树，包含文件头、函数名、类、枚举和行范围 |
| `get_blast_radius` | 在删除或修改代码前检查爆炸半径，追踪特定符号在代码库中的使用位置 |
| `run_static_analysis` | 运行项目的原生 linter/compiler 来查找未使用变量、死代码、类型错误 |
| `semantic_navigate` | 按语义浏览代码库，使用聚类将相关文件分组 |
| `get_feature_hub` | Obsidian 风格的特性中心导航器，通过 wiki 链接组织相关文件 |

### 使用场景

- **理解代码结构**：使用 `get_context_tree` 或 `get_file_skeleton` 快速了解模块 API
- **搜索功能**：使用 `semantic_code_search` 按自然语言意图搜索，而非精确匹配
- **追踪调用链**：使用 `semantic_identifier_search` 找到函数的所有调用位置
- **重构前检查**：使用 `get_blast_radius` 了解修改代码的影响范围
- **代码质量检查**：使用 `run_static_analysis` 查找类型错误和死代码

### 示例

```
# 语义搜索"分割计算"
mcp__contextplus__semantic_code_search("抽屉分割算法")

# 查找函数调用
mcp__contextplus__semantic_identifier_search("find_best_scheme")

# 获取文件骨架
mcp__contextplus__get_file_skeleton("opengrid/core/scheme.py")

# 检查修改影响
mcp__contextplus__get_blast_radius("Tile", "opengrid/core/tile.py")
```

## 核心设计原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不含 `input()` 或交互式提示
- 脚本只做计算，Agent 处理用户交互
- 完整工作流见 [SKILL.md](SKILL.md)

## 库存管理约束

- **禁止直接编辑** `inventory/inventory.json`
- 必须通过脚本修改并提供原因
- 每次操作记录到日志

## 核心常量

- `TILE_SIZE = 28` - 网格单元格大小 (mm)
- `MAX_X = 10`, `MAX_Y = 11` - 最大瓦片尺寸
- `FULL_THICKNESS = 7.2` - 单层厚度
- `MAX_Z = 325` - 打印机 Z 轴限制

### 算法优先级

最小化独特尺寸 → 最小化瓦片总数 → 最大化均衡度

# OpenGrid 体系与 3D 打印生产术语规范 (v1.0)

## 1. 核心词汇定义 (Core Definitions)

### **Grid (网格标准)**

- **本质**：逻辑协议 / 度量衡。
- **定义**：指整个生态系统遵循的几何对齐规则。在 OpenGrid 体系中，标准 Grid 间距为 **28mm**。
- **作用**：确保不同来源的配件（Hooks, Bins, Snaps）在空间上具有互操作性。

### **Cell (单元格)**

- **本质**：最小空间单位。
- **定义**：Grid 系统中最小的 $1 \times 1$ 区域（即 $28\text{mm} \times 28\text{mm}$ 的方格）。
- **作用**：用于描述附件的尺寸（如“这个盒子占 $2 \times 3$ Cells”）或定位安装点。

### **Tile (基础面板)**

- **本质**：物理实体对象。
- **定义**：由 $M \times N$ 个 Cells 组成的单块打印成品底板。
- **分类**：包括 Standard Tile, Lite Tile, 或是兼容 Gridfinity 的适配 Tile。

### **Stack (生产堆叠)**

- **本质**：垂直排列形态。
- **定义**：为了优化 3D 打印效率，将多个 Tile 在 Z 轴方向通过微小空气间隙（Air Gap）垂直叠放而成的集合体。
- **关键参数**：`Layer_Height`, `Air_Gap` (通常为 $0.2\text{mm} \sim 0.25\text{mm}$)。

### **Plate (打印盘/任务)**

- **本质**：物理空间极限 / 任务容器。
- **定义**：3D 打印机（如 Bambu Lab X1C/P1S）单次运行所涵盖的所有模型总和。
- **构成**：一个 Plate 可以包含多个 Stacks、散装的 Tiles 以及其他 Accessories。

---

## 2. 层级与嵌套关系 (Hierarchical Relationships)

为了使 Agent 理解空间逻辑，请遵循以下公式化表达：

### **2.1 空间包含逻辑**

$$Cell \subset Tile \subset Stack \subset Plate$$

- **Cell $\to$ Tile**: **Tile** 是 **Cell** 的阵列容器。
- _描述语_：“一个 $5 \times 5$ 的 Tile 包含了 25 个 Cells。”

- **Tile $\to$ Stack**: **Stack** 是 **Tile** 的垂直克隆序列。
- _描述语_：“这个 Stack 由 4 层相同规格的 Tiles 组成。”

- **Stack/Tile $\to$ Plate**: **Plate** 是所有待打印实体的物理边界。
- _描述语_：“在当前 Plate 上，我布置了 2 个 Stacks 和 1 组配套的 Snaps。”

### **2.2 跨体系兼容逻辑 (Grid-to-Grid)**

- **OpenGrid ($28\text{mm}$)** 与 **Gridfinity ($42\text{mm}$)** 的公倍数关系：

$$3 \times \text{OpenGrid Cell} = 2 \times \text{Gridfinity Cell} = 84\text{mm}$$

_这是 Agent 在进行跨系统适配器建模时的核心计算依据。_

---

## 3. 生产工作流示例 (Workflow for Agent)

当用户发出指令时，Agent 应按以下逻辑解析词汇：

1. **确定标准 (Grid)**：确认是否使用标准 $28\text{mm}$ 协议。
2. **设计规格 (Cell & Tile)**：用户需要 $X \times Y$ 尺寸的 **Tile**。
3. **计算策略 (Stack)**：基于用户总需求量，计算需要多少层 **Stack** 才能最有效利用打印时间。
4. **排版布局 (Plate)**：在切片软件（如 Bambu Studio）的物理 **Plate** 范围内分配空间。
