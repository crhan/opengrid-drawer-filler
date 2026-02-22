"""CLI 输出格式化函数"""
import json
from typing import Any


def print_plan(width: int, depth: int, scheme: Any, copies: int = 1):
    """打印人类可读的方案"""
    print(f"抽屉尺寸: {width} x {depth} mm (x{copies})")
    print(f"网格: {scheme.get('grid_w')} x {scheme.get('grid_h')}")
    print("瓦片分割:")
    for tile in scheme.get('tiles', []):
        print(f"  {tile[0]}x{tile[1]}")
    print(f"总打印次数: {scheme.get('prints', 1)}")


def output_json(width: int, depth: int, scheme: Any, copies: int = 1) -> str:
    """输出 JSON 格式"""
    data = {
        'dimensions': {'width': width, 'depth': depth, 'copies': copies},
        'grid': scheme.get('grid'),
        'tiles': scheme.get('tiles', []),
        'prints': scheme.get('prints', 1)
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


__all__ = ['print_plan', 'output_json']
