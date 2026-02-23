"""pytest 配置和共享导入"""

import pytest
import sys
import os
from pathlib import Path

# 添加 scripts 目录到路径
scripts_path = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.insert(0, scripts_path)

# 添加根目录到路径（用于导入 config 和 inventory 模块）
root_path = os.path.join(os.path.dirname(__file__), '..')
if root_path not in sys.path:
    sys.path.insert(0, root_path)


# === Config 隔离机制 ===
# 在导入 split_calc 之前 mock 配置，使用测试值
from opengrid import config as config_module

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
    }

def mock_get_printer_config():
    return _TEST_PRINTER_CONFIG

# 替换配置函数
config_module.load_config = mock_load_config
config_module.get_printer_config = mock_get_printer_config
config_module._config = {}

# 从 opengrid.core 导入核心函数
from opengrid.core import (
    get_max_stacks,
    get_grid_dimensions,
    validate_tile,
    split_with_limit,
    calc_balance,
    calc_scheme_balance,
    find_best_scheme,
    calculate_filament_and_time,
    find_all_schemes,
    TILE_SIZE,
    MAX_X,
    MAX_Y,
    MIN_TILE,
    FULL_THICKNESS,
    MAX_Z,
    recalculate_derived_constants,
)

# 应用测试配置到核心常量
recalculate_derived_constants(
    tile_size=28,
    max_z=325,
    bed_x=280,
    bed_y=308,
    tile_type="Full",
    interface_separation=0.2,
    stacking_method="Ironing"
)

# Override format_time with English-compatible version for tests
def format_time(minutes):
    """Format minutes to human readable string (English format for compatibility)"""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h{mins}m"

# 从 CLI commands 导入批量计算函数
from opengrid.cli.commands.split import (
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    optimize_batch_global,
)
