import pytest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from project_manager import ProjectManager


def test_create_project_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)

        drawers = [{"width": 485, "depth": 425, "copies": 1}]
        path = pm.create_project("测试抽屉", drawers)

        assert path.exists()
        assert (path / "stl").exists()
        assert (path / "project.yaml").exists()
