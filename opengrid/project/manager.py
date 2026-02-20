"""Project management"""
import os
import sys
import shutil
import yaml
from datetime import datetime
from pathlib import Path


class ProjectManager:
    def __init__(self, projects_dir, template_3mf_path=None, skill_dir=None):
        self.projects_dir = Path(projects_dir).expanduser()
        self.template_3mf_path = template_3mf_path
        self.skill_dir = Path(skill_dir) if skill_dir else Path(__file__).parent.parent

    def create_project(self, name, drawers):
        """Create project directory"""
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"

        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        self._save_project_config(project_path, name, drawers)
        return project_path

    def create_print_project(self, name, scheme_data, drawer_specs, stl_files):
        """Create a print project with STL files and HTML plan

        Args:
            name: Project name
            scheme_data: Scheme data dict with keys: scheme, stats, inventory_usage
            drawer_specs: List of drawer specs
            stl_files: List of STL file paths to copy

        Returns:
            Path: Project directory path
        """
        # 1. Create project directory with date prefix
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"
        project_path.mkdir(parents=True, exist_ok=True)

        # 2. Create stl subdirectory
        stl_dir = project_path / "stl"
        stl_dir.mkdir(exist_ok=True)

        # 3. Copy STL files (flattened)
        for stl_path in stl_files:
            src = Path(stl_path)
            if src.exists():
                dst = stl_dir / src.name
                shutil.copy2(src, dst)

        # 4. Copy 3MF template if exists
        if self.template_3mf_path:
            template_src = Path(self.template_3mf_path)
            if template_src.exists():
                shutil.copy2(template_src, project_path / template_src.name)

        # 5. Save project.yaml
        self._save_project_yaml(project_path, name, scheme_data, drawer_specs, stl_files)

        # 6. Generate HTML plan
        self._generate_html_plan(project_path, name, scheme_data, drawer_specs, stl_files)

        return project_path

    def _save_project_config(self, path, name, drawers):
        """Save project.yaml"""
        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "drawers": drawers,
            "status": "pending"
        }
        with open(path / "project.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

    def _save_project_yaml(self, project_path, name, scheme_data, drawer_specs, stl_files):
        """Save project.yaml with full scheme data"""
        tiles = scheme_data.get("scheme", {}).get("tiles", [])

        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "status": "pending",
            "drawers": drawer_specs,
            "scheme": scheme_data.get("scheme", {}),
            "stats": scheme_data.get("stats", {}),
            "inventory_usage": scheme_data.get("inventory_usage", {}),
            "stl_files": [f"stl/{Path(f).name}" for f in stl_files]
        }

        with open(project_path / "project.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def _generate_html_plan(self, project_path, name, scheme_data, drawer_specs, stl_files):
        """Generate HTML print plan"""
        from opengrid.ui.presenter import generate_print_plan_html

        generate_print_plan_html(
            project_path=project_path,
            project_name=name,
            scheme_data=scheme_data,
            drawer_specs=drawer_specs,
            stl_files=stl_files
        )

    def get_project_path(self, name):
        """Get existing project path"""
        for p in self.projects_dir.iterdir():
            if p.is_dir() and name in p.name:
                return p
        return None

    def list_projects(self):
        """List all projects"""
        projects = []
        for p in self.projects_dir.iterdir():
            if p.is_dir() and (p / "project.yaml").exists():
                projects.append(p)
        return sorted(projects, key=lambda x: x.name, reverse=True)
