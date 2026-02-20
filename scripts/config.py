"""配置管理模块"""

import os
import yaml
from pathlib import Path

# 默认配置
DEFAULTS = {
    "initialized": False,
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "projects_dir": "~/opengrid_projects/",  # 新增
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
    "h2d": {"bed_x": 300, "bed_y": 320, "max_z": 325},
}

_config = None


def get_config_path():
    """获取配置文件路径"""
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "config" / "config.yaml"


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


def get_projects_dir():
    """获取项目根目录"""
    config = load_config()
    return Path(config.get("projects_dir", "~/opengrid_projects/")).expanduser()


def get_inventory():
    """获取默认库存（当未指定库存文件时使用）"""
    from scripts.inventory import load_inventory
    return load_inventory()


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


def get_bambu_printers():
    """从 BambuStudio.conf 读取已配置的打印机"""
    import re

    conf_path = Path.home() / "Library/Application Support/BambuStudio/BambuStudio.conf"
    if not conf_path.exists():
        return []

    try:
        with open(conf_path) as f:
            content = f.read()
            match = re.search(r'"user_bed_type_list"\s*:\s*\{([^}]+)\}', content)
            if not match:
                return []

            printers = []
            for line in match.group(1).split('\n'):
                key_match = re.search(r'"([^"]+)"\s*:', line)
                if key_match:
                    name = key_match.group(1)
                    model = None
                    if "A1 mini" in name:
                        model = "a1_mini"
                    elif "H2D" in name:
                        model = "h2d"
                    elif "P1P" in name:
                        model = "p1p"
                    elif "P1S" in name:
                        model = "p1s"
                    elif "X1C" in name:
                        model = "x1c"
                    elif "X1E" in name:
                        model = "x1e"
                    elif "A1" in name:
                        model = "a1"

                    if model:
                        printers.append({"name": name, "model": model})
            return printers
    except Exception:
        return []


def ensure_initialized():
    """检查初始化状态，未初始化则打印简短警告"""
    if is_initialized():
        return

    print("\n警告: openGrid 未初始化")
    print("请运行: cp config.example.yaml config.yaml")
    print("然后编辑 config.yaml 设置 initialized: true 和打印机型号")
    print()


# 测试
if __name__ == "__main__":
    print(load_config())
    print(get_printer_config())
