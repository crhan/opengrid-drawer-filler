"""项目索引管理模块测试"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from opengrid import projects


@pytest.fixture
def temp_projects_file():
    """创建临时项目文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_file = Path(tmpdir) / "projects.json"
        with patch.object(projects, "PROJECTS_FILE", projects_file):
            yield projects_file


@pytest.fixture
def empty_projects(temp_projects_file):
    """空项目索引"""
    data = {"projects": [], "last_active": None}
    with open(temp_projects_file, "w") as f:
        json.dump(data, f)
    return temp_projects_file


@pytest.fixture
def sample_projects(temp_projects_file):
    """示例项目索引"""
    data = {
        "projects": [
            {
                "name": "project1",
                "path": "/path/to/project1",
                "created": "2024-01-01T00:00:00"
            },
            {
                "name": "project2",
                "path": "/path/to/project2",
                "created": "2024-01-02T00:00:00"
            }
        ],
        "last_active": "/path/to/project1"
    }
    with open(temp_projects_file, "w") as f:
        json.dump(data, f)
    return temp_projects_file


class TestRegisterProject:
    """注册项目测试"""

    def test_register_new_project(self, temp_projects_file):
        """测试注册新项目"""
        projects.register_project("test_project", "/test/path")

        with open(temp_projects_file) as f:
            data = json.load(f)

        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "test_project"
        assert data["projects"][0]["path"] == "/test/path"
        assert data["last_active"] == "/test/path"

    def test_register_existing_project_updates_name(self, sample_projects):
        """测试更新已存在项目的名称"""
        projects.register_project("updated_name", "/path/to/project1")

        with open(sample_projects) as f:
            data = json.load(f)

        assert len(data["projects"]) == 2
        assert data["projects"][0]["name"] == "updated_name"
        assert data["last_active"] == "/path/to/project1"

    def test_register_new_project_sets_last_active(self, sample_projects):
        """测试注册新项目后设置 last_active"""
        projects.register_project("new_project", "/new/path")

        with open(sample_projects) as f:
            data = json.load(f)

        assert len(data["projects"]) == 3
        assert data["last_active"] == "/new/path"


class TestListProjects:
    """列出项目测试"""

    def test_list_empty_projects(self, empty_projects):
        """测试列出空项目列表"""
        result = projects.list_projects()
        assert result == []

    def test_list_existing_projects(self, sample_projects):
        """测试列出已存在的项目"""
        result = projects.list_projects()

        assert len(result) == 2
        assert result[0]["name"] == "project1"
        assert result[1]["name"] == "project2"


class TestGetLastActive:
    """获取上次活跃项目测试"""

    def test_get_last_active_with_value(self, sample_projects):
        """测试获取有值的上次活跃项目"""
        result = projects.get_last_active()
        assert result == "/path/to/project1"

    def test_get_last_active_with_none(self, empty_projects):
        """测试获取无值的上次活跃项目"""
        result = projects.get_last_active()
        assert result is None


class TestSetLastActive:
    """设置上次活跃项目测试"""

    def test_set_last_active(self, sample_projects):
        """测试设置上次活跃项目"""
        projects.set_last_active("/path/to/project2")

        with open(sample_projects) as f:
            data = json.load(f)

        assert data["last_active"] == "/path/to/project2"


class TestIsProjectRegistered:
    """检查项目是否已注册测试"""

    def test_registered_path_returns_true(self, sample_projects):
        """测试已注册路径返回 True"""
        result = projects.is_project_registered("/path/to/project1")
        assert result is True

    def test_unregistered_path_returns_false(self, sample_projects):
        """测试未注册路径返回 False"""
        result = projects.is_project_registered("/nonexistent/path")
        assert result is False


class TestSwitchProject:
    """切换项目测试"""

    def test_switch_to_existing_project(self, sample_projects):
        """测试切换到已存在的项目"""
        result = projects.switch_project("/path/to/project2")
        assert result is True

        with open(sample_projects) as f:
            data = json.load(f)
        assert data["last_active"] == "/path/to/project2"

    def test_switch_to_nonexistent_project(self, sample_projects):
        """测试切换到不存在的项目"""
        result = projects.switch_project("/nonexistent/path")
        assert result is False


class TestGetCurrentProject:
    """获取当前项目测试"""

    def test_get_current_registered_project(self, sample_projects, monkeypatch):
        """测试获取当前已注册的项目"""
        monkeypatch.setattr(os, 'getcwd', lambda: "/path/to/project1")
        result = projects.get_current_project()

        assert result is not None
        assert result["name"] == "project1"
        assert result["path"] == "/path/to/project1"

    def test_get_current_unregistered_project(self, sample_projects, monkeypatch):
        """测试获取未注册的当前项目"""
        monkeypatch.setattr(os, 'getcwd', lambda: "/unregistered/path")
        result = projects.get_current_project()

        assert result is None
