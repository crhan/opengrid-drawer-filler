"""CLI 工具函数"""
import re
from typing import List, Tuple
from opengrid.core.constants import PRESETS


def parse_dimensions(args: List[str]) -> List[Tuple[int, int, int]]:
    """解析位置参数为尺寸列表

    支持格式:
    - 485x425 -> (485, 425, 1)
    - 265x365:2 -> (265, 365, 2)
    - 265x365x2 -> (265, 365, 2)
    - 265 365 -> (265, 365, 1)
    - 265 365 2 -> (265, 365, 2)
    """
    items = []
    for arg in args:
        # 支持 "宽x深:份数" 或 "宽x深x份数" 格式
        match = re.match(r'(\d+)[x×](\d+)(?:[x:](\d+))?', arg)
        if match:
            w = int(match.group(1))
            h = int(match.group(2))
            c = int(match.group(3)) if match.group(3) else 1
            items.append((w, h, c))
            continue

        # 空格分隔格式
        parts = arg.split()
        if len(parts) == 2:
            try:
                items.append((int(parts[0]), int(parts[1]), 1))
            except ValueError:
                pass
        elif len(parts) == 3:
            try:
                items.append((int(parts[0]), int(parts[1]), int(parts[2])))
            except ValueError:
                pass

    return items


def parse_batch_input(input_str: str) -> List[Tuple[int, int, int]]:
    """解析批量输入字符串

    支持格式:
    - 265x365:2 325x365:2 (多个尺寸)
    - 265x365x2 (用 x 分隔份数)
    - 265 365 2 (空格分隔)
    """
    items = []

    # 首先尝试解析 "宽x深:份数" 或 "宽x深x份数" 格式
    # 按空格分割
    parts = input_str.strip().split()

    for part in parts:
        # 尝试匹配 "宽x深:份数" 或 "宽x深x份数" 格式
        match = re.match(r'(\d+)[x×](\d+)(?:[x:](\d+))?', part)
        if match:
            width = int(match.group(1))
            depth = int(match.group(2))
            copies = int(match.group(3)) if match.group(3) else 1
            items.append((width, depth, copies))
            continue

    # 如果上面的解析失败，尝试 "宽 深 份数" 格式
    if not items and len(parts) >= 3:
        try:
            width = int(parts[0])
            depth = int(parts[1])
            copies = int(parts[2])
            items.append((width, depth, copies))
        except:
            pass

    return items


def parse_preset(preset_name: str, copies: int = 1):
    """解析预设名称为尺寸

    Args:
        preset_name: 预设名称
        copies: 份数

    Returns:
        [(width, depth, copies), ...] 或 None 如果预设不存在
    """
    if preset_name in PRESETS:
        w, h, _ = PRESETS[preset_name]
        return [(w, h, copies)]
    return None


__all__ = ['parse_dimensions', 'parse_batch_input', 'parse_preset']
