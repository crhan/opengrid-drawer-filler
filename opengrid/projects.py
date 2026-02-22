"""项目索引管理模块"""

import json
import os
from pathlib import Path
from datetime import datetime

PROJECTS_FILE = Path.home() / ".opengrid" / "projects.json"


def _ensure_projects_dir():
    """确保 ~/.opengrid 目录存在"""
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_projects():
    """加载项目索引"""
    _ensure_projects_dir()
    if not PROJECTS_FILE.exists():
        return {"projects": [], "last_active": None}
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def _save_projects(data):
    """保存项目索引"""
    _ensure_projects_dir()
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_project(name: str, path: str):
    """注册新项目到索引

    Args:
        name: 项目名称
        path: 项目目录路径
    """
    data = _load_projects()

    # 检查是否已存在
    for p in data["projects"]:
        if p["path"] == path:
            p["name"] = name  # 更新名称
            data["last_active"] = path
            _save_projects(data)
            return

    # 新增项目
    data["projects"].append({
        "name": name,
        "path": path,
        "created": datetime.now().isoformat()
    })
    data["last_active"] = path
    _save_projects(data)


def list_projects():
    """列出所有已注册项目

    Returns:
        list: 项目列表
    """
    data = _load_projects()
    return data["projects"]


def get_last_active():
    """获取上次活跃项目路径

    Returns:
        str: 项目路径，如果没有则返回 None
    """
    data = _load_projects()
    return data.get("last_active")


def set_last_active(path: str):
    """设置上次活跃项目

    Args:
        path: 项目目录路径
    """
    data = _load_projects()
    data["last_active"] = path
    _save_projects(data)


def is_project_registered(path: str) -> bool:
    """检查路径是否为已注册项目

    Args:
        path: 目录路径

    Returns:
        bool: 是否已注册
    """
    data = _load_projects()
    return any(p["path"] == path for p in data["projects"])


def switch_project(path: str) -> bool:
    """切换到指定项目

    Args:
        path: 项目目录路径

    Returns:
        bool: 是否切换成功
    """
    if not is_project_registered(path):
        return False
    set_last_active(path)
    return True


def get_current_project():
    """获取当前所在项目（如果已注册）

    Returns:
        dict: 项目信息，如果没有则返回 None
    """
    cwd = os.getcwd()
    data = _load_projects()
    for p in data["projects"]:
        if p["path"] == cwd:
            return p
    return None
