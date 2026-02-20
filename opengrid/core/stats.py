"""Statistics and formatting functions"""
from .constants import FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL, PRINT_TIME_PER_CELL


def calculate_filament_and_time(cells, stacks):
    """Calculate filament usage and print time

    Returns: (main_filament_g, support_filament_g, time_minutes)
    """
    main = cells * stacks * FILAMENT_MAIN_PER_CELL
    support = cells * stacks * FILAMENT_SUPPORT_PER_CELL
    time_min = cells * stacks * PRINT_TIME_PER_CELL
    return main, support, time_min


def format_time(minutes):
    """Format minutes to human readable string"""
    if minutes < 60:
        return f"{int(minutes)}分钟"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}小时"
    return f"{hours}小时{mins}分钟"
