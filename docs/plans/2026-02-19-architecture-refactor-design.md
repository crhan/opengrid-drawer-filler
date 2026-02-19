# opengrid-drawer-filler 架构重构设计

**Date**: 2026-02-19
**Status**: Approved
**Scope**: 完整重构项目，按领域划分目录结构

## 目标

将 `scripts/` 目录下的 Python 文件按领域进行合理划分，形成清晰的模块边界和依赖关系：
- 核心算法与外部依赖分离
- 各领域职责单一
- 便于维护和测试

## 当前问题

1. `split_calc.py` 过于臃肿（1200+ 行），同时负责核心算法和 CLI 入口
2. slicer 相关代码混在分割算法中
3. 模块边界不清晰，部分功能重叠
4. 缺乏统一的目录结构

## 架构设计

### 最终目录结构

```
scripts/
├── __init__.py
├── core/                      # 核心领域 - 无外部依赖
│   ├── __init__.py
│   ├── constants.py           # 常量定义
│   ├── grid.py               # 网格计算
│   ├── splitter.py            # 分割算法
│   ├── scheme.py             # 方案生成与评估
│   ├── cost.py               # 成本计算
│   └── stats.py              # 耗材/时间估算
│
├── config/                    # 配置领域
│   ├── __init__.py
│   ├── config.py             # 配置加载/验证
│   ├── printer.py            # 打印机预设
│   ├── summary.py            # 配置摘要显示
│   └── init.py               # 初始化交互
│
├── inventory/                 # 库存领域
│   ├── __init__.py
│   ├── inventory.py          # CRUD 操作
│   └── matcher.py            # 库存匹配算法
│
├── project/                  # 项目管理
│   ├── __init__.py
│   └── manager.py            # 项目创建/列表
│
├── stl/                      # STL 生成（暂时移除 slicer 功能）
│   ├── __init__.py
│   ├── generator.py          # OpenSCAD 调用
│   └── manager.py            # 文件管理/链接
│
├── ui/                       # 用户界面
│   ├── __init__.py
│   ├── presenter.py          # 方案展示
│   ├── visualizer.py         # 可视化（PNG/SVG/HTML）
│   ├── interactive.py        # 交互式工作流
│   └── print_plan.py         # 打印计划输出（整合自 print_plan.py）
│
├── split_calc.py             # CLI 入口（调用 core/）
├── inventory.py              # CLI 入口（调用 inventory/）
└── 3mf_utils.py             # 3MF 工具（独立）
```

### 领域职责

#### core/ - 核心算法

无任何外部依赖，仅处理纯业务逻辑：

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| constants.py | 常量定义 | TILE_SIZE, MIN_TILE, TILE_THICKNESS, FILAMENT_MAIN_PER_CELL 等 |
| grid.py | 网格计算 | get_grid_dimensions(), get_max_stacks() |
| splitter.py | 分割算法 | split_with_limit(), calc_balance() |
| scheme.py | 方案生成 | find_best_scheme(), find_all_schemes(), normalize_tiles() |
| cost.py | 成本计算 | calculate_print_cost(), replan_with_inventory() |
| stats.py | 统计计算 | calculate_filament_and_time(), format_time() |

#### config/ - 配置管理

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| config.py | 配置加载 | load_config(), get_printer_config(), is_initialized(), ensure_initialized() |
| printer.py | 打印机预设 | PRINTER_PRESETS, get_printer_preset() |
| summary.py | 配置摘要 | get_config_summary(), format_summary() |
| init.py | 初始化交互 | 主函数式入口 |

#### inventory/ - 库存管理

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| inventory.py | CRUD 操作 | add_inventory(), deduct_inventory(), undo_last(), load_inventory() |
| matcher.py | 库存匹配 | get_inventory_match() |

#### project/ - 项目管理

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| manager.py | 项目管理 | ProjectManager 类 |

#### stl/ - STL 生成

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| generator.py | OpenSCAD 调用 | generate_stl(), generate_all_stls() |
| manager.py | 文件管理 | link_stls_to_project() |

注：slicer 相关功能（slice_with_bambu, slice_with_orca, open_in_slicer）暂时移除，后续研究。

#### ui/ - 用户界面

| 模块 | 职责 | 导出函数 |
|------|------|----------|
| presenter.py | 方案展示 | present_schemes(), format_scheme_for_display() |
| visualizer.py | 可视化 | Visualizer 类（PNG/SVG/HTML 生成） |
| interactive.py | 交互式工作流 | interactive_main() |
| print_plan.py | 打印计划输出 | 主函数式入口（从 print_plan.py 移入） |

### 依赖关系图

```
                    ┌─────────────┐
                    │   config/   │  ← 无依赖（基础）
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌─────────┐       ┌──────────┐      ┌──────────┐
   │  core/  │       │ inventory│      │ project/ │
   └────┬────┘       └────┬─────┘      └────┬─────┘
        │                 │                 │
        └────────┬────────┘                 │
                 │                         │
                 ▼                         ▼
           ┌──────────┐             ┌──────────┐
           │  stl/   │             │   ui/    │
           └────┬─────┘             └────┬─────┘
                │                        │
                └────────┬───────────────┘
                         ▼
                  ┌─────────────┐
                  │ CLI 入口    │
                  │ split_calc │
                  │ inventory  │
                  └─────────────┘
```

## 迁移计划

| 阶段 | 操作 | 变更文件 |
|------|------|----------|
| 1 | 创建目录结构 | 新建 core/, config/, inventory/, project/, stl/, ui/ |
| 2 | 创建 core/ 模块 | 从 split_calc.py 提取并拆分 |
| 3 | 简化 split_calc.py | 仅保留 CLI 入口 |
| 4 | 创建 config/ 模块 | 从现有文件提取 |
| 5 | 创建 inventory/ 模块 | 从现有文件提取 |
| 6 | 创建 project/ 模块 | 从 project_manager.py 提取 |
| 7 | 创建 stl/ 模块 | 从 slicer.py, stl_manager.py 提取（移除 slicer 功能） |
| 8 | 创建 ui/ 模块 | 从相关文件提取，整合 print_plan.py |
| 9 | 移动测试文件 | tests/ → 按领域重新组织 |
| 10 | 更新文档 | CLAUDE.md, SKILL.md |

## 待移除内容

根据用户需求，后续研究 slicer 相关功能：
- `slicer.py` 中的 slice_with_bambu(), slice_with_orca(), open_in_slicer() 函数
- SKILL.md 中的 slicer 相关文档

## 验收标准

1. 所有现有功能保持不变
2. 新目录结构清晰，领域边界明确
3. 原有 CLI 入口（split_calc.py, inventory.py）正常工作
4. 测试通过
5. 文档更新完成
