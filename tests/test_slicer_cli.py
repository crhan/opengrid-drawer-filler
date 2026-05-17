"""Tests for opengrid.cli.commands.slicer 的输入校验

覆盖：
- 纯函数 _parse_dims / _validate_dims（无 sys.exit / 无 stderr，直接断言返回值）
- CLI 包装 _parse_slicer_dims（sys.exit + stderr 行为）
"""
import pytest

from opengrid.cli.commands import slicer
from opengrid.core.split_result import PrinterConfig


# ---------- 纯函数测试 ----------

def test_parse_dims_returns_tuple_on_success():
    assert slicer._parse_dims("7x5x2") == (7, 5, 2)


def test_parse_dims_returns_error_on_wrong_segment_count():
    err = slicer._parse_dims("7x5")
    assert isinstance(err, str)
    assert "WxHxS" in err


def test_parse_dims_returns_error_on_non_integer():
    err = slicer._parse_dims("7x5xfull")
    assert isinstance(err, str)
    assert "整数" in err


def test_parse_dims_returns_error_on_zero_or_negative():
    err = slicer._parse_dims("0x5x2")
    assert isinstance(err, str)
    assert "正整数" in err


def _make_printer(max_x=10, max_y=11, max_z=325, tile_thickness=6.8, bed_x=280, bed_y=308):
    """构造测试用 PrinterConfig，跟实际 opengrid 配置脱钩。"""
    return PrinterConfig(
        max_z=max_z, bed_x=bed_x, bed_y=bed_y, tile_thickness=tile_thickness,
        max_cells_x=max_x, max_cells_y=max_y,
    )


def test_validate_dims_returns_none_for_valid():
    assert slicer._validate_dims(7, 5, 2, _make_printer()) is None


def test_validate_dims_catches_excess_width():
    err = slicer._validate_dims(99, 5, 2, _make_printer(max_x=10))
    assert err is not None
    assert "宽≤10" in err


def test_validate_dims_catches_excess_height():
    err = slicer._validate_dims(5, 99, 2, _make_printer(max_y=11))
    assert err is not None
    assert "深≤11" in err


def test_validate_dims_catches_excess_stacks():
    # max_stacks 由 get_max_stacks(printer) 算出，跟 max_z + tile_thickness 相关。
    # 用 max_z=10, tile_thickness=6.8 → 约 1 层
    err = slicer._validate_dims(5, 5, 99, _make_printer(max_z=10))
    assert err is not None
    assert "堆叠≤" in err


# ---------- CLI 包装测试（sys.exit + stderr 行为）----------


# _parse_slicer_dims 调 sys.exit；用 pytest.raises(SystemExit) 捕获。


def test_parse_slicer_dims_normal(capsys):
    # 测试机 PrinterConfig: bed_x=300, bed_y=320, max_z=325（h2d preset）
    # 实际上限取决于配置，本测试只验证不抛 / 不退出。
    w, h, s = slicer._parse_slicer_dims("7x5x2")
    assert (w, h, s) == (7, 5, 2)


def test_parse_slicer_dims_wrong_segment_count(capsys):
    with pytest.raises(SystemExit) as exc:
        slicer._parse_slicer_dims("7x5")  # 缺 S
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "WxHxS" in err


def test_parse_slicer_dims_non_integer(capsys):
    with pytest.raises(SystemExit):
        slicer._parse_slicer_dims("7x5xfull")
    assert "整数" in capsys.readouterr().err


def test_parse_slicer_dims_zero_or_negative(capsys):
    with pytest.raises(SystemExit):
        slicer._parse_slicer_dims("0x5x2")
    assert "正整数" in capsys.readouterr().err


def test_parse_slicer_dims_exceeds_width(capsys):
    with pytest.raises(SystemExit) as exc:
        slicer._parse_slicer_dims("99x5x2")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "超出当前打印机限制" in err
    assert "宽≤" in err  # 帮助信息含允许范围


def test_parse_slicer_dims_exceeds_height(capsys):
    with pytest.raises(SystemExit):
        slicer._parse_slicer_dims("5x99x2")
    assert "超出当前打印机限制" in capsys.readouterr().err


def test_parse_slicer_dims_exceeds_stacks(capsys):
    with pytest.raises(SystemExit):
        slicer._parse_slicer_dims("5x5x999")
    err = capsys.readouterr().err
    assert "超出当前打印机限制" in err
    assert "堆叠≤" in err
