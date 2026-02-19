"""配置管理模块"""

import os
import yaml
from pathlib import Path

# 默认配置
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
    "software": {
        "openscad": "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "bambustudio": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
        "orca": "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
    }
}

# Bambu 机型预设
PRINTER_PRESETS = {
    "a1_mini": {"bed_x": 120, "bed_y": 120, "max_z": 120},
    "a1": {"bed_x": 180, "bed_y": 180, "max_z": 180},
    "p1p": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "p1s": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1c": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1e": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "h2d": {"bed_x": 300, "bed_y": 300, "max_z": 300},
}

_config = None


def get_config_path():
    """获取配置文件路径"""
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "config.yaml"


def load_config():
    """加载配置，优先使用 config.yaml，缺失则使用默认值"""
    global _config
    if _config is not None:
        return _config

    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        # 合并默认配置
        config = DEFAULTS.copy()
        for section, values in user_config.items():
            if section in config and isinstance(config[section], dict):
                config[section].update(values)
            else:
                config[section] = values
        _config = config
        return config
    _config = DEFAULTS.copy()
    return _config


def get_printer_config():
    """获取打印机配置，处理预设"""
    config = load_config()
    printer = config.get("printer", {})
    model = printer.get("model", "p1p")

    if model == "custom":
        return printer.get("custom", PRINTER_PRESETS["p1p"])
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])


def reload_config():
    """重新加载配置"""
    global _config
    _config = None
    return load_config()


def is_initialized():
    """检查是否已初始化"""
    config_path = get_config_path()
    if not config_path.exists():
        return False
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("initialized", False)


# 测试
if __name__ == "__main__":
    print(load_config())
    print(get_printer_config())
