"""Printer presets"""
import os

PRINTER_PRESETS = {
    "a1_mini": {"bed_x": 120, "bed_y": 120, "max_z": 120},
    "a1": {"bed_x": 180, "bed_y": 180, "max_z": 180},
    "p1p": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "p1s": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1c": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "x1e": {"bed_x": 256, "bed_y": 256, "max_z": 256},
    "h2d": {"bed_x": 300, "bed_y": 320, "max_z": 325},
}

PRINTER_NAMES = {
    "a1_mini": "A1 mini",
    "a1": "A1",
    "p1p": "P1P",
    "p1s": "P1S",
    "x1c": "X1C",
    "x1e": "X1E",
    "h2d": "H2D"
}


def get_printer_preset(model: str) -> dict:
    """Get printer configuration by model name"""
    if model == "custom":
        return None
    return PRINTER_PRESETS.get(model, PRINTER_PRESETS["p1p"])
