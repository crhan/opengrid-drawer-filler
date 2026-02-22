"""CLI 工具函数"""
import re
from typing import List, Tuple


def parse_dimensions(args: List[str]) -> List[Tuple[int, int, int]]:
    """解析位置参数为尺寸列表

    支持格式:
    - 485x425 -> (485, 425, 1)
    - 265x365:2 -> (265, 365, 2)
    - 265 365 -> (265, 365, 1)
    - 265 365 2 -> (265, 365, 2)
    """
    items = []
    for arg in args:
        # 支持 x 或 × 符号
        match = re.match(r'(\d+)[x×](\d+)(?::(\d+))?', arg)
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
    """解析批量输入字符串"""
    return parse_dimensions(input_str.split())


__all__ = ['parse_dimensions', 'parse_batch_input']
