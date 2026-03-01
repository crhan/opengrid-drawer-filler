import pytest
from pydantic import ValidationError
from opengrid.core.cost_v2 import Tile, Stack, Plate, PlateCost, CostResult, calculate_stacks


def test_tile_model():
    tile = Tile(w=6, h=8, copies=3)
    assert tile.w == 6
    assert tile.h == 8
    assert tile.copies == 3


def test_tile_default_copies():
    """测试 copies 默认值为 1"""
    tile = Tile(w=6, h=8)
    assert tile.copies == 1


def test_tile_validation_w_zero():
    """测试 w=0 时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=0, h=8)


def test_tile_validation_h_zero():
    """测试 h=0 时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=6, h=0)


def test_tile_validation_w_negative():
    """测试 w 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=-1, h=8)


def test_tile_validation_h_negative():
    """测试 h 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=6, h=-1)


def test_tile_validation_copies_zero():
    """测试 copies=0 时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=6, h=8, copies=0)


def test_tile_validation_copies_negative():
    """测试 copies 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Tile(w=6, h=8, copies=-1)


def test_stack_model():
    """测试 Stack 模型"""
    tile = Tile(w=6, h=8)
    stack = Stack(tile=tile, count=5)
    assert stack.count == 5
    assert stack.tile.w == 6
    assert stack.tile.h == 8


def test_stack_default_count():
    """测试 count 默认值（如果有的话）"""
    stack = Stack(tile=Tile(w=6, h=8), count=3)
    assert stack.count == 3


def test_stack_validation_count_zero():
    """测试 count=0 时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Stack(tile=Tile(w=6, h=8), count=0)


def test_stack_validation_count_negative():
    """测试 count 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Stack(tile=Tile(w=6, h=8), count=-1)


def test_plate_model():
    """测试 Plate 模型"""
    stack = Stack(tile=Tile(w=6, h=8), count=3)
    plate = Plate(index=0, stacks=[stack])
    assert plate.index == 0
    assert len(plate.stacks) == 1
    assert plate.stacks[0].tile.w == 6


def test_plate_multiple_stacks():
    """测试 Plate 包含多个 Stacks"""
    stack1 = Stack(tile=Tile(w=6, h=8), count=3)
    stack2 = Stack(tile=Tile(w=4, h=4), count=2)
    plate = Plate(index=1, stacks=[stack1, stack2])
    assert plate.index == 1
    assert len(plate.stacks) == 2


def test_plate_cost_model():
    """测试 PlateCost 模型"""
    stack = Stack(tile=Tile(w=6, h=8), count=3)
    plate_cost = PlateCost(
        index=0,
        stacks=[stack],
        print_time=100.0,
        filament_g=50.0
    )
    assert plate_cost.index == 0
    assert plate_cost.print_time == 100.0
    assert plate_cost.filament_g == 50.0
    assert len(plate_cost.stacks) == 1


def test_plate_cost_multiple_stacks():
    """测试 PlateCost 包含多个 Stacks"""
    stack1 = Stack(tile=Tile(w=6, h=8), count=3)
    stack2 = Stack(tile=Tile(w=4, h=4), count=2)
    plate_cost = PlateCost(
        index=0,
        stacks=[stack1, stack2],
        print_time=200.0,
        filament_g=100.0
    )
    assert len(plate_cost.stacks) == 2
    assert plate_cost.print_time == 200.0
    assert plate_cost.filament_g == 100.0


def test_cost_result_model():
    """测试 CostResult 模型"""
    stack = Stack(tile=Tile(w=6, h=8), count=3)
    plate_cost = PlateCost(
        index=0,
        stacks=[stack],
        print_time=100.0,
        filament_g=50.0
    )
    result = CostResult(
        total_cost=100.0,
        total_filament_g=50.0,
        plate_count=1,
        swap_penalty_total=0,
        plates=[plate_cost]
    )
    assert result.total_cost == 100.0
    assert result.total_filament_g == 50.0
    assert result.plate_count == 1
    assert result.swap_penalty_total == 0
    assert len(result.plates) == 1


def test_cost_result_multiple_plates():
    """测试 CostResult 包含多个 PlateCost"""
    stack1 = Stack(tile=Tile(w=6, h=8), count=3)
    stack2 = Stack(tile=Tile(w=4, h=4), count=2)

    plate_cost1 = PlateCost(
        index=0,
        stacks=[stack1],
        print_time=100.0,
        filament_g=50.0
    )
    plate_cost2 = PlateCost(
        index=1,
        stacks=[stack2],
        print_time=80.0,
        filament_g=40.0
    )

    result = CostResult(
        total_cost=180.0,
        total_filament_g=90.0,
        plate_count=2,
        swap_penalty_total=5,
        plates=[plate_cost1, plate_cost2]
    )
    assert result.plate_count == 2
    assert result.total_cost == 180.0
    assert result.total_filament_g == 90.0
    assert result.swap_penalty_total == 5
    assert len(result.plates) == 2


# ========== 边界验证测试 ==========

def test_plate_validation_index_negative():
    """测试 index 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        Plate(index=-1, stacks=[Stack(tile=Tile(w=6, h=8), count=3)])


def test_plate_validation_index_zero():
    """测试 index=0 应该有效（索引从 0 开始）"""
    plate = Plate(index=0, stacks=[Stack(tile=Tile(w=6, h=8), count=3)])
    assert plate.index == 0


def test_plate_cost_validation_index_negative():
    """测试 PlateCost index 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        PlateCost(
            index=-1,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=100.0,
            filament_g=50.0
        )


def test_plate_cost_validation_print_time_negative():
    """测试 print_time 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        PlateCost(
            index=0,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=-10.0,
            filament_g=50.0
        )


def test_plate_cost_validation_print_time_zero():
    """测试 print_time=0 应该有效"""
    plate_cost = PlateCost(
        index=0,
        stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
        print_time=0.0,
        filament_g=50.0
    )
    assert plate_cost.print_time == 0.0


def test_plate_cost_validation_filament_g_negative():
    """测试 filament_g 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        PlateCost(
            index=0,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=100.0,
            filament_g=-5.0
        )


def test_plate_cost_validation_filament_g_zero():
    """测试 filament_g=0 应该有效"""
    plate_cost = PlateCost(
        index=0,
        stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
        print_time=100.0,
        filament_g=0.0
    )
    assert plate_cost.filament_g == 0.0


def test_cost_result_validation_total_cost_negative():
    """测试 total_cost 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        CostResult(
            total_cost=-10.0,
            total_filament_g=50.0,
            plate_count=1,
            swap_penalty_total=0,
            plates=[PlateCost(
                index=0,
                stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
                print_time=100.0,
                filament_g=50.0
            )]
        )


def test_cost_result_validation_total_cost_zero():
    """测试 total_cost=0 应该有效"""
    result = CostResult(
        total_cost=0.0,
        total_filament_g=50.0,
        plate_count=1,
        swap_penalty_total=0,
        plates=[PlateCost(
            index=0,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=0.0,
            filament_g=50.0
        )]
    )
    assert result.total_cost == 0.0


def test_cost_result_validation_total_filament_g_negative():
    """测试 total_filament_g 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        CostResult(
            total_cost=100.0,
            total_filament_g=-5.0,
            plate_count=1,
            swap_penalty_total=0,
            plates=[PlateCost(
                index=0,
                stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
                print_time=100.0,
                filament_g=50.0
            )]
        )


def test_cost_result_validation_total_filament_g_zero():
    """测试 total_filament_g=0 应该有效"""
    result = CostResult(
        total_cost=100.0,
        total_filament_g=0.0,
        plate_count=1,
        swap_penalty_total=0,
        plates=[PlateCost(
            index=0,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=100.0,
            filament_g=0.0
        )]
    )
    assert result.total_filament_g == 0.0


def test_cost_result_validation_plate_count_negative():
    """测试 plate_count 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        CostResult(
            total_cost=100.0,
            total_filament_g=50.0,
            plate_count=-1,
            swap_penalty_total=0,
            plates=[PlateCost(
                index=0,
                stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
                print_time=100.0,
                filament_g=50.0
            )]
        )


def test_cost_result_validation_plate_count_zero():
    """测试 plate_count=0 应该有效（空盘情况）"""
    result = CostResult(
        total_cost=0.0,
        total_filament_g=0.0,
        plate_count=0,
        swap_penalty_total=0,
        plates=[]
    )
    assert result.plate_count == 0


def test_cost_result_validation_swap_penalty_total_negative():
    """测试 swap_penalty_total 负数时应该抛出验证错误"""
    with pytest.raises(ValidationError):
        CostResult(
            total_cost=100.0,
            total_filament_g=50.0,
            plate_count=1,
            swap_penalty_total=-5,
            plates=[PlateCost(
                index=0,
                stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
                print_time=100.0,
                filament_g=50.0
            )]
        )


def test_cost_result_validation_swap_penalty_total_zero():
    """测试 swap_penalty_total=0 应该有效"""
    result = CostResult(
        total_cost=100.0,
        total_filament_g=50.0,
        plate_count=1,
        swap_penalty_total=0,
        plates=[PlateCost(
            index=0,
            stacks=[Stack(tile=Tile(w=6, h=8), count=3)],
            print_time=100.0,
            filament_g=50.0
        )]
    )
    assert result.swap_penalty_total == 0


# ========== calculate_stacks 测试 ==========

def test_calculate_stacks_single():
    """测试单 Stack 情况：3 copies < max layers -> 1 Stack"""
    tiles = [Tile(w=6, h=8, copies=3)]
    stacks = calculate_stacks(tiles, max_z=325, tile_thickness=6.8, stack_gap=0.4)
    assert len(stacks) == 1
    assert stacks[0].tile.w == 6
    assert stacks[0].tile.h == 8
    assert stacks[0].count == 3


def test_calculate_stacks_multiple():
    """测试多 Stack 情况：50 copies > max layers -> 均匀分成 2 个 Stack"""
    tiles = [Tile(w=6, h=8, copies=50)]
    stacks = calculate_stacks(tiles, max_z=325, tile_thickness=6.8, stack_gap=0.4)
    assert len(stacks) == 2
    assert stacks[0].count == 25
    assert stacks[1].count == 25
