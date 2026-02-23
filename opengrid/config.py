"""配置管理模块 - 仅支持项目级配置"""

import copy
import os
import yaml
from pathlib import Path

# 默认配置（仅用于测试/开发）
DEFAULTS = {
    "initialized": False,
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "printer": {"model": "p1p"},
    "opengrid": {
        "tile_type": "Full",
        "stacking_method": "Ironing",
        "interface_separation": 0.2,
        "tile_size": 28
    },
}

# Bambu 机型预设
PRINTER_PRESETS = {
    "a1_mini": {"bed_x": 120, "bed_y": 120, "max_z": 120},
    "a1": {"bed_x": 180, "bed_y": 180, "max_z": 180},
    "p1p": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "p1s": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1c": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1e": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "h2d": {"bed_x": 300, "bed_y": 320, "max_z": 325},
}

_config = {}


def get_config_path():
    """获取配置文件路径（仅项目级）"""
    project_config = Path.cwd() / "opengrid_config.yaml"
    if not project_config.exists():
        raise FileNotFoundError(
            "未找到 opengrid_config.yaml\n"
            "请在项目目录下运行，或先初始化项目（调用 setup skill）"
        )
    return project_config


def load_config():
    """加载项目级配置"""
    global _config

    # 检查缓存
    if "project" in _config:
        return _config["project"]

    config_path = get_config_path()
    config = _load_single_config(config_path)

    _config["project"] = config
    return config


def load_config_or_default():
    """加载配置，如果不存在则返回默认值（用于无项目目录场景）"""
    global _config

    # 检查缓存
    if "project" in _config:
        return _config["project"]

    try:
        config_path = get_config_path()
        config = _load_single_config(config_path)
    except FileNotFoundError:
        # 无配置文件时使用默认值
        config = copy.deepcopy(DEFAULTS)

    _config["project"] = config
    return config


def get_printer_config_or_default():
    """获取打印机配置，如果无配置则返回默认值"""
    try:
        return get_printer_config()
    except FileNotFoundError:
        return PRINTER_PRESETS["p1p"]


def _load_single_config(config_path):
    """加载配置文件"""
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        config = copy.deepcopy(DEFAULTS)
        for section, values in user_config.items():
            if section in config and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values
        return config
    return copy.deepcopy(DEFAULTS)


def get_printer_config():
    """获取打印机配置"""
    config = load_config()
    printer = config.get("printer", {})
    model = printer.get("model", "p1p")
    if model == "custom":
        return printer.get("custom", PRINTER_PRESETS["p1p"])
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])


def reload_config():
    """重新加载配置"""
    global _config
    _config = {}
    return load_config()


def is_initialized():
    """检查是否已初始化"""
    try:
        config_path = get_config_path()
    except FileNotFoundError:
        return False
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("initialized", False)


def ensure_initialized():
    """检查初始化状态"""
    if is_initialized():
        return
    print("\n错误: 项目未初始化")
    print("请编辑 opengrid_config.yaml 设置 initialized: true")
    raise SystemExit(1)
