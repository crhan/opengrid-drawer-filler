# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) and other AI agents (Codex via `AGENTS.md` symlink) when working with code in this repository.

## 项目概述

`opengrid-drawer-filler` 是一个 **clone-and-use** 的个人 3D 打印工具：根据抽屉尺寸计算最优 openGrid 瓦片分割方案，并生成 STL 文件用于 3D 打印。

工作方式：克隆仓库，`uv sync`，在仓库目录里跑 `uv run scripts/opengrid.py ...`。不需要安装为 Claude Code 插件。Skill 通过 `.claude/skills/` 自动加载（Codex 通过 `.codex/skills` 软链接复用）。

## 仓库结构

```
opengrid-drawer-filler/
├── .claude/skills/                     # Claude Code 项目级 skill（自动加载）
│   └── opengrid-drawer-filler/
│       ├── SKILL.md                    # 技能定义（Agent 工作流）
│       └── references/                 # 参考文档（算法、配置、切片器）
├── .codex/skills        → ../.claude/skills   # Codex 复用 skill 的软链接
├── AGENTS.md            → CLAUDE.md           # 给 Codex 的入口（指向本文件）
│
├── opengrid/                           # 核心 Python 库
│   ├── core/                           # 算法（splitter, scheme, cost）
│   ├── cli/                            # CLI 命令实现
│   ├── stl/                            # STL 生成
│   └── ui/                             # 终端/HTML 展示
├── scripts/opengrid.py                 # 统一 CLI 入口（uv run 直接跑）
├── opengrid_config.yaml                # 项目配置（仓库根，已 initialized）
├── inventory.json                      # 库存数据（仓库根，禁止手改）
└── tests/                              # pytest 用例
```

## 开发与使用

### 首次准备

```bash
uv sync              # 装 Python 依赖
```

生成 STL 还要 OpenSCAD + BOSL2 + QuackWorks 子模块——细节走 `/opengrid-drawer-filler-setup` skill，
不要让用户自己摸 BOSL2 装哪、放哪。

### 测试

```bash
uv run pytest                                          # 全量
uv run pytest tests/test_scheme.py                     # 单文件
uv run pytest tests/test_scheme.py::TestX::test_y      # 单测
```

### 常用命令

```bash
# 状态：看打印机配置 + 库存（加 --json 给 Agent 解析）
uv run scripts/opengrid.py status
uv run scripts/opengrid.py status --json

# 算分割
uv run scripts/opengrid.py split 325x460
uv run scripts/opengrid.py split 325x460 -i inventory.json   # 用库存
uv run scripts/opengrid.py split 325x460 --json > scheme.json
# split --json 输出里有 slicer_commands 字段，列出每条要跑的 slicer 命令，Agent 直接 exec 即可

# 方案对比（生成 HTML）
uv run scripts/opengrid.py compare a.json b.json -o cmp.html

# 库存
uv run scripts/opengrid.py inventory list
uv run scripts/opengrid.py inventory list --json
uv run scripts/opengrid.py inventory add 8x8:5 --reason "原因"
uv run scripts/opengrid.py inventory deduct 8x8:2 --reason "原因"
uv run scripts/opengrid.py inventory undo

# 生成 STL（WxHxS：宽 cells x 深 cells x 堆叠层数）
uv run scripts/opengrid.py slicer generate 7x5x2

# 项目目录：把一次设计任务的方案 + STL + 计划文档放在同一个目录里管理
uv run scripts/opengrid.py project list             # 列出已有项目
uv run scripts/opengrid.py project create foo 325x460   # 新建 foo 项目，附带 325x460 抽屉
uv run scripts/opengrid.py project show foo         # 查看某项目详情
```

## 非显而易见的项目规范

### 测试超时
- pytest timeout 设的是 **5秒/测试**（`pyproject.toml`），不是常见的 30+ 秒
- 改算法时如果某测试卡住，5 秒就会被 kill

### 配置系统
- `opengrid_config.yaml` 在**仓库根**，脚本必须在该目录下运行（或用 `-c` 指定绝对路径）
- `opengrid/config.py` 的 `load_config()` 有进程内缓存（全局 `_config`），改完 yaml 要调 `reload_config()` 才能生效

### 库存管理
- **严格禁止直接编辑** `inventory.json`，必须走 `uv run scripts/opengrid.py inventory ...`
- 每次修改要带 `--reason`，自动追加到 `inventory.json` 的 `log` 数组

### 核心常量是全局可变状态
- `opengrid/core/constants.py` 的 `MAX_X` / `MAX_Y` / `TILE_SIZE` 是**模块级全局变量**
- 调 `recalculate_derived_constants()` 会改这些全局，影响所有后续计算
- 注意调用顺序：先 set 配置 → recalculate → 再跑算法

### 尺寸解析
- 支持两种乘号：`x` 和 `×`（U+00D7）等效
- 例：`265x365` == `265×365`

### CLI 入口
- 只有一个入口 `scripts/opengrid.py`，子命令包括 `status / split / compare / inventory / slicer / project`
- `scripts/opengrid.py` 顶部有 PEP 723 内联依赖声明，`uv run` 会自动建临时 env
- 仓库根有 `pyproject.toml`，所以 `uv sync` 后也可以直接 `python scripts/opengrid.py ...`

## 核心设计原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不含 `input()` 或交互式提示
- 脚本只输出结构化数据（文本表 / JSON / HTML），Agent 解析后跟用户交互
- 完整工作流见 [.claude/skills/opengrid-drawer-filler/SKILL.md](.claude/skills/opengrid-drawer-filler/SKILL.md)

## 核心常量

| 常量 | 值 | 含义 |
|------|----|------|
| `TILE_SIZE` | 28 mm | 网格单元格大小 |
| `MAX_X`, `MAX_Y` | 10, 11 | 单块瓦片最大尺寸 |
| `FULL_THICKNESS` | 7.2 mm | 单层厚度 |
| `MAX_Z` | 325 mm | 打印机 Z 轴限制 |

### 算法优先级

最小化独特尺寸 → 最小化瓦片总数 → 最大化均衡度

## 代码分析工具 (contextplus MCP)

本项目配置了 **contextplus** MCP 服务，提供基于语义理解的代码分析能力。

| 工具 | 用途 |
|------|------|
| `semantic_code_search` | 按自然语言意图搜索代码（不仅是精确变量名） |
| `semantic_identifier_search` | 语义搜索函数/类/方法，返回定义行和调用链 |
| `get_file_skeleton` | 获取文件的签名级骨架（不读完整代码体） |
| `get_context_tree` | 项目结构树（含文件头、函数名、行范围） |
| `get_blast_radius` | 修改/删除前查影响范围 |
| `run_static_analysis` | 跑项目原生 linter 查未用变量、死代码、类型错误 |
| `semantic_navigate` | 按聚类浏览代码库 |
| `get_feature_hub` | Obsidian 风格的 wiki 链接导航 |

# OpenGrid 体系与 3D 打印生产术语规范 (v1.0)

## 1. 核心词汇定义 (Core Definitions)

### **Grid (网格标准)**

- **本质**：逻辑协议 / 度量衡。
- **定义**：整个生态系统遵循的几何对齐规则。OpenGrid 标准间距为 **28mm**。
- **作用**：确保不同来源的配件（Hooks, Bins, Snaps）在空间上具有互操作性。

### **Cell (单元格)**

- **本质**：最小空间单位。
- **定义**：Grid 系统中最小的 $1 \times 1$ 区域（$28\text{mm} \times 28\text{mm}$）。
- **作用**：描述附件尺寸（"这个盒子占 $2 \times 3$ Cells"）或定位安装点。

### **Tile (基础面板)**

- **本质**：物理实体对象。
- **定义**：由 $M \times N$ 个 Cells 组成的单块打印成品底板。
- **分类**：Standard Tile, Lite Tile, 或兼容 Gridfinity 的适配 Tile。

### **Stack (生产堆叠)**

- **本质**：垂直排列形态。
- **定义**：多个 Tile 通过微小空气间隙（Air Gap）在 Z 轴方向垂直叠放，以优化 3D 打印效率。
- **关键参数**：`Layer_Height`, `Air_Gap`（通常 $0.2\text{mm} \sim 0.25\text{mm}$）。

### **Plate (打印盘/任务)**

- **本质**：物理空间极限 / 任务容器。
- **定义**：3D 打印机（如 Bambu Lab X1C/P1S）单次运行涵盖的所有模型总和。
- **构成**：可包含多个 Stacks、散装 Tiles 及其他 Accessories。

---

## 2. 层级与嵌套关系 (Hierarchical Relationships)

### **2.1 空间包含逻辑**

$$Cell \subset Tile \subset Stack \subset Plate$$

- **Cell $\to$ Tile**: Tile 是 Cell 的阵列容器。"一个 $5 \times 5$ 的 Tile 包含 25 个 Cells。"
- **Tile $\to$ Stack**: Stack 是 Tile 的垂直克隆序列。"这个 Stack 由 4 层相同规格的 Tiles 组成。"
- **Stack/Tile $\to$ Plate**: Plate 是所有待打印实体的物理边界。

### **2.2 跨体系兼容逻辑 (Grid-to-Grid)**

OpenGrid（$28\text{mm}$）与 Gridfinity（$42\text{mm}$）的公倍数：

$$3 \times \text{OpenGrid Cell} = 2 \times \text{Gridfinity Cell} = 84\text{mm}$$

这是跨系统适配器建模的核心计算依据。

---

## 3. 生产工作流示例 (Workflow for Agent)

1. **确定标准 (Grid)**：确认是否使用标准 $28\text{mm}$ 协议。
2. **设计规格 (Cell & Tile)**：用户需要 $X \times Y$ 尺寸的 Tile。
3. **计算策略 (Stack)**：基于总需求量，算需要多少层 Stack 才能最有效利用打印时间。
4. **排版布局 (Plate)**：在切片软件（如 Bambu Studio）的物理 Plate 范围内分配空间。
