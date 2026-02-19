"""Config summary functions"""
from .config import load_config, get_printer_config


PRINTER_NAMES = {
    "a1_mini": "A1 mini",
    "a1": "A1",
    "p1p": "P1P",
    "p1s": "P1S",
    "x1c": "X1C",
    "x1e": "X1E",
    "h2d": "H2D"
}


def get_config_summary():
    """Get config summary"""
    config = load_config()
    printer_config = get_printer_config()
    model = config.get("printer", {}).get("model", "p1p")
    printer_name = PRINTER_NAMES.get(model, model.upper())

    # Lazy import to avoid circular dependency
    try:
        from ..inventory import load_inventory
        inventory = load_inventory()
    except Exception:
        inventory = {}

    return {
        "printer": {
            "model": printer_name,
            "bed_x": printer_config["bed_x"],
            "bed_y": printer_config["bed_y"],
            "max_z": printer_config["max_z"]
        },
        "inventory": inventory,
        "projects_dir": str(config.get("projects_dir", "~/opengrid_projects/"))
    }


def format_summary(summary):
    """Format config summary for display"""
    p = summary["printer"]
    inv = summary["inventory"]

    if inv:
        inv_parts = [f"{k}: {v} stack" for k, v in sorted(inv.items())]
        inv_str = ", ".join(inv_parts)
    else:
        inv_str = "(空)"

    return f"""
╔══════════════════════════════════════════════════════════╗
║  当前配置                                              ║
╠══════════════════════════════════════════════════════════╣
║  打印机: {p['model']} ({p['bed_x']}×{p['bed_y']}mm)                                ║
║  库存:   {inv_str}                          ║
║  输出:   {summary['projects_dir']}          ║
╚══════════════════════════════════════════════════════════╝
"""
