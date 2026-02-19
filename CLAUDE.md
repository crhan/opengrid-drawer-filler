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

## Common Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_split_calc.py

# Run specific test class
pytest tests/test_split_calc.py::TestFindBestScheme

# Run specific test
pytest tests/test_split_calc.py::TestFindBestScheme::test_no_split_needed

# Run split calculator (interactive mode)
python3 scripts/split_calc.py

# Run with specific dimensions
python3 scripts/split_calc.py 485 425

# Batch mode (auto-merge optimization)
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# Generate STL files
python3 scripts/split_calc.py 485 425 -g

# JSON output
python3 scripts/split_calc.py 485 425 -j
```

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
- `split_with_limit(n, parts, max_val)` - Generate valid splits with pruning
- `validate_tile(w, h)` - Validate tile dimensions

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
