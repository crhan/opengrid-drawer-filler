import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from config_summary import get_config_summary, format_summary


def test_get_config_summary_returns_dict():
    result = get_config_summary()
    assert "printer" in result
    assert "inventory" in result
    assert "projects_dir" in result
    # 检查打印机型号是否在已知列表中或包含在列表中
    valid_models = ["A1 mini", "A1", "P1P", "P1S", "X1C", "X1E", "H2D", "TEST"]
    assert result["printer"]["model"] in valid_models


def test_format_summary_prints_info():
    summary = {
        "printer": {"model": "P1P", "bed_x": 256, "bed_y": 256},
        "inventory": {"7x5": 3, "10x5": 2},
        "projects_dir": "/tmp/test_projects"
    }
    output = format_summary(summary)
    assert "P1P" in output
    assert "256×256" in output
    # 检查格式中是否包含库存信息（顺序可能不同）
    assert "7x5" in output
