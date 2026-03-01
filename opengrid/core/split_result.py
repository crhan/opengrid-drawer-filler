"""SplitResult: 封装一次 split 请求的全部上下文和计算结果"""
from dataclasses import dataclass
from typing import Optional

from .cost_v2 import (
    Tile, Stack, Plate, CostResult,
    calculate_stacks, calculate_plates, calculate_cost,
)
from .cost import _match_inventory
from .scheme import find_all_schemes
from .grid import get_grid_dimensions
from .splitter import calc_scheme_balance


# 候选方案精算上限：超过此数量后只用启发式排序
# 初始值 100，性能测试后调整
_SCORE_LIMIT = 100


@dataclass
class PrinterConfig:
    """打印机配置，由入口处从 config 构造，传入 SplitResult.compute"""
    max_z: int            # Z 轴最大高度 (mm)
    bed_x: int            # 打印盘宽度 (mm)
    bed_y: int            # 打印盘深度 (mm)
    tile_thickness: float # 瓦片厚度 (mm)，由 tile_type 决定


class SplitResult:
    """单次 split 请求的完整结果。只读，不重算。"""

    def __init__(
        self,
        width: int,
        depth: int,
        copies: int,
        grid: tuple[int, int],
        tiles: list[tuple[int, int]],
        x_splits: list[int],
        y_splits: list[int],
        unique_sizes: int,
        balance: float,
        from_inventory: dict,
        need_print: dict,
        stacks: list[Stack],
        plates: list[Plate],
        cost: CostResult,
    ):
        # 输入上下文
        self.width = width
        self.depth = depth
        self.copies = copies

        # 分割方案
        self.grid = grid
        self.tiles = tiles
        self.x_splits = x_splits
        self.y_splits = y_splits
        self.unique_sizes = unique_sizes
        self.balance = balance

        # 库存匹配（v1 逻辑保留）
        self.from_inventory = from_inventory
        self.need_print = need_print

        # 打印成本（v2 计算）
        self.stacks = stacks
        self.plates = plates
        self.cost = cost

    @classmethod
    def compute(
        cls,
        width: int,
        depth: int,
        copies: int,
        inventory: Optional[dict],
        printer: PrinterConfig,
    ) -> "SplitResult":
        """
        计算最优分割方案。

        Args:
            width: 抽屉宽度 (mm)
            depth: 抽屉深度 (mm)
            copies: 打印份数
            inventory: 可用库存 {"6x8": 3, ...}，None 等同于 {}
            printer: 打印机配置

        Returns:
            SplitResult 实例，包含最优方案和完整成本信息
        """
        inv = inventory or {}
        grid_x, grid_y = get_grid_dimensions(width, depth)

        # 获取所有候选方案（已按 unique_sizes, tile_count, balance 预排序）
        candidates = find_all_schemes(grid_x, grid_y)

        best_result = None
        best_score = None

        for i, candidate in enumerate(candidates):
            tiles = candidate["tiles"]

            # Step 1: 库存匹配
            from_inv, need_print = _match_inventory(tiles, inv, copies)

            # 剪枝 A: 库存完全满足，成本=0，立即返回
            if not need_print:
                stacks, plates, cost_result = _zero_cost_result()
                return cls._build(
                    width, depth, copies, candidate,
                    from_inv, need_print,
                    stacks, plates, cost_result
                )

            # 剪枝 B: 已有 cost=0 的最优解，跳过
            if best_score is not None and best_score[0] == 0:
                break

            # 剪枝 C: 超过精算上限，使用启发式分数（不调用 v2 pipeline）
            if i >= _SCORE_LIMIT:
                heuristic_score = (
                    float("inf"),
                    len(set(tiles)),
                    len(tiles),
                    calc_scheme_balance(candidate["x_splits"], candidate["y_splits"])
                )
                if best_score is None or heuristic_score < best_score:
                    best_score = heuristic_score
                    best_result = (candidate, from_inv, need_print, None, None, None)
                continue

            # Step 2: v2 cost pipeline
            tiles_v2 = [
                Tile(w=w, h=h, copies=count)
                for key, count in need_print.items()
                for w, h in [map(int, key.split("x"))]
            ]
            stacks = calculate_stacks(tiles_v2, printer.max_z, printer.tile_thickness)
            plates = calculate_plates(stacks, printer.bed_x, printer.bed_y)
            cost_result = calculate_cost(plates)

            score = (
                cost_result.total_cost,
                len(set(tiles)),
                len(tiles),
                calc_scheme_balance(candidate["x_splits"], candidate["y_splits"])
            )

            if best_score is None or score < best_score:
                best_score = score
                best_result = (candidate, from_inv, need_print, stacks, plates, cost_result)

        # 若 best_result 来自启发式（stacks 为 None），补算一次 v2
        candidate, from_inv, need_print, stacks, plates, cost_result = best_result
        if stacks is None:
            tiles_v2 = [
                Tile(w=w, h=h, copies=count)
                for key, count in need_print.items()
                for w, h in [map(int, key.split("x"))]
            ]
            stacks = calculate_stacks(tiles_v2, printer.max_z, printer.tile_thickness)
            plates = calculate_plates(stacks, printer.bed_x, printer.bed_y)
            cost_result = calculate_cost(plates)

        return cls._build(width, depth, copies, candidate, from_inv, need_print, stacks, plates, cost_result)

    @classmethod
    def _build(cls, width, depth, copies, candidate, from_inv, need_print, stacks, plates, cost_result):
        """从候选方案和计算结果构造 SplitResult"""
        tiles = candidate["tiles"]
        return cls(
            width=width,
            depth=depth,
            copies=copies,
            grid=(
                max(candidate["x_splits"]) if candidate["x_splits"] else 0,
                max(candidate["y_splits"]) if candidate["y_splits"] else 0,
            ),
            tiles=tiles,
            x_splits=candidate["x_splits"],
            y_splits=candidate["y_splits"],
            unique_sizes=len(set(tiles)),
            balance=calc_scheme_balance(candidate["x_splits"], candidate["y_splits"]),
            from_inventory=from_inv,
            need_print=need_print,
            stacks=stacks,
            plates=plates,
            cost=cost_result,
        )


def _zero_cost_result() -> tuple[list, list, CostResult]:
    """返回零成本结果（库存完全满足时）"""
    cost = CostResult(
        total_cost=0.0,
        total_filament_g=0.0,
        plate_count=0,
        swap_penalty_total=0,
        plates=[],
    )
    return [], [], cost
