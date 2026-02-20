# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

opengrid-drawer-filler (openGrid 抽屉铺满) - 计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。

## 首次安装

首次使用需要运行安装脚本：

```bash
cd {skill_dir}
./scripts/setup.sh
```

脚本安装：
- Python venv 虚拟环境 (`.venv`)
- Python 依赖 (pyyaml, pytest, Pillow)
- OpenSCAD Snapshot (通过 Homebrew)
- QuackWorks 源码 (克隆到 vendor 目录)
- BOSL2 库 (OpenSCAD 依赖)

## 配置文件

首次使用需要配置 `config.yaml`：

```bash
# 复制模板
cp config.example.yaml config.yaml

# 编辑配置
# - STL 输出目录
# - 打印机型号 (Bambu 机型预设)
# - openGrid 参数
```

### 打印机预设

| 型号 | bed_x | bed_y | max_z |
|------|-------|-------|-------|
| a1_mini | 120 | 120 | 120 |
| a1 | 180 | 180 | 180 |
| p1p | 256 | 256 | 256 |
| p1s | 256 | 256 | 256 |
| x1c | 256 | 256 | 256 |
| x1e | 256 | 256 | 256 |
| h2d | 300 | 300 | 300 |

## 常用命令

**注意**: 所有 Python 命令都应使用项目 venv (`.venv/bin/python`) 执行。

```bash
# 运行所有测试
.venv/bin/python -m pytest

# 运行特定测试文件
.venv/bin/python -m pytest tests/test_scheme.py

# 运行特定测试
.venv/bin/python -m pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed

# 批量计算
.venv/bin/python scripts/split_calc.py -b "265x365:2 325x365:2"

# 单尺寸计算
.venv/bin/python scripts/split_calc.py 485 425

# JSON 输出
.venv/bin/python scripts/split_calc.py 485 425 -j
```

## 核心设计原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不应包含 `input()` 或任何交互式提示
- 脚本只做计算：接收参数，返回结果
- Agent 处理所有用户交互：提问、展示选项、获取决策
- 完整工作流见 `SKILL.md`
- **重要**: Agent 必须在计算方案前确认库存状态（见 SKILL.md Step 3）

## 架构

### 模块划分

```
scripts/
├── core/           # 核心算法
│   ├── constants.py   # 常量定义
│   ├── grid.py        # 网格计算
│   ├── splitter.py    # 分割算法
│   ├── scheme.py      # 方案查找
│   ├── stats.py       # 耗材和时间估算
│   └── cost.py        # 库存成本计算
├── inventory/      # 库存管理
│   ├── inventory.py   # 库存追踪
│   └── matcher.py     # 库存匹配
├── stl/           # STL 生成
│   ├── generator.py   # OpenSCAD 生成
│   └── manager.py     # 文件管理
├── project/       # 项目管理
├── ui/            # 输出展示
│   ├── presenter.py   # 方案格式化
│   ├── visualizer.py  # HTML 可视化
│   └── print_plan.py  # 打印计划
└── config/        # 配置管理
    ├── config.py      # 配置加载
    └── printer.py     # 打印机预设
```

### 核心常量

- `TILE_SIZE = 28` - 网格单元格大小 (mm)
- `MAX_X = 10`, `MAX_Y = 11` - 最大瓦片尺寸
- `FULL_THICKNESS = 7.2` - 单层厚度 (6.8mm + 0.4mm 间隙)
- `MAX_Z = 325` - 打印机 Z 轴限制 (~45 stack)

### 算法优先级

最小化独特尺寸 → 最小化瓦片总数 → 最大化均衡度

## 开发指南

**重要：使用 git worktrees 进行功能开发**

开始功能开发或实施计划前，使用 `using-git-worktrees` skill 创建隔离的 worktree，保持主分支干净。

完成前运行测试：
```bash
.venv/bin/python -m pytest -v
```

## 测试

使用 pytest，测试文件按领域组织：
- `test_scheme.py` - 方案查找算法
- `test_split.py` - 分割算法
- `test_inventory.py` - 库存匹配
- `test_integration.py` - 端到端测试
- `test_batch.py` - 批量计算和合并优化
