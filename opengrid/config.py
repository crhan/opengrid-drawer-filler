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

# 全局变量存储命令行指定的配置文件路径
_cli_config_path = None

# 全局变量存储命令行指定的库存文件路径
_cli_inventory_path = None


def set_cli_inventory_path(path):
    """设置命令行指定的库存文件路径"""
    global _cli_inventory_path
    _cli_inventory_path = path


def get_cli_inventory_path():
    """获取命令行指定的库存文件路径"""
    global _cli_inventory_path
    return _cli_inventory_path


def set_cli_config_path(path):
    """设置命令行指定的配置文件路径"""
    global _cli_config_path
    _cli_config_path = path


def get_cli_config_path():
    """获取命令行指定的配置文件路径"""
    global _cli_config_path
    return _cli_config_path


def get_config_path():
    """获取配置文件路径（支持命令行指定）"""
    # 优先使用命令行指定的路径
    cli_path = get_cli_config_path()
    if cli_path:
        config_path = Path(cli_path)
        if config_path.exists():
            return config_path
        # 如果指定的文件不存在，报错
        raise FileNotFoundError(
            f"指定的配置文件不存在: {cli_path}\n"
            "请检查配置文件路径是否正确"
        )

    # 默认在当前目录查找
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

    # 检查缓存 - 如果有CLI指定的路径，需要重新加载
    if "project" in _config:
        # 如果当前加载的路径与CLI指定的不同，需要重新加载
        cli_path = get_cli_config_path()
        cached_path = _config.get("_config_path")
        if cli_path and cached_path != cli_path:
            # 路径不同，清除缓存重新加载
            _config = {}
        else:
            return _config["project"]

    config_path = get_config_path()
    config = _load_single_config(config_path)

    # 缓存配置路径以便后续比较
    _config["project"] = config
    _config["_config_path"] = str(config_path)
    return config


def load_config_or_default():
    """加载配置，如果不存在则返回默认值（用于无项目目录场景）"""
    global _config

    # 检查缓存 - 如果有CLI指定的路径，需要重新加载
    if "project" in _config:
        cli_path = get_cli_config_path()
        cached_path = _config.get("_config_path")
        if cli_path and cached_path != cli_path:
            _config = {}

    try:
        config_path = get_config_path()
        config = _load_single_config(config_path)
        _config["_config_path"] = str(config_path)
    except FileNotFoundError:
        # 无配置文件时使用默认值
        config = copy.deepcopy(DEFAULTS)
        _config["_config_path"] = None

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
