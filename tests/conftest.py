"""pytest 配置和共享导入"""

import pytest
import sys
import os

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

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
