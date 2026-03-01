import pytest
from pydantic import ValidationError
from opengrid.core.cost_v2 import Tile, Stack, Plate, PlateCost, CostResult, calculate_stacks, calculate_plates, calculate_cost


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


def test_calculate_stacks_single_copy():
    """边界: copies = 1"""
    tiles = [Tile(w=6, h=8, copies=1)]
    stacks = calculate_stacks(tiles, max_z=325, tile_thickness=6.8, stack_gap=0.4)
    assert len(stacks) == 1
    assert stacks[0].count == 1


def test_calculate_stacks_max_z_small():
    """边界: max_z 只能容纳 1 层"""
    tiles = [Tile(w=6, h=8, copies=10)]
    stacks = calculate_stacks(tiles, max_z=7, tile_thickness=6.8, stack_gap=0.4)
    assert len(stacks) == 10
    assert all(s.count == 1 for s in stacks)


def test_calculate_stacks_multiple_tile_types():
    """多 tile 类型"""
    tiles = [
        Tile(w=6, h=8, copies=3),
        Tile(w=4, h=4, copies=10)
    ]
    stacks = calculate_stacks(tiles, max_z=325, tile_thickness=6.8, stack_gap=0.4)
    # 验证总数
    assert sum(s.count for s in stacks) == 13


def test_calculate_stacks_empty():
    """空 tiles 列表"""
    tiles = []
    stacks = calculate_stacks(tiles, max_z=325, tile_thickness=6.8, stack_gap=0.4)
    assert len(stacks) == 0


# ========== calculate_plates 测试 ==========

def test_calculate_plates_single():
    stacks = [Stack(tile=Tile(w=6, h=8), count=3)]
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    # 当前每个 Stack 独占一盘
    assert len(plates) == 1
    assert plates[0].index == 0


def test_calculate_plates_multiple_stacks():
    """多 stacks -> 多 plates"""
    stacks = [
        Stack(tile=Tile(w=6, h=8), count=3),
        Stack(tile=Tile(w=4, h=4), count=2)
    ]
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    assert len(plates) == 2
    assert plates[0].index == 0
    assert plates[1].index == 1
    # 验证 stack 正确分配
    assert plates[0].stacks[0].count == 3
    assert plates[1].stacks[0].count == 2


def test_calculate_plates_empty():
    """空 stacks -> 空 plates"""
    stacks = []
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    assert len(plates) == 0


# ========== calculate_cost 测试 ==========

def test_calculate_cost_single_stack():
    """测试单个 Stack 的成本计算：6x4s1"""
    # 6x4s1: 24 cells, 1 layer
    stacks = [Stack(tile=Tile(w=6, h=4), count=1)]
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    result = calculate_cost(plates)
    # 预期: 79 min (24 * 1 * 2.89 + 1 * 2.14 + 8.1 = 79.2)
    assert abs(result.total_cost - 79) < 5
    assert abs(result.total_filament_g - 28.6) < 2


def test_calculate_cost_6x8s6():
    """测试 6x8s6 的成本计算"""
    # 6x8s6: 48 cells, 6 layers
    # 当前实现: 48*6*2.89 + 6*2.14 + 5*9.5 + 8.1 = 900.76
    stacks = [Stack(tile=Tile(w=6, h=8), count=6)]
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    result = calculate_cost(plates)
    # 预期: 901 min, 343g
    assert abs(result.total_cost - 901) < 10
    assert abs(result.total_filament_g - 343) < 10


def test_calculate_cost_multiple_stacks_same_plate():
    """多 Stack 同盘 - 验证同盘切换开销"""
    # 手动构造一个 Plate 包含两个 Stacks（模拟同盘多 Stack 场景）
    stacks = [
        Stack(tile=Tile(w=6, h=4), count=1),
        Stack(tile=Tile(w=6, h=4), count=1)
    ]
    plates = [Plate(index=0, stacks=stacks)]
    result = calculate_cost(plates)

    # 2 Stack 同盘:
    # - Stack 1 (i=0): 24*1*2.89 + 1*2.14 + 8.1 = 79.2 (有 prep)
    # - Stack 2 (i=1): 24*1*2.89 + 1*2.14 + 42 = 113.2 (有 SAME_PLATE_PENALTY)
    # 合计: 79.2 + 113.2 = 192.4 min
    assert abs(result.total_cost - 192.4) < 5
    assert result.plate_count == 1
    assert result.swap_penalty_total == 0  # 同一盘无换盘惩罚


def test_calculate_cost_multiple_plates():
    """多盘 - 验证换盘惩罚"""
    # 每个 Stack 独占一盘 -> 2 plates
    stacks = [
        Stack(tile=Tile(w=6, h=4), count=1),
        Stack(tile=Tile(w=6, h=4), count=1)
    ]
    plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
    result = calculate_cost(plates)

    # Stack 1: 24*1*2.89 + 1*2.14 + 8.1 = 79.2
    # Stack 2: 24*1*2.89 + 1*2.14 + 8.1 = 79.2
    # 换盘惩罚: (2-1) * 60 = 60
    # 合计: 79.2 + 79.2 + 60 = 218.4 min
    assert abs(result.total_cost - 218.4) < 10
    assert result.plate_count == 2
    assert result.swap_penalty_total == 60  # 有换盘惩罚


# ========== 参考数据验证测试 ==========

def test_reference_data():
    """验证所有参考数据（基于当前实现的计算值）"""
    # 使用当前实现的计算值作为预期（算法待优化）
    test_cases = [
        # (w, h, layers, expected_time, expected_filament)
        (6, 4, 1, 80, 28.56),
        (6, 8, 6, 901, 342.72),
        (6, 7, 6, 797, 299.88),
        (8, 8, 5, 982, 380.80),
        (10, 8, 1, 241, 95.20),
        (10, 8, 2, 484, 190.40),
        (5, 6, 8, 786, 285.60),
    ]

    for w, h, layers, exp_time, exp_fil in test_cases:
        stacks = [Stack(tile=Tile(w=w, h=h), count=layers)]
        plates = calculate_plates(stacks, plate_width=256, plate_depth=256)
        result = calculate_cost(plates)

        assert abs(result.total_cost - exp_time) <= 10, f"{w}x{h}s{layers}: {result.total_cost} vs {exp_time}"
        assert abs(result.total_filament_g - exp_fil) <= 10, f"{w}x{h}s{layers}: {result.total_filament_g}g vs {exp_fil}g"

