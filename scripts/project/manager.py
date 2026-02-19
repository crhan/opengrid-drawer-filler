"""Project management"""
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path


class ProjectManager:
    def __init__(self, projects_dir):
        self.projects_dir = Path(projects_dir).expanduser()

    def create_project(self, name, drawers):
        """Create project directory"""
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"

        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        self._save_project_config(project_path, name, drawers)
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
