#!/usr/bin/env python3
"""项目管理模块"""

import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


class ProjectManager:
    def __init__(self, projects_dir):
        self.projects_dir = Path(projects_dir).expanduser()

    def create_project(self, name, drawers):
        """创建项目目录

        Args:
            name: 项目名（如 "厨房抽屉"）
            drawers: [{"width": 485, "depth": 425, "copies": 1}, ...]

        Returns:
            project_path: 项目目录路径
        """
        # 生成日期前缀
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"

        # 创建目录结构
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        # 保存 project.yaml
        self._save_project_config(project_path, name, drawers)

        return project_path

    def _save_project_config(self, path, name, drawers):
        """保存 project.yaml"""
        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "drawers": drawers,
            "status": "pending"
        }
        with open(path / "project.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

    def get_project_path(self, name):
        """获取已存在的项目路径"""
        # 尝试精确匹配
        for p in self.projects_dir.iterdir():
            if p.is_dir() and name in p.name:
                return p
        return None

    def list_projects(self):
        """列出所有项目"""
        projects = []
        for p in self.projects_dir.iterdir():
            if p.is_dir() and (p / "project.yaml").exists():
                projects.append(p)
        return sorted(projects, key=lambda x: x.name, reverse=True)
