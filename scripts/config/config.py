"""Configuration management"""
import copy
import os
import yaml
from pathlib import Path
from .printer import PRINTER_PRESETS

# Default configuration
DEFAULTS = {
    "initialized": False,
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "projects_dir": "~/opengrid_projects/",
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

_config = None


def get_config_path():
    """Get config file path"""
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "config.yaml"


def load_config():
    """Load configuration from YAML file or use defaults"""
    global _config
    if _config is not None:
        return _config

    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
            config = copy.deepcopy(DEFAULTS)
            for section, values in user_config.items():
                if section in config and isinstance(config[section], dict):
                    config[section].update(values)
                else:
                    config[section] = values
            _config = config
            return config
        except (yaml.YAMLError, IOError):
            _config = copy.deepcopy(DEFAULTS)
            return _config

    _config = copy.deepcopy(DEFAULTS)
    return _config


def get_printer_config():
    """Get printer configuration"""
    config = load_config()
    printer = config.get("printer", {})
    model = printer.get("model", "p1p")

    if model == "custom":
        return printer.get("custom", PRINTER_PRESETS["p1p"])
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])


def get_projects_dir():
    """Get projects directory"""
    config = load_config()
    return config.get("projects_dir", "~/opengrid_projects/")


def reload_config():
    """Reload configuration, clearing cache"""
    global _config
    _config = None
    return load_config()


def is_initialized():
    """Check if config is initialized"""
    config = load_config()
    return config.get("initialized", False)


def ensure_initialized():
    """Ensure config is initialized, prompt if not"""
    if not is_initialized():
        from .init import main as init_main
        init_main()
