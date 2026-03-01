import pytest
from opengrid.core.cost_v2 import Tile, Stack, Plate, PlateCost, CostResult

def test_tile_model():
    tile = Tile(w=6, h=8, copies=3)
    assert tile.w == 6
    assert tile.h == 8
    assert tile.copies == 3
