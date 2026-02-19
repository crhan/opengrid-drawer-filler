# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

opengrid-drawer-filler (openGrid 抽屉铺满) - 计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。

## 首次安装

首次使用需要运行安装脚本：

```bash
cd {skill_dir}
./scripts/setup.sh
```

脚本安装：
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

## Common Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scheme.py

# Run specific test class
pytest tests/test_scheme.py::TestFindBestScheme

# Run specific test
pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed

# Run split calculator (shows help, no interactive input)
python3 scripts/split_calc.py

# Run with specific dimensions
python3 scripts/split_calc.py 485 425

# Batch mode (auto-merge optimization)
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# JSON output
python3 scripts/split_calc.py 485 425 -j

# List available presets
python3 scripts/split_calc.py --list-presets
```

## Core Design Principle

**Agent 负责用户交互，脚本负责计算和生成。**

- Scripts should NOT contain `input()` or any interactive prompts
- Scripts are pure computation: take parameters, return results
- Agent handles all user interaction: ask questions, present options, get decisions
- See `SKILL.md` for the complete Agent workflow

## Architecture

### Core Algorithm (`scripts/split_calc.py`)

**Constants:**
- `TILE_SIZE = 28` - Grid cell size in mm
- `MAX_X = 10`, `MAX_Y = 11` - Maximum tile dimensions in cells
- `MIN_TILE = 2` - Minimum tile size
- `FULL_THICKNESS = 7.2` - Single layer thickness (6.8mm + 0.4mm spacing)
- `MAX_Z = 325` - Printer Z-axis height limit (~45 stacks)

**Key Functions:**
- `get_grid_dimensions(width_mm, depth_mm)` - Calculate available grid cells
- `find_best_scheme(x, y)` - Find optimal split scheme using priority: minimize unique sizes → minimize total tiles → maximize balance
- `find_all_schemes(x, y)` - Generate all valid split schemes for a drawer size
- `split_with_limit(n, parts, max_val)` - Generate valid splits with pruning
- `validate_tile(w, h)` - Validate tile dimensions
- `calculate_single(width, depth, copies)` - Calculate scheme for single drawer
- `merge_and_optimize(results)` - Merge multiple drawer results, optimize shared tiles
- `optimize_batch_global(results)` - Global optimization across all drawers to minimize print count

**Batch Mode:**
- Supports multiple drawer sizes with copies
- Automatically merges shared tile sizes across drawers
- `optimize_batch_global()` considers cross-drawer optimization to reduce total print count

**Rotation Symmetry:**
- Algorithm considers both original and rotated orientations (x,y vs y,x)
- Returns normalized results for better usability

### Slicer Integration (`scripts/slicer.py`)

Currently a skeleton module with constants for OpenSCAD and slicer paths (Bambu Studio, Orca Slicer).

### Output Paths

- STL output: `/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/`
- Sliced output: Same directory + `/sliced/`

## Development Guidelines

**IMPORTANT: Use git worktrees for feature development**

Before starting any feature work or implementation plan, use the `using-git-worktrees` skill to create an isolated worktree. This keeps the main branch clean and allows parallel development.

Run tests before claiming completion:
```bash
pytest -v
```

## Testing

Tests use pytest. Test files are organized by domain:
- `tests/test_constants.py` - Constants validation
- `tests/test_utils.py` - Utility functions (get_max_stacks, get_grid_dimensions)
- `tests/test_validate.py` - Tile validation
- `tests/test_split.py` - Split algorithm
- `tests/test_balance.py` - Balance scoring
- `tests/test_scheme.py` - Scheme finding (find_best_scheme, find_all_schemes)
- `tests/test_stats.py` - Statistics (calculate_filament_and_time, format_time)
- `tests/test_integration.py` - End-to-end tests with real drawer sizes
- `tests/test_batch.py` - Batch calculation and merge optimization
- `tests/test_inventory.py` - Inventory management (if present)

## Project Files

- `SKILL.md` - Skill definition file (used by Claude Code skill system)
- `scripts/split_calc.py` - Core calculation logic (CLI entry point, no interactive input)
- `scripts/slicer.py` - STL generation using OpenSCAD
- `scripts/inventory.py` - Inventory management for tile tracking
- `scripts/3mf_utils.py` - 3MF project file utilities
- `scripts/config.py` - Configuration loading (simplified, no exit on uninitialized)
- `scripts/scheme_generator.py` - Multi-scheme generation
- `scripts/scheme_presenter.py` - Scheme output formatting
- `scripts/project_manager.py` - Project directory management
- `scripts/visualizer.py` - HTML print plan generation
