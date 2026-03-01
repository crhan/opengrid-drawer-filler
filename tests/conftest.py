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

# 从 opengrid 库导入核心函数
from opengrid.core import (
    get_max_stacks as core_get_max_stacks,
    get_grid_dimensions,
    validate_tile as core_validate_tile,
    normalize_tiles as core_normalize_tiles,
    split_with_limit,
    calc_balance,
    calc_scheme_balance,
    find_best_scheme as core_find_best_scheme,
    calculate_filament_and_time,
    find_all_schemes as core_find_all_schemes,
    TILE_SIZE,
    MIN_TILE,
    TILE_THICKNESS,
    GridConfig,
)

# 测试专用的常量（用于测试断言）
# 这些值对应测试配置 _TEST_PRINTER_CONFIG
MAX_X = 10   # 280 // 28
MAX_Y = 11   # 308 // 28
MAX_Z = 325  # 测试配置中的 max_z
FULL_THICKNESS = 7.2  # TILE_THICKNESS["Full"] + 2 * interface_separation (6.8 + 0.4)

# 创建测试专用的 GridConfig
TEST_GRID_CONFIG = GridConfig(max_cells_x=MAX_X, max_cells_y=MAX_Y)


def validate_tile(w, h, grid_config: GridConfig = None):
    """测试用的 validate_tile 包装函数

    如果没有传入 grid_config，使用测试专用的配置
    """
    if grid_config is None:
        grid_config = TEST_GRID_CONFIG
    return core_validate_tile(w, h, grid_config)


def find_best_scheme(x, y, grid_config: GridConfig = None, verbose=False, inventory=None, copies=1):
    """测试用的 find_best_scheme 包装函数

    如果没有传入 grid_config，使用测试专用的配置
    """
    if grid_config is None:
        grid_config = TEST_GRID_CONFIG
    return core_find_best_scheme(x, y, grid_config, verbose, inventory, copies)


def find_all_schemes(x, y, grid_config: GridConfig = None, max_schemes=2000):
    """测试用的 find_all_schemes 包装函数

    如果没有传入 grid_config，使用测试专用的配置
    """
    if grid_config is None:
        grid_config = TEST_GRID_CONFIG
    return core_find_all_schemes(x, y, grid_config, max_schemes)


def normalize_tiles(tiles, grid_config: GridConfig = None):
    """测试用的 normalize_tiles 包装函数

    如果没有传入 grid_config，使用测试专用的配置
    """
    if grid_config is None:
        grid_config = TEST_GRID_CONFIG
    return core_normalize_tiles(tiles, grid_config)


# 导入 PrinterConfig 用于测试
from opengrid.core.split_result import PrinterConfig

# 创建测试专用的 PrinterConfig
TEST_PRINTER_CONFIG = PrinterConfig(
    max_z=325,
    bed_x=280,
    bed_y=308,
    tile_thickness=7.2,
    max_cells_x=MAX_X,
    max_cells_y=MAX_Y,
)


def get_max_stacks(printer_config: PrinterConfig = None):
    """测试用的 get_max_stacks 包装函数

    如果没有传入 printer_config，使用测试专用的配置
    """
    if printer_config is None:
        printer_config = TEST_PRINTER_CONFIG
    return core_get_max_stacks(printer_config)


from opengrid.cli.commands.split import (
    calculate_single,
    merge_and_optimize,
    calculate_total_prints,
    optimize_batch_global,
)


def format_time(minutes):
    """格式化打印时间 (英文格式，兼容测试)"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h{mins}m"
    return f"{mins}m"
