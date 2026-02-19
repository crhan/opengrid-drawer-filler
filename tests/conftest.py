"""pytest 配置和共享导入"""

import pytest
import sys
import os

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

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
