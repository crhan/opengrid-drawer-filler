import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scheme_presenter import present_schemes


def test_present_schemes_formats_output():
    schemes = {
        "math": {
            "name": "纯数学优化",
            "scheme": {"tiles": [(7, 5), (7, 5), (7, 5), (10, 5), (10, 5), (10, 5)]}
        },
        "inventory": {
            "name": "库存感知",
            "scheme": {"tiles": [(7, 5), (7, 5), (8, 5), (8, 5)]}
        }
    }

    output = present_schemes(schemes, {})
    assert "纯数学优化" in output
    assert "7×5" in output
