"""pytest 配置和共享导入"""

import pytest
import sys
import os
import shutil
import tempfile
from pathlib import Path

# 添加 scripts 目录到路径
scripts_path = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, scripts_path)

# 添加根目录到路径（用于导入 config 和 inventory 模块）
root_path = os.path.join(os.path.dirname(__file__), '..')
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# === Inventory 隔离机制 ===
# 在测试开始前备份全局 inventory 到临时文件，测试结束后恢复
import inventory as inventory_module

# 获取全局 inventory 路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(inventory_module.__file__))
_ORIGINAL_INVENTORY_FILE = os.path.join(_SCRIPT_DIR, '..', 'inventory', 'inventory.json')

# 创建测试用临时目录
_test_inventory_dir = tempfile.mkdtemp(prefix="opengrid_test_inventory_")
_test_inventory_file = os.path.join(_test_inventory_dir, "inventory.json")

# 备份全局 inventory（如果存在）
if os.path.exists(_ORIGINAL_INVENTORY_FILE):
    shutil.copy2(_ORIGINAL_INVENTORY_FILE, _test_inventory_file)
else:
    with open(_test_inventory_file, 'w') as f:
        f.write('{"inventory": {}, "log": []}')

# 修改模块常量指向临时文件
inventory_module.INVENTORY_FILE = _test_inventory_file


# === Config 隔离机制 ===
# 在导入 split_calc 之前 mock 配置，使用测试值
import config as config_module

# 测试用的打印机配置（更大的打印床和 Z 轴）
_TEST_PRINTER_CONFIG = {"bed_x": 280, "bed_y": 308, "max_z": 325}

def mock_load_config():
    return {
        "output": {"stl_dir": "~/3D打印/opengrid/"},
        "printer": {"model": "test"},
        "opengrid": {
            "tile_type": "Full",
            "stacking_method": "Ironing",
            "interface_separation": 0.2,
            "tile_size": 28
        },
        "software": {
            "openscad": "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
            "bambustudio": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
            "orca": "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
        }
    }

def mock_get_printer_config():
    return _TEST_PRINTER_CONFIG

# 替换配置函数
config_module.load_config = mock_load_config
config_module.get_printer_config = mock_get_printer_config
config_module._config = None

from split_calc import (
    get_max_stacks,
    get_grid_dimensions,
    validate_tile,
    split_with_limit,
    calc_balance,
    calc_scheme_balance,
    find_best_scheme,
    calculate_single,
    merge_and_optimize,
    calculate_filament_and_time,
    format_time,
    find_all_schemes,
    calculate_total_prints,
    optimize_batch_global,
    TILE_SIZE,
    MAX_X,
    MAX_Y,
    MIN_TILE,
    FULL_THICKNESS,
    MAX_Z,
)
