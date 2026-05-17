# 把 opengrid.cli.batch 的向后兼容 re-export 钉死。
# batch.py 在 2026-05 被拆为 core/batch_planner + ui/batch_view，外部调用
# 方（split.py、旧测试）仍 `from opengrid.cli.batch import ...` 拿这些符号。
# 一旦哪天有人嫌冗余把 re-export 删了，这个测试会先失败而不是生产代码先炸。


def test_legacy_imports_from_cli_batch():
    from opengrid.cli.batch import (
        batch_mode,
        calculate_single,
        merge_and_optimize,
        calculate_total_prints,
        calculate_batch_cost_with_inventory,
        optimize_batch_global,
        build_batch_data,
        print_batch_plan,
    )
    # 全是 callable，挨个戳一下确保不是 None
    for fn in (
        batch_mode,
        calculate_single,
        merge_and_optimize,
        calculate_total_prints,
        calculate_batch_cost_with_inventory,
        optimize_batch_global,
        build_batch_data,
        print_batch_plan,
    ):
        assert callable(fn), f"{fn} 应是可调用对象"


def test_split_module_reexports_batch_helpers():
    # split.py 顶层有 `from opengrid.cli.batch import (...)`，老代码可能直接
    # 从 split 模块拿这些符号。任何一个丢了都会炸 import time。
    from opengrid.cli.commands import split as split_module

    for name in (
        'calculate_single',
        'merge_and_optimize',
        'calculate_total_prints',
        'calculate_batch_cost_with_inventory',
        'optimize_batch_global',
        'build_batch_data',
        'print_batch_plan',
    ):
        assert hasattr(split_module, name), f"split 模块应该 re-export {name}"
