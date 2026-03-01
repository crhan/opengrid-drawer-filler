"""TDD tests for GridConfig refactor bugs identified by code review.

Design doc: docs/plans/2026-03-01-grid-config-refactor-design.md

Bugs covered:
  BUG3 - get_grid_dimensions missing tile_size parameter (design §4)
  BUG1 - build_batch_data uses tile_thickness variable not defined in its scope
  BUG2 - build_batch_data and print_batch_plan use FILAMENT_* constants not imported
"""
import io
import pytest
from unittest.mock import patch


# ─────────────────────────────────────────────────────────────────────────────
# BUG3: get_grid_dimensions must accept tile_size parameter
#
# Design §4 requires the signature: get_grid_dimensions(width, depth, tile_size)
# Current implementation hardcodes TILE_SIZE=28, ignoring the GridConfig.tile_size
# field that GridConfig already carries.
# ─────────────────────────────────────────────────────────────────────────────

class TestGetGridDimensionsTileSize:
    """Design §4: get_grid_dimensions must accept tile_size parameter."""

    def test_accepts_tile_size_keyword_argument(self):
        """Calling with tile_size= must not raise TypeError."""
        from opengrid.core.grid import get_grid_dimensions
        x, y = get_grid_dimensions(280, 308, tile_size=28)
        assert x == 10  # 280 // 28
        assert y == 11  # 308 // 28

    def test_custom_tile_size_changes_result(self):
        """When tile_size differs from 28, results must differ from hardcoded default."""
        from opengrid.core.grid import get_grid_dimensions
        x, y = get_grid_dimensions(280, 308, tile_size=56)
        assert x == 5   # 280 // 56 = 5, not 10
        assert y == 5   # 308 // 56 = 5, not 11


# ─────────────────────────────────────────────────────────────────────────────
# BUG1 + BUG2: build_batch_data crashes when to_print > max_stacks
#
# When a tile size requires more prints than max_stacks (triggered for large
# tile counts), the function references:
#   - tile_thickness  → NameError (never defined in build_batch_data scope)
#   - FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL, PRINT_TIME_PER_CELL
#                     → NameError (not imported in split.py)
#
# max_stacks for test config = int(325 // 7.2) = 45
# We use to_print=100 to ensure: num_prints=3, remainder=1 → both bugs trigger.
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildBatchDataLargeTileCount:
    """build_batch_data must not crash when to_print > max_stacks."""

    @pytest.fixture
    def printer(self):
        """Test PrinterConfig: max_stacks = int(325 // 7.2) = 45."""
        from opengrid.core.split_result import PrinterConfig
        return PrinterConfig(
            max_z=325,
            bed_x=280,
            bed_y=308,
            tile_thickness=7.2,
            max_cells_x=10,
            max_cells_y=11,
        )

    @pytest.fixture
    def merged_tiles_exceeding_max_stacks(self):
        """100 stacks of one tile size: to_print=100 > max_stacks=45.

        With to_print=100 and max_stacks=45:
          num_prints = ceil(100/45) = 3
          stacks_per_print = 100 // 3 = 33
          remainder = 100 % 3 = 1   (> 0, triggers FILAMENT_* path)
        """
        return {
            (5, 5): {
                "total": 100,
                "by_drawer": [
                    {
                        "size": "280×308",
                        "name": "280×308",
                        "copies": 1,
                        "tiles_per_copy": 100,
                        "total": 100,
                        "index": 0,
                    }
                ],
            }
        }

    def test_does_not_raise_name_error(self, printer, merged_tiles_exceeding_max_stacks):
        """build_batch_data must complete without NameError."""
        from opengrid.cli.commands.split import build_batch_data
        result = build_batch_data(
            batch_results=[],
            merged_tiles=merged_tiles_exceeding_max_stacks,
            inventory=None,
            drawer_names={},
            printer_config=printer,
        )
        assert result is not None

    def test_stats_reflect_multiple_prints(self, printer, merged_tiles_exceeding_max_stacks):
        """When to_print > max_stacks, stats.total_prints must reflect split runs."""
        from opengrid.cli.commands.split import build_batch_data
        result = build_batch_data(
            batch_results=[],
            merged_tiles=merged_tiles_exceeding_max_stacks,
            inventory=None,
            drawer_names={},
            printer_config=printer,
        )
        # 100 stacks / max_stacks 45 → ceiling = 3 prints
        assert result["stats"]["total_prints"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# BUG2 (print_batch_plan): same FILAMENT_* NameError in human-readable mode
#
# print_batch_plan defines tile_thickness locally (unlike build_batch_data),
# but still references unimported FILAMENT_* constants when remainder > 0.
# ─────────────────────────────────────────────────────────────────────────────

class TestPrintBatchPlanLargeTileCount:
    """print_batch_plan must not crash in human-readable mode when to_print > max_stacks."""

    @pytest.fixture
    def printer(self):
        from opengrid.core.split_result import PrinterConfig
        return PrinterConfig(
            max_z=325,
            bed_x=280,
            bed_y=308,
            tile_thickness=7.2,
            max_cells_x=10,
            max_cells_y=11,
        )

    @pytest.fixture
    def merged_tiles_exceeding_max_stacks(self):
        return {
            (5, 5): {
                "total": 100,
                "by_drawer": [
                    {
                        "size": "280×308",
                        "name": "280×308",
                        "copies": 1,
                        "tiles_per_copy": 100,
                        "total": 100,
                        "index": 0,
                    }
                ],
            }
        }

    def test_does_not_raise_name_error(self, printer, merged_tiles_exceeding_max_stacks):
        """print_batch_plan human-readable mode must complete without NameError."""
        from opengrid.cli.commands.split import print_batch_plan
        captured = io.StringIO()
        with patch("builtins.print", side_effect=lambda *a, **k: captured.write(str(a) + "\n")):
            result = print_batch_plan(
                batch_results=[],
                merged_tiles=merged_tiles_exceeding_max_stacks,
                inventory=None,
                json_output=False,
                drawer_names={},
                printer_config=printer,
            )
        assert result is not None
        assert result["total_prints"] == 3
