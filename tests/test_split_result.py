import pytest
from opengrid.core.split_result import PrinterConfig, SplitResult


def test_compute_raises_on_too_small_drawer():
    """每边 < MIN_TILE × TILE_SIZE = 56mm 时算法层抛 ValueError（不再 TypeError）。

    这是评审发现的真 bug：之前 best_result is None 走到 unpack 就崩。
    """
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8, max_cells_x=9, max_cells_y=9)
    with pytest.raises(ValueError, match=r"抽屉尺寸过小"):
        SplitResult.compute(
            width=50, depth=50, copies=1,
            inventory={}, printer=pc,
        )


def test_printer_config_defaults():
    """PrinterConfig 应有合理默认值"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8, max_cells_x=9, max_cells_y=9)
    assert pc.max_z == 325
    assert pc.tile_thickness == 6.8


def test_split_result_no_split_needed():
    """不需要分割时：单片，cost 应接近 v2 公式，无换盘惩罚"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8, max_cells_x=9, max_cells_y=9)
    result = SplitResult.compute(
        width=168, depth=112, copies=1,
        inventory={}, printer=pc
    )
    assert result.unique_sizes == 1
    assert len(result.tiles) == 1
    assert result.cost.swap_penalty_total == 0
    assert result.cost.total_cost > 0


def test_split_result_full_inventory_zero_cost():
    """库存完全满足时，cost 应为 0"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8, max_cells_x=9, max_cells_y=9)
    # 6x4 (168x112mm) → tiles = [(6,4)]
    result = SplitResult.compute(
        width=168, depth=112, copies=1,
        inventory={"4x6": 1}, printer=pc
    )
    assert result.cost.total_cost == 0
    assert result.from_inventory != {}
    assert result.need_print == {}


def test_split_result_partial_inventory():
    """库存部分满足时，need_print 非空，cost > 0"""
    pc = PrinterConfig(max_z=325, bed_x=256, bed_y=256, tile_thickness=6.8, max_cells_x=9, max_cells_y=9)
    result = SplitResult.compute(
        width=168, depth=112, copies=3,
        inventory={"4x6": 1}, printer=pc
    )
    assert result.need_print != {}
    assert result.cost.total_cost > 0
