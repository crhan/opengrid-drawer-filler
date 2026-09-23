"""CLI 工具函数"""
import re
from typing import List, Optional, Tuple
from opengrid.core.constants import PRESETS


def parse_dimensions(
    args: List[str],
    default_copies: int = 1,
    unparsed: Optional[List[str]] = None,
) -> List[Tuple[int, int, int]]:
    """解析抽屉尺寸，argv 列表或整串都行（内部按空白重新切词）

    支持格式:
    - 485x425 / 485×425 -> (485, 425, default_copies)
    - 265x365:2 / 265x365x2 -> (265, 365, 2)
    - 265 365 -> (265, 365, default_copies)（连续两个裸数字）
    - 265 365 2 -> (265, 365, 2)（连续三个裸数字，第三个是份数）
      连续 4 个以上裸数字有歧义（两对？宽深份+半截？），整段算无法识别
    - 混合：225x255:2 325x460 -> 两项

    Args:
        default_copies: 没写份数的项用这个份数（split -c）
        unparsed: 传入列表时，无法识别的词会追加进去，便于 CLI 报警告
    """
    tokens = " ".join(args).split()
    items = []
    bare: List[int] = []

    def flush_bare():
        if len(bare) == 2:
            items.append((bare[0], bare[1], default_copies))
        elif len(bare) == 3:
            items.append((bare[0], bare[1], bare[2]))
        elif bare and unparsed is not None:
            unparsed.append(" ".join(map(str, bare)))
        bare.clear()

    for tok in tokens:
        match = re.fullmatch(r'(\d+)[x×](\d+)(?:[x:](\d+))?', tok)
        if match:
            flush_bare()
            c = int(match.group(3)) if match.group(3) else default_copies
            items.append((int(match.group(1)), int(match.group(2)), c))
        elif tok.isdigit():
            bare.append(int(tok))
        else:
            flush_bare()
            if unparsed is not None:
                unparsed.append(tok)
    flush_bare()
    return items


def parse_batch_input(input_str: str) -> List[Tuple[int, int, int]]:
    """解析批量输入字符串（parse_dimensions 的整串版本）"""
    return parse_dimensions([input_str])


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
