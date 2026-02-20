"""UI module exports"""
from .presenter import present_schemes, format_scheme_for_display
from .visualizer import Visualizer, get_tile_color

try:
    from .interactive import interactive_main
    __all__ = [
        "present_schemes", "format_scheme_for_display",
        "Visualizer", "get_tile_color",
        "interactive_main"
    ]
except ImportError:
    __all__ = [
        "present_schemes", "format_scheme_for_display",
        "Visualizer", "get_tile_color"
    ]
