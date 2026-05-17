"""Tests for opengrid.cli.commands.slicer 的输入校验

覆盖 _parse_slicer_dims 的上限/格式/正整数校验。slicer 子命令的"防御性"
是关键路径的一部分，前评审发现完全没测，本文件补齐。
"""
import pytest

from opengrid.cli.commands import slicer


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
