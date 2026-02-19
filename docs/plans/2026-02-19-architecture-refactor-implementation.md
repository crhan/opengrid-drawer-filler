# Architecture Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor scripts/ directory into domain-based modules (core/, config/, inventory/, project/, stl/, ui/)

**Architecture:** Split monolithic split_calc.py into focused modules, reorganize other scripts into domain directories, maintain backward compatibility for CLI入口

**Tech Stack:** Python 3.12+, pytest

---

## Phase 1: Create Directory Structure

### Task 1: Create core/ module directory

**Files:**
- Create: `scripts/core/__init__.py`
- Create: `scripts/core/constants.py`
- Create: `scripts/core/grid.py`
- Create: `scripts/core/splitter.py`
- Create: `scripts/core/scheme.py`
- Create: `scripts/core/cost.py`
- Create: `scripts/core/stats.py`

**Step 1: Create scripts/core/ directory and __init__.py**

```bash
mkdir -p scripts/core
touch scripts/core/__init__.py
```

**Step 2: Create constants.py**

```python
"""Core constants for openGrid calculations"""

# Grid dimensions
TILE_SIZE = 28  # mm per cell
MIN_TILE = 2    # minimum tile size in cells

# Tile thickness by type (mm)
TILE_THICKNESS = {
    "Full": 6.8,
    "Lite": 4.0,
    "Heavy": 13.8
}

# Filament estimates (based on实测数据)
FILAMENT_MAIN_PER_CELL = 1.13     # g/cell/layer
FILAMENT_SUPPORT_PER_CELL = 0.06  # g/cell/layer
PRINT_TIME_PER_CELL = 3.1         # minutes/cell/layer

# Swap penalty for color changes (minutes)
SWAP_PENALTY = 60
```

**Step 3: Create grid.py**

```python
"""Grid dimension calculations"""
from .constants import TILE_SIZE


def get_grid_dimensions(width_mm, depth_mm):
    """Calculate available grid cells for drawer dimensions"""
    x = width_mm // TILE_SIZE
    y = depth_mm // TILE_SIZE
    return x, y


def validate_tile(w, h):
    """Validate if a tile size is within printer limits"""
    from .constants import MIN_TILE
    # These will be set from config later
    MAX_X = 10  # placeholder
    MAX_Y = 11  # placeholder
    return MIN_TILE <= w <= MAX_X and MIN_TILE <= h <= MAX_Y
```

**Step 4: Create splitter.py**

```python
"""Tile splitting algorithms"""
from .constants import MIN_TILE


def split_with_limit(n, parts, max_val):
    """Split number n into parts, each not exceeding max_val"""
    if parts == 1:
        return [[n]] if n <= max_val else []

    results = []

    def recurse(remaining, current):
        if len(current) == parts - 1:
            if MIN_TILE <= remaining <= max_val:
                current.append(remaining)
                results.append(current[:])
                current.pop()
            return

        min_needed = MIN_TILE * (parts - len(current) - 1)
        if remaining < min_needed:
            return

        max_allowed = max_val * (parts - len(current) - 1)
        if remaining > max_allowed + max_val:
            return

        for i in range(MIN_TILE, min(max_val, remaining - min_needed) + 1):
            current.append(i)
            recurse(remaining - i, current)
            current.pop()

    recurse(n, [])
    return results


def calc_balance(splits):
    """Calculate balance ratio (max/min), lower is more balanced"""
    if not splits or min(splits) == 0:
        return 1
    return max(splits) / min(splits)
```

**Step 5: Create scheme.py (placeholder for now)**

```python
"""Scheme generation and evaluation"""
# Will be populated from split_calc.py in Task 3
```

**Step 6: Create cost.py (placeholder)**

```python
"""Cost calculation functions"""
# Will be populated from split_calc.py in Task 3
```

**Step 7: Create stats.py (placeholder)**

```python
"""Statistics and formatting functions"""
# Will be populated from split_calc.py in Task 3
```

**Step 8: Commit**

```bash
git add scripts/core/
git commit -m "refactor: create core/ module structure with constants and basic functions"
```

---

### Task 2: Create config/ module

**Files:**
- Create: `scripts/config/__init__.py`
- Create: `scripts/config/config.py`
- Create: `scripts/config/printer.py`
- Create: `scripts/config/summary.py`
- Create: `scripts/config/init.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p scripts/config
touch scripts/config/__init__.py
```

**Step 2: Copy and adapt printer.py**

```python
"""Printer presets"""

PRINTER_PRESETS = {
    "a1_mini": {"bed_x": 120, "bed_y": 120, "max_z": 120},
    "a1": {"bed_x": 180, "bed_y": 180, "max_z": 180},
    "p1p": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "p1s": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1c": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1e": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "h2d": {"bed_x": 300, "bed_y": 300, "max_z": 300},
}


def get_printer_preset(model: str) -> dict:
    """Get printer configuration by model name"""
    if model == "custom":
        return None
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])
```

**Step 3: Move config.py content**

```bash
# Copy scripts/config.py content to scripts/config/config.py
# Update imports accordingly
```

**Step 4: Move config_summary.py to summary.py**

```bash
# Copy scripts/config_summary.py to scripts/config/summary.py
# Update imports
```

**Step 5: Move init.py**

```bash
# Copy scripts/init.py to scripts/config/init.py
# Update imports
```

**Step 6: Commit**

```bash
git add scripts/config/
git commit -m "refactor: create config/ module"
```

---

### Task 3: Create inventory/ module

**Files:**
- Create: `scripts/inventory/__init__.py`
- Create: `scripts/inventory/inventory.py`
- Create: `scripts/inventory/matcher.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p scripts/inventory
touch scripts/inventory/__init__.py
```

**Step 2: Copy inventory.py content to inventory submodule**

```python
"""Inventory CRUD operations"""
import json
import os
from datetime import datetime

INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')


def _load_data():
    """Load full inventory data with log"""
    if not os.path.exists(INVENTORY_FILE):
        return {"inventory": {}, "log": []}
    with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_data(data):
    """Save full inventory data"""
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_inventory():
    """Return current inventory dict"""
    data = _load_data()
    return data.get("inventory", {})


def add_inventory(items, reason=""):
    """Add items to inventory"""
    inv = load_inventory()
    for key, count in items.items():
        inv[key] = inv.get(key, 0) + count
    _save_data({"inventory": inv, "log": []})
    return inv


# ... other functions
```

**Step 3: Extract matcher.py from inventory.py**

```python
"""Inventory matching algorithm"""


def get_inventory_match(tiles, copies, inv):
    """Calculate inventory match for a scheme"""
    # Extract from existing get_inventory_match in inventory.py
    pass
```

**Step 4: Commit**

```bash
git add scripts/inventory/
git commit -m "refactor: create inventory/ module"
```

---

### Task 4: Create project/ module

**Files:**
- Create: `scripts/project/__init__.py`
- Create: `scripts/project/manager.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p scripts/project
touch scripts/project/__init__.py
```

**Step 2: Copy project_manager.py content**

```bash
# Copy scripts/project_manager.py to scripts/project/manager.py
# Update class name if needed
```

**Step 3: Commit**

```bash
git add scripts/project/
git commit -m "refactor: create project/ module"
```

---

### Task 5: Create stl/ module (without slicer functions)

**Files:**
- Create: `scripts/stl/__init__.py`
- Create: `scripts/stl/generator.py`
- Create: `scripts/stl/manager.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p scripts/stl
touch scripts/stl/__init__.py
```

**Step 2: Create generator.py (OpenSCAD only)**

```python
"""STL generation using OpenSCAD"""
import subprocess
import os

# Constants and generate_stl function from slicer.py
# WITHOUT: slice_with_bambu, slice_with_orca, open_in_slicer


def generate_stl(width, height, stacks, verbose=False, force=False):
    """Generate single STL file"""
    # Implementation from slicer.py
    pass


def generate_all_stls(scheme, copies, verbose=False, force=False):
    """Generate all STL files for a scheme"""
    # Implementation from slicer.py
    pass
```

**Step 3: Create manager.py**

```python
"""STL file management"""
# Move from stl_manager.py
def generate_and_link_stls(scheme, project_path, copies=1, verbose=False, force=False):
    """Generate STL and link to project"""
    pass
```

**Step 4: Commit**

```bash
git add scripts/stl/
git commit -m "refactor: create stl/ module (slicer functions deferred)"
```

---

### Task 6: Create ui/ module

**Files:**
- Create: `scripts/ui/__init__.py`
- Create: `scripts/ui/presenter.py`
- Create: `scripts/ui/visualizer.py`
- Create: `scripts/ui/interactive.py`
- Create: `scripts/ui/print_plan.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p scripts/ui
touch scripts/ui/__init__.py
```

**Step 2: Move scheme_presenter.py to presenter.py**

```bash
# Copy scripts/scheme_presenter.py to scripts/ui/presenter.py
```

**Step 3: Move visualizer.py**

```bash
# Copy scripts/visualizer.py to scripts/ui/visualizer.py
```

**Step 4: Move interactive.py**

```bash
# Copy scripts/interactive.py to scripts/ui/interactive.py
```

**Step 5: Move print_plan.py**

```bash
# Copy scripts/print_plan.py to scripts/ui/print_plan.py
# Update imports to use ui.visualizer
```

**Step 6: Commit**

```bash
git add scripts/ui/
git commit -m "refactor: create ui/ module with presentation layer"
```

---

### Task 7: Simplify CLI entry points

**Files:**
- Modify: `scripts/split_calc.py`
- Modify: `scripts/inventory.py`

**Step 1: Simplify split_calc.py to CLI only**

```python
#!/usr/bin/env python3
"""openGrid 抽屉分割计算器 - CLI入口"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import from new modules
from core.scheme import find_best_scheme, find_all_schemes
from core.grid import get_grid_dimensions
from core.stats import format_time, calculate_filament_and_time
from core.constants import TILE_SIZE, MIN_TILE

# Keep main() function mostly the same but use imports from core/


def main():
    # ... existing implementation, just update imports
    pass


if __name__ == "__main__":
    from config import ensure_initialized
    ensure_initialized()
    main()
```

**Step 2: Update inventory.py CLI**

```python
#!/usr/bin/env python3
"""Inventory CLI - calls inventory/ module"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from inventory.inventory import (
    add_inventory,
    deduct_inventory,
    undo_last,
    load_inventory,
    print_inventory
)

# Keep main() function, just update imports
```

**Step 3: Commit**

```bash
git add scripts/split_calc.py scripts/inventory.py
git commit -m "refactor: simplify CLI entry points to use new modules"
```

---

### Task 8: Move test files to new structure

**Files:**
- Create: `tests/core/`
- Create: `tests/config/`
- Create: `tests/inventory/`
- Create: `tests/project/`
- Create: `tests/stl/`
- Create: `tests/ui/`

**Step 1: Create test directories**

```bash
mkdir -p tests/core tests/config tests/inventory tests/project tests/stl tests/ui
```

**Step 2: Move existing test files**

```bash
# Move tests/test_constants.py -> tests/core/test_constants.py
# Move tests/test_utils.py -> tests/core/test_grid.py
# Move tests/test_split.py -> tests/core/test_splitter.py
# Move tests/test_scheme.py -> tests/core/test_scheme.py
# Move tests/test_inventory.py -> tests/inventory/test_matcher.py
# etc.
```

**Step 3: Update imports in test files**

```python
# Before:
from split_calc import find_best_scheme

# After:
from core.scheme import find_best_scheme
```

**Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: reorganize tests into domain directories"
```

---

### Task 9: Update documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `SKILL.md`

**Step 1: Update CLAUDE.md imports section**

```markdown
## Architecture

### Core Modules

| Module | Responsibility |
|--------|---------------|
| core/ | Pure business logic (split algorithm, cost calculation) |
| config/ | Configuration management |
| inventory/ | Tile inventory |
| project/ | Project management |
| stl/ | STL generation (OpenSCAD) |
| ui/ | Presentation and visualization |

### Import Patterns

```python
# Core algorithm
from core.scheme import find_best_scheme
from core.grid import get_grid_dimensions

# Config
from config import load_config, get_printer_config

# Inventory
from inventory.inventory import load_inventory
from inventory.matcher import get_inventory_match

# STL
from stl.generator import generate_stl

# UI
from ui.presenter import present_schemes
from ui.visualizer import Visualizer
```
```

**Step 2: Remove slicer references from SKILL.md**

**Step 3: Commit**

```bash
git add CLAUDE.md SKILL.md
git commit -m "docs: update documentation for new module structure"
```

---

### Task 10: Final verification

**Step 1: Run all tests**

```bash
pytest -v
```

**Step 2: Test CLI entry points**

```bash
python3 scripts/split_calc.py --help
python3 scripts/split_calc.py 485 425
python3 scripts/inventory.py list
```

**Step 3: Test interactive workflow**

```bash
python3 scripts/ui/interactive.py 485x425
```

**Step 4: Commit final**

```bash
git commit -m "refactor: complete architecture reorganization"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-02-19-architecture-refactor-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
