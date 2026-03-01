"""CLI 输出格式化函数"""
import json
from typing import Any
from opengrid.core.constants import FILAMENT_MAIN_PER_CELL, FILAMENT_SUPPORT_PER_CELL, PRINT_TIME_PER_CELL
from opengrid.core.cost import calculate_print_cost


def print_plan(width: int, depth: int, scheme: Any, copies: int = 1):
    """打印人类可读的方案"""
    # 计算网格尺寸
    grid_w = max(scheme.get('x_splits', [])) if scheme.get('x_splits') else 0
    grid_h = max(scheme.get('y_splits', [])) if scheme.get('y_splits') else 0

    print(f"抽屉尺寸: {width} x {depth} mm (x{copies})")
    print(f"网格: {grid_w} x {grid_h}")
    print("瓦片分割:")
    for tile in scheme.get('tiles', []):
        print(f"  {tile[0]}x{tile[1]}")
    print(f"总打印次数: {scheme.get('prints', 1)}")


def output_json(width: int, depth: int, result: Any, copies: int = 1, inventory: dict = None) -> str:
    """输出 JSON 格式

    Args:
        result: SplitResult 实例或向下兼容的 scheme dict
    """
    from opengrid.core.split_result import SplitResult

    # 如果是 SplitResult 实例，直接读取属性
    if isinstance(result, SplitResult):
        tiles_list = [{'width': w, 'height': h} for w, h in result.tiles]
        unique_sizes = result.unique_sizes
        total_tiles = len(result.tiles)
        total_cells = sum(w * h for w, h in result.tiles)

        # 直接从 SplitResult 读取成本信息
        total_time_min = result.cost.total_cost
        filament_main = result.cost.total_filament_g
        from_inventory = result.from_inventory
        need_print = result.need_print

        stats = {
            'unique_sizes': unique_sizes,
            'total_tiles': total_tiles,
            'total_cells': total_cells,
            'total_time_min': total_time_min,
            'filament_main_g': filament_main,
            'filament_support_g': result.cost.total_filament_g * 0.3,  # 估算
        }

        data = {
            'dimensions': {'width': width, 'depth': depth, 'copies': copies},
            'grid': result.grid,
            'tiles': tiles_list,
            'prints': result.cost.plate_count if result.cost.plate_count > 0 else 1,
            'scheme': {
                'tiles': tiles_list,
                'x_parts': len(result.x_splits),
                'y_parts': len(result.y_splits),
                'x_splits': result.x_splits,
                'y_splits': result.y_splits,
            },
            'stats': stats,
            'cost': {
                'total_cost': result.cost.total_cost,
                'total_filament_g': result.cost.total_filament_g,
                'plate_count': result.cost.plate_count,
                'swap_penalty_total': result.cost.swap_penalty_total,
            }
        }

        # 如果有库存信息
        if inventory or from_inventory:
            total_from_inv = sum(from_inventory.values()) if from_inventory else 0
            total_need_print = sum(need_print.values()) if need_print else len(result.tiles) * copies

            data['inventory_usage'] = {
                'from_inventory': from_inventory,
                'need_print': need_print,
                'total_from_inventory': total_from_inv,
                'total_need_print': total_need_print
            }

        return json.dumps(data, indent=2, ensure_ascii=False)

    # 向下兼容旧 dict 格式
    scheme = result

    # 转换 tiles 格式
    tiles = scheme.get('tiles', [])
    tiles_list = []
    for t in tiles:
        if isinstance(t, tuple):
            tiles_list.append({'width': t[0], 'height': t[1]})
        elif isinstance(t, dict):
            tiles_list.append(t)
        else:
            tiles_list.append({'width': t[0], 'height': t[1]})

    # 计算统计信息
    unique_sizes = len(set((t['width'], t['height']) for t in tiles_list))
    total_tiles = len(tiles_list)
    total_cells = sum(t['width'] * t['height'] for t in tiles_list)

    # 计算打印时间和耗材
    # 使用 calculate_print_cost 获取实际需要打印的瓦片时间（考虑库存）
    cost, from_inventory, need_print = calculate_print_cost(tiles, inventory, copies)

    # need_print 是字典 {"3x6": 2, "6x6": 1}，需要转换为瓦片列表来计算
    need_print_cells = 0
    if need_print:
        for key, count in need_print.items():
            w, h = map(int, key.split('x'))
            need_print_cells += w * h * count
    else:
        need_print_cells = total_cells

    total_time_min = need_print_cells * PRINT_TIME_PER_CELL * copies
    filament_main = need_print_cells * FILAMENT_MAIN_PER_CELL * copies
    filament_support = need_print_cells * FILAMENT_SUPPORT_PER_CELL * copies

    stats = {
        'unique_sizes': unique_sizes,
        'total_tiles': total_tiles,
        'total_cells': total_cells,
        'total_time_min': total_time_min,
        'filament_main_g': filament_main,
        'filament_support_g': filament_support,
    }

    # 基本数据
    data = {
        'dimensions': {'width': width, 'depth': depth, 'copies': copies},
        'grid': scheme.get('grid'),
        'tiles': tiles_list,
        'prints': scheme.get('prints', 1),
        'scheme': {
            'tiles': tiles_list,
            'x_parts': scheme.get('x_parts'),
            'y_parts': scheme.get('y_parts'),
            'x_splits': scheme.get('x_splits'),
            'y_splits': scheme.get('y_splits'),
        },
        'stats': stats,
    }

    # 如果有库存信息，添加库存使用情况
    if inventory:
        # 使用 calculate_print_cost 返回的结果
        # 计算使用的库存数量
        total_from_inv = sum(from_inventory.values()) if from_inventory else 0
        total_need_print = sum(need_print.values()) if need_print else len(tiles) * copies

        data['inventory_usage'] = {
            'from_inventory': from_inventory,
            'need_print': need_print,
            'total_from_inventory': total_from_inv,
            'total_need_print': total_need_print
        }

    return json.dumps(data, indent=2, ensure_ascii=False)


__all__ = ['print_plan', 'output_json']
