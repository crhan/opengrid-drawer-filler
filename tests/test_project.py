import pytest
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from opengrid.project.manager import ProjectManager


class TestProjectManager:
    def test_create_project_with_stl_files(self):
        """Test creating project with STL files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProjectManager(tmpdir)

            # Mock scheme data
            scheme_data = {
                "scheme": {
                    "x_splits": [7, 3],
                    "y_splits": [5, 5],
                    "tiles": [
                        {"width": 7, "height": 5, "count": 4, "from_inventory": True},
                        {"width": 3, "height": 5, "count": 4, "from_inventory": False},
                    ]
                },
                "stats": {
                    "total_tiles": 8,
                    "total_prints": 4,
                    "total_time": "12.4 分钟",
                    "total_filament": "45.2g"
                },
                "inventory_usage": {"7x5": 4}
            }

            drawer_specs = [{"width": 265, "depth": 365, "copies": 2}]

            # Create temp STL files for testing
            stl_dir = Path(tmpdir) / "stl_temp"
            stl_dir.mkdir()
            stl_file = stl_dir / "test.stl"
            stl_file.write_text("dummy stl")

            project_path = pm.create_print_project(
                name="test-project",
                scheme_data=scheme_data,
                drawer_specs=drawer_specs,
                stl_files=[str(stl_file)]
            )

            # Verify project structure
            assert (project_path / "project.yaml").exists()
            assert (project_path / "print_plan.html").exists()
            assert (project_path / "stl" / "test.stl").exists()

    def test_create_project_with_3mf_template(self):
        """Test creating project with 3MF template"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock 3MF template
            template_3mf = Path(tmpdir) / "test.3mf"
            template_3mf.write_text("dummy 3mf")

            pm = ProjectManager(
                tmpdir,
                template_3mf_path=str(template_3mf)
            )

            scheme_data = {
                "scheme": {
                    "x_splits": [3],
                    "y_splits": [5],
                    "tiles": []
                },
                "stats": {},
                "inventory_usage": {}
            }

            drawer_specs = [{"width": 265, "depth": 365, "copies": 1}]

            # Create temp STL file
            stl_file = Path(tmpdir) / "test.stl"
            stl_file.write_text("dummy stl")

            project_path = pm.create_print_project(
                name="test-3mf",
                scheme_data=scheme_data,
                drawer_specs=drawer_specs,
                stl_files=[str(stl_file)]
            )

            # Verify 3MF template was copied
            assert (project_path / "test.3mf").exists()
