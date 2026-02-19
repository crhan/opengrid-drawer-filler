"""配置管理模块"""

import os
import sys
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


def get_projects_dir():
    """获取项目根目录"""
    config = load_config()
    return Path(config.get("projects_dir", "~/opengrid_projects/")).expanduser()


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
    """检查初始化状态，未初始化则提示并退出"""
    if is_initialized():
        return

    config_path = get_config_path()

    print("\n" + "=" * 50)
    print("openGrid 初始化检查")
    print("=" * 50)
    print()
    print("请先完成以下步骤：")
    print()
    print("1) 运行 setup.sh 安装依赖")
    print("   cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler")
    print("   ./scripts/setup.sh")
    print()

    printers = get_bambu_printers()

    print("2) 复制配置文件")
    print("   cp config.example.yaml config.yaml")
    print()

    example_path = config_path.parent / "config.example.yaml"
    if example_path.exists():
        print("【默认配置】")
        with open(example_path) as f:
            example = yaml.safe_load(f)
            example["initialized"] = True
            example["output"]["stl_dir"] = "~/Documents/opengrid/"
            print(f"   initialized: true")
            print(f"   output.stl_dir: {example['output']['stl_dir']}")

        if printers:
            print()
            print("【检测到的打印机】")
            for i, p in enumerate(printers, 1):
                print(f"   {i}) {p['name']} → {p['model']}")
            print()
            print("在 config.yaml 中设置 printer.model")
        else:
            print()
            print("   printer.model: <选择型号>")
            print("   opengrid.tile_type: Full")
            print("   opengrid.stacking_method: Ironing")

    print()
    print("编辑 config.yaml 完成配置后重新运行。")
    print("=" * 50)
    sys.exit(1)


# 测试
if __name__ == "__main__":
    print(load_config())
    print(get_printer_config())
