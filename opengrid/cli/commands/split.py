"""split 子命令实现"""
import json
from opengrid.cli.utils import parse_dimensions
from opengrid.cli.formatters import print_plan, output_json
from opengrid.core import find_best_scheme, find_all_schemes, get_grid_dimensions, get_max_stacks, MIN_TILE
from opengrid.core.constants import (
    FILAMENT_MAIN_PER_CELL,
    FILAMENT_SUPPORT_PER_CELL,
    PRINT_TIME_PER_CELL,
)
from opengrid.core.cost import calculate_print_cost
from opengrid.core.stats import calculate_filament_and_time, format_time
from opengrid.core.split_result import PrinterConfig, SplitResult
from opengrid.core.grid import GridConfig
from opengrid.config import load_config_or_default, get_printer_config_or_default


def _build_printer_config() -> PrinterConfig:
    """从当前配置构造 PrinterConfig"""
    config = load_config_or_default()
    printer = get_printer_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    tile_size = config.get("opengrid", {}).get("tile_size", 28)

    from opengrid.core.constants import TILE_THICKNESS
    thickness = TILE_THICKNESS.get(tile_type, 7.2)

    bed_x = printer.get("bed_x", 256)
    bed_y = printer.get("bed_y", 256)

    return PrinterConfig(
        max_z=printer.get("max_z", 256),
        bed_x=bed_x,
        bed_y=bed_y,
        tile_thickness=thickness,
        max_cells_x=bed_x // tile_size,
        max_cells_y=bed_y // tile_size,
    )


def _build_grid_config() -> GridConfig:
    """从当前配置构造 GridConfig"""
    printer = _build_printer_config()
    return GridConfig(
        max_cells_x=printer.max_cells_x,
        max_cells_y=printer.max_cells_y,
    )


def add_parser(subparsers):
    parser = subparsers.add_parser('split', help='抽屉分割计算')
    parser.add_argument('dimensions', nargs='*', help='尺寸列表')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数')
    parser.add_argument('-j', '--json', action='store_true', help='JSON 输出并保存到文件（默认临时目录）')
    parser.add_argument('--print-json', action='store_true', help='JSON 输出到标准输出（用于管道重定向）')
    parser.add_argument('-o', '--output', help='JSON 输出文件路径（默认临时目录）')
    parser.add_argument('-H', '--html', help='生成 HTML 报告并保存到指定路径')
    parser.add_argument('-P', '--project-dir', help='生成完整项目到指定目录')
    parser.add_argument('-b', '--batch', help='批量输入')
    parser.add_argument('-i', '--inventory', help='库存文件路径')
    parser.set_defaults(func=handle_split)
    return parser


def handle_split(args):
    """处理 split 命令"""
    import tempfile
    from pathlib import Path
    import time

    # 加载库存文件
    inventory = None
    if args.inventory:
        # 显式指定了库存文件路径
        try:
            with open(args.inventory, 'r', encoding='utf-8') as f:
                data = json.load(f)
            inventory = data.get('inventory', {})
        except FileNotFoundError:
            print(f"错误: 库存文件不存在: {args.inventory}")
            return
        except json.JSONDecodeError:
            print(f"错误: 库存文件格式无效: {args.inventory}")
            return
    else:
        # 从配置文件读取库存（如果配置了 inventory_path）
        try:
            from opengrid.config import load_config_or_default, get_config_path
            config = load_config_or_default()
            config_dir = get_config_path().parent
            from opengrid.inventory import get_inventory_path
            inv_path = get_inventory_path(config, config_dir)
            if inv_path.exists():
                with open(inv_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                inventory = data.get('inventory', {})
        except Exception:
            # 配置没有 inventory_path 或文件不存在，跳过
            pass

    # 批处理模式
    if args.batch:
        result = batch_mode(
            args.batch,
            verbose=False,
            inventory=inventory,
            json_output=args.print_json or args.json
        )
        return

    # 解析输入
    dims = parse_dimensions(args.dimensions)

    if not dims:
        print("错误: 请提供尺寸参数")
        return

    width, depth, copies = dims[0]

    # 构造打印机配置
    printer = _build_printer_config()

    # 找最优方案（使用 SplitResult）
    split_result = SplitResult.compute(width, depth, copies, inventory, printer)
    scheme = split_result  # 向下兼容：formatters 读 scheme dict

    # 输出
    if args.print_json:
        # 输出到 stdout（原有行为，用于管道重定向）
        print(output_json(width, depth, split_result, copies, inventory=inventory))
    elif args.json or args.output:
        json_data = output_json(width, depth, split_result, copies, inventory=inventory)

        # 确定输出路径
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # 使用临时目录
            temp_dir = Path(tempfile.gettempdir()) / 'opengrid'
            temp_dir.mkdir(parents=True, exist_ok=True)
            # 生成唯一的文件名
            timestamp = int(time.time() * 1000)
            output_path = temp_dir / f'scheme_{timestamp}.json'

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_data)

        print(f"方案已保存: {output_path}")
    elif args.html:
        from opengrid.ui.visualizer import Visualizer
        v = Visualizer()
        # 转换格式以匹配 generate_html
        plan_data = {
            'scheme': scheme,
            'drawer': {'width': width, 'depth': depth},
            'stats': {
                'total_tiles': len(scheme.get('tiles', [])),
                'unique_sizes': len(set(scheme.get('tiles', []))),
                'total_prints': 1
            }
        }
        v.generate_html(plan_data, args.html)
        print(f"已生成 HTML 报告: {args.html}")
    elif args.project_dir:
        from opengrid.ui.presenter import generate_print_plan_html
        project_path = Path(args.project_dir)
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        # 转换格式以匹配 generate_print_plan_html
        scheme_data = {
            'scheme': scheme,
            'stats': {
                'total_time': f"{int(width*depth*0.001)} min", # 粗略估算用于演示
                'total_filament': f"{int(width*depth*0.0004)}g"
            },
            'inventory_usage': {
                'from_inventory': scheme.get('from_inventory', {}),
                'need_print': scheme.get('need_print', {})
            }
        }
        drawer_specs = [{'width': width, 'depth': depth, 'copies': copies}]

        generate_print_plan_html(
            project_path=project_path,
            project_name=project_path.name,
            scheme_data=scheme_data,
            drawer_specs=drawer_specs,
            stl_files=[] # 演示时为空
        )
        print(f"已生成项目计划: {project_path}/print_plan.html")
    else:
        print_plan(width, depth, scheme, copies, inventory)


__all__ = ['add_parser']
def calculate_single(width, depth, copies=1, verbose=False, index=None, grid_config: GridConfig = None):
    """计算单个尺寸的分割方案

    Args:
        width: 抽屉宽度 (mm)
        depth: 抽屉深度 (mm)
        copies: 打印份数
        verbose: 是否详细输出
        index: 索引
        grid_config: GridConfig 实例，如果为 None 则使用默认配置
    """
    if grid_config is None:
        grid_config = _build_grid_config()

    x, y = get_grid_dimensions(width, depth)

    if x < MIN_TILE or y < MIN_TILE:
        return None

    # 不再检查 MAX_X/MAX_Y，因为 split 会把大网格拆分成小瓦片

    scheme = find_best_scheme(x, y, grid_config, verbose)

    if not scheme:
        return None

    return {
        'width': width,
        'depth': depth,
        'copies': copies,
        'grid': (x, y),
        'scheme': scheme,
        'index': index  # 用于映射到抽屉名称
    }


def merge_and_optimize(batch_results, drawer_names=None, printer_config: PrinterConfig = None):
    """合并多个尺寸的方案，优化共用尺寸

    策略:
    1. 收集所有需要的瓦片尺寸
    2. 统计每个尺寸的总需求数量
    3. 输出合并后的打印计划

    Args:
        batch_results: 批量计算结果列表
        drawer_names: 可选的抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    if drawer_names is None:
        drawer_names = {}

    # 收集所有瓦片尺寸及其需求
    all_tiles = {}  # {(w, h): {drawer: count, total: total_count}}

    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']
        idx = result.get('index')

        # 统计该尺寸的瓦片
        tile_counts = {}
        for w, h in scheme['tiles']:
            key = (w, h)
            tile_counts[key] = tile_counts.get(key, 0) + 1

        # 乘以份数
        for (w, h), count in tile_counts.items():
            if (w, h) not in all_tiles:
                all_tiles[(w, h)] = {'total': 0, 'by_drawer': []}

            total_for_drawer = count * copies
            all_tiles[(w, h)]['total'] += total_for_drawer

            # 获取抽屉名称
            drawer_name = drawer_names.get(idx, f"{width}×{depth}") if idx is not None else f"{width}×{depth}"

            all_tiles[(w, h)]['by_drawer'].append({
                'size': f"{width}×{depth}",
                'name': drawer_name,
                'copies': copies,
                'tiles_per_copy': count,
                'total': total_for_drawer,
                'index': idx
            })

    return all_tiles


def calculate_total_prints(batch_results, schemes, printer_config: PrinterConfig = None):
    """计算给定方案组合的总打印次数

    Args:
        batch_results: 批量计算结果列表，每个元素包含 width, depth, copies, scheme
        schemes: 对应的分割方案列表
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        (total_prints, details): 总打印次数和每个尺寸的详细信息
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    # 合并所有瓦片
    all_tiles = {}
    for result, scheme in zip(batch_results, schemes):
        if result is None or scheme is None:
            continue
        copies = result['copies']
        for w, h in scheme['tiles']:
            key = (w, h)
            if key not in all_tiles:
                all_tiles[key] = 0
            all_tiles[key] += copies

    # 计算每个尺寸的打印次数
    max_stacks = get_max_stacks(printer_config)
    total_prints = 0
    details = {}

    for (w, h), stacks in all_tiles.items():
        prints_needed = (stacks + max_stacks - 1) // max_stacks
        total_prints += prints_needed
        details[(w, h)] = {
            'stacks': stacks,
            'print_count': prints_needed
        }

    return total_prints, details


def calculate_batch_cost_with_inventory(schemes, batch_results, inventory):
    """计算批量方案的总成本，正确追踪库存使用

    正确的逻辑：按节省成本排序，优先给节省多的抽屉分配库存

    Args:
        schemes: 分割方案列表
        batch_results: 批量计算结果列表
        inventory: 库存字典 {"6x7": 3, ...}

    Returns:
        (total_cost, inventory_usage): 总成本和每个抽屉的库存使用情况
    """
    if not inventory:
        return sum(
            calculate_print_cost(s['tiles'], {}, batch_results[i].get('copies', 1))[0]
            for i, s in enumerate(schemes) if s
        ), {}

    # 第一步：计算每个抽屉不使用库存和使用库存的成本差异
    # 按节省成本从高到低排序
    savings = []
    for i, scheme in enumerate(schemes):
        if scheme is None:
            continue

        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        # 不使用库存的成本
        cost_no_inv, _, _ = calculate_print_cost(scheme['tiles'], {}, copies)
        # 使用库存的成本
        cost_with_inv, from_inv, _ = calculate_print_cost(scheme['tiles'], inventory, copies)

        saved = cost_no_inv - cost_with_inv
        savings.append({
            'index': i,
            'scheme': scheme,
            'cost_no_inv': cost_no_inv,
            'cost_with_inv': cost_with_inv,
            'from_inv': from_inv,
            'saved': saved
        })

    # 按节省成本从高到低排序
    savings.sort(key=lambda x: x['saved'], reverse=True)

    # 第二步：按排序分配库存
    remaining_inv = dict(inventory)
    total_cost = 0
    inventory_usage = {}

    for item in savings:
        i = item['index']
        scheme = item['scheme']
        copies = batch_results[i].get('copies', 1) if i < len(batch_results) else 1

        # 检查库存是否足够
        can_use = True
        for key, needed in item['from_inv'].items():
            if remaining_inv.get(key, 0) < needed:
                can_use = False
                break

        if can_use:
            # 使用库存
            cost = item['cost_with_inv']
            for key, used in item['from_inv'].items():
                remaining_inv[key] -= used
            inventory_usage[i] = item['from_inv']
        else:
            # 库存不足，不能使用库存
            cost = item['cost_no_inv']
            inventory_usage[i] = {}

        total_cost += cost

    return total_cost, inventory_usage


def optimize_batch_global(batch_results, inventory=None, grid_config: GridConfig = None, printer_config: PrinterConfig = None):
    """贪心 + 局部搜索优化

    Args:
        batch_results: 批量计算结果列表
        inventory: 可选库存字典 {"6x7": 3, ...}
        grid_config: GridConfig 实例，如果为 None 则使用默认配置
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置
    """
    if grid_config is None:
        grid_config = _build_grid_config()
    if printer_config is None:
        printer_config = _build_printer_config()

    if not batch_results:
        return None

    # 步骤1：各自找最优作为初始解
    # 注意：不传inventory，让每个抽屉选择最优的瓦片方案（与库存无关）
    # 库存分配由 calculate_batch_cost_with_inventory 统一处理
    initial_schemes = []
    for i, r in enumerate(batch_results):
        if r is None:
            initial_schemes.append(None)
            continue
        x, y = r['grid']
        copies = r.get('copies', 1)
        # 不传 inventory，每个抽屉选择成本最低的方案
        scheme = find_best_scheme(x, y, grid_config, inventory=None, copies=copies)
        initial_schemes.append(scheme)

    # 计算初始解的成本（打印次数或库存成本）
    if inventory:
        initial_cost, _ = calculate_batch_cost_with_inventory(
            initial_schemes, batch_results, inventory
        )
    else:
        initial_total, _ = calculate_total_prints(batch_results, initial_schemes, printer_config)
        initial_cost = initial_total

    # 步骤2：为每个抽屉生成所有方案
    all_options = []
    for result in batch_results:
        if result is None:
            all_options.append([None])
            continue
        x, y = result['grid']
        schemes = find_all_schemes(x, y, grid_config)
        all_options.append(schemes)

    # 步骤3：找最优组合
    best_schemes = initial_schemes.copy()
    best_cost = initial_cost

    # 对每个抽屉，尝试其他方案，看能否减少成本
    for i, options in enumerate(all_options):
        if len(options) <= 1:
            continue

        for option in options:
            # 构建新组合
            test_schemes = best_schemes.copy()
            test_schemes[i] = option

            # 检查是否有效（不能有 None）
            if None in test_schemes:
                continue

            # 计算新组合的成本（使用新的批量成本计算函数）
            if inventory:
                total, _ = calculate_batch_cost_with_inventory(
                    test_schemes, batch_results, inventory
                )
            else:
                total, _ = calculate_total_prints(batch_results, test_schemes, printer_config)

            if total < best_cost:
                best_schemes = test_schemes
                best_cost = total

    # 返回优化结果
    # 重新计算最终的库存使用情况，并更新到每个方案中
    if inventory:
        final_cost, final_inv_usage = calculate_batch_cost_with_inventory(
            best_schemes, batch_results, inventory
        )
        # 更新每个方案的 from_inventory 字段
        for i, scheme in enumerate(best_schemes):
            if scheme is not None and i in final_inv_usage:
                scheme['from_inventory'] = final_inv_usage[i]
    else:
        final_cost = best_cost

    return {
        'schemes': best_schemes,
        'total_prints': best_cost if not inventory else None,
        'cost': final_cost if inventory else None,
        'initial_prints': initial_cost if not inventory else None,
        'initial_cost': initial_cost if inventory else None,
        'improved': best_cost < initial_cost
    }


def build_batch_data(batch_results, merged_tiles, inventory=None, drawer_names=None, printer_config: PrinterConfig = None):
    """构建统一的批量方案数据结构，用于生成人类可读输出和 JSON 输出

    Args:
        batch_results: 批量计算结果列表
        merged_tiles: 合并后的瓦片字典
        inventory: 库存字典
        drawer_names: 抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置

    Returns:
        包含所有信息的统一字典
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    from opengrid.core.constants import TILE_THICKNESS

    if drawer_names is None:
        drawer_names = {}

    tile_thickness = printer_config.tile_thickness
    max_stacks = get_max_stacks(printer_config)
    sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0
    tiles_output = []

    # 记录库存使用情况
    from_inventory = {}
    need_print_tiles = {}

    for (w, h), info in sorted_tiles:
        cells = w * h
        total_stacks = info['total']

        # 检查库存（规格化：小边在前，与 _match_inventory 保持一致）
        key = f"{min(w, h)}x{max(w, h)}"
        available = inventory.get(key, 0) if inventory else 0
        to_print = max(0, total_stacks - available)

        # 记录库存使用
        if available > 0:
            from_inventory[key] = min(available, total_stacks)
        if to_print > 0:
            need_print_tiles[key] = to_print

        # 计算实际打印成本（基于需要打印的数量）
        if to_print > max_stacks:
            num_prints = (to_print + max_stacks - 1) // max_stacks
            stacks_per_print = to_print // num_prints
            remainder = to_print % num_prints

            height = stacks_per_print * tile_thickness
            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells
                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        elif to_print > 0:
            main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)
            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1
        # to_print == 0 means completely covered by inventory

        tiles_output.append({
            "width": w,
            "height": h,
            "stacks": total_stacks,
            "prints": total_prints if to_print > 0 else 0,
            "from_inventory": from_inventory.get(key, 0),
            "to_print": to_print
        })

    # 构建 drawers 列表（包含每个抽屉的详细信息）
    drawers_output = []
    # 从每个 drawer 的 scheme 中收集库存使用情况
    from_inventory_agg = {}
    need_print_agg = {}

    for r in batch_results:
        if not r:
            continue
        width = r['width']
        depth = r['depth']
        copies = r['copies']
        scheme = r['scheme']
        idx = r.get('index')

        # 获取抽屉名称
        name = drawer_names.get(idx, f"{width}×{depth}") if idx is not None else f"{width}×{depth}"

        # 获取该 drawer 的库存使用情况
        drawer_inv = _build_single_inventory(scheme, inventory) or {}
        drawer_from_inv = drawer_inv.get('from_inventory', {})
        drawer_need_print = drawer_inv.get('need_print', {})

        # 聚合到顶层
        for k, v in drawer_from_inv.items():
            from_inventory_agg[k] = from_inventory_agg.get(k, 0) + v
        for k, v in drawer_need_print.items():
            need_print_agg[k] = need_print_agg.get(k, 0) + v

        drawers_output.append({
            "name": name,
            "width": width,
            "depth": depth,
            "copies": copies,
            "scheme": {
                "x_parts": scheme['x_parts'],
                "y_parts": scheme['y_parts'],
                "x_splits": scheme['x_splits'],
                "y_splits": scheme['y_splits'],
            },
            "tiles": _format_tiles_from_scheme(scheme),
            "inventory": drawer_inv
        })

    # 构建输出
    output = {
        "drawers": drawers_output,
        "tiles": tiles_output,
        "stats": {
            "total_filament_g": round(total_main + total_support),
            "total_time_min": int(total_time),
            "total_prints": total_prints
        }
    }

    # 如果有库存，添加库存信息（从 drawer 级别聚合）
    if inventory and (from_inventory_agg or need_print_agg):
        output["inventory_usage"] = {
            "from_inventory": from_inventory_agg,
            "need_print": need_print_agg
        }

    return output


def _format_tiles_from_scheme(scheme):
    """将 scheme['tiles'] (元组列表) 转换为带计数的字典列表"""
    tiles = scheme.get('tiles', [])
    if not tiles:
        return []
    # 统计每个尺寸的数量
    counts = {}
    for w, h in tiles:
        key = (w, h)
        counts[key] = counts.get(key, 0) + 1
    # 转换为列表
    return [
        {"width": w, "height": h, "count": c}
        for (w, h), c in sorted(counts.items(), key=lambda x: x[0][0] * x[0][1], reverse=True)
    ]


def _build_single_inventory(scheme, inventory):
    """构建单个方案的库存信息"""
    from_inv = scheme.get('from_inventory', {})
    need_print = scheme.get('need_print', {})

    # 如果没有 need_print（抽屉没有使用库存），从 tiles 计算
    if scheme.get('tiles'):
        tiles = scheme.get('tiles', [])
        # 先统计所有瓦片
        tile_counts = {}
        for w, h in tiles:
            # 规格化：小边在前，与 _match_inventory 保持一致
            key = f"{min(w, h)}x{max(w, h)}"
            tile_counts[key] = tile_counts.get(key, 0) + 1

        # 如果有 from_inventory，计算需要打印的数量（总需求 - 库存）
        if from_inv:
            for key, inv_count in from_inv.items():
                total_needed = tile_counts.get(key, 0)
                need_print[key] = max(0, total_needed - inv_count)
        else:
            # 没有使用库存，全部需要打印
            need_print = tile_counts

    # 过滤掉 0 值的 need_print
    need_print = {k: v for k, v in need_print.items() if v > 0}

    # 收集所有需要的瓦片尺寸
    all_needed = {}
    if from_inv:
        for k, v in from_inv.items():
            all_needed[k] = all_needed.get(k, 0) + v
    if need_print:
        for k, v in need_print.items():
            all_needed[k] = all_needed.get(k, 0) + v

    if not all_needed:
        return None

    covered = 0
    total_sizes = 0
    for key in all_needed.keys():
        need = all_needed[key]
        available = inventory.get(key, 0) if inventory else 0
        total_sizes += 1
        if available >= need:
            covered += 1

    return {
        "coverage": {
            "covered": covered,
            "total": total_sizes,
            "percent": int(covered / total_sizes * 100) if total_sizes > 0 else 0
        },
        "from_inventory": from_inv,
        "need_print": need_print
    }


def print_batch_plan(batch_results, merged_tiles, inventory=None, json_output=False, drawer_names=None, printer_config: PrinterConfig = None):
    """打印批量打印计划

    Args:
        batch_results: 批量计算结果列表
        merged_tiles: 合并后的瓦片字典
        inventory: 库存字典
        json_output: 是否输出 JSON 格式
        drawer_names: 抽屉名称映射 {index: "name"}
        printer_config: PrinterConfig 实例，如果为 None 则使用默认配置
    """
    if printer_config is None:
        printer_config = _build_printer_config()

    from opengrid.core.constants import TILE_THICKNESS
    from opengrid.config import get_printer_config_or_default, load_config_or_default

    # 如果 drawer_names 为 None，创建空映射
    if drawer_names is None:
        drawer_names = {}

    # 计算 tile_thickness (瓦片厚度 + 接口间隙)
    config = load_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    interface_separation = config.get("opengrid", {}).get("interface_separation", 0.2)
    stacking_method = config.get("opengrid", {}).get("stacking_method", "Ironing")
    base_thickness = TILE_THICKNESS.get(tile_type, 6.8)
    if stacking_method == "Ironing":
        tile_thickness = base_thickness + 2 * interface_separation
    else:
        tile_thickness = base_thickness + 0.4 + 2 * interface_separation

    # 如果是 JSON 模式，只计算统计信息不打印
    if json_output:
        # 使用统一的批量数据结构
        output = build_batch_data(batch_results, merged_tiles, inventory, drawer_names, printer_config)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        # 返回统计信息字典
        total_filament = output['stats']['total_filament_g']
        # 估算主材/支撑比例 (75%/25%)
        return {
            'total_main': total_filament * 0.75,
            'total_support': total_filament * 0.25,
            'total_filament': total_filament,
            'total_time': output['stats']['total_time_min'],
            'total_prints': output['stats']['total_prints']
        }

    # 人类可读模式
    print("=" * 70)
    print("openGrid 批量打印计划 - 合并优化版")
    print("=" * 70)

    # 打印抽屉名称对照表（如果有多个抽屉）
    if drawer_names:
        print("\n--- 打印目标 ---")
        print(f"\n| 名字 | 尺寸 | 份数 |")
        print(f"|------|------|------|")
        for result in batch_results:
            if not result:
                continue
            idx = result.get('index')
            if idx is not None and idx in drawer_names:
                name = drawer_names[idx]
                width = result['width']
                depth = result['depth']
                copies = result['copies']
                print(f"| {name} | {width}×{depth}mm | {copies} |")

    # 先打印每个尺寸的分割方案
    print("\n--- 各尺寸分割方案 ---")
    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']
        x, y = result['grid']

        idx = result.get('index')
        if idx is not None and idx in drawer_names:
            name = drawer_names[idx]
            print(f"\n{name} × {copies} 份:")
        else:
            print(f"\n{width}×{depth}mm × {copies}份:")
        print(f"  格子: {x} × {y}")
        print(f"  分割: {scheme['x_parts']}×{scheme['y_parts']}")
        print(f"  X: {' + '.join(map(str, scheme['x_splits']))}")
        print(f"  Y: {' + '.join(map(str, scheme['y_splits']))}")

    # 打印合并后的瓦片清单
    print("\n" + "=" * 70)
    print("--- 合并后的瓦片清单（可一起打印）---")
    print("=" * 70)

    max_stacks = get_max_stacks(printer_config)

    # 按尺寸排序
    sorted_tiles = sorted(merged_tiles.items(), key=lambda x: (x[0][0] * x[0][1], x[0][0]), reverse=True)

    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0

    for (w, h), info in sorted_tiles:
        cells = w * h
        total_stacks = info['total']

        print(f"\n{w}×{h} 格 ({w*28}mm × {h*28}mm):")

        # 显示来源
        for src in info['by_drawer']:
            # 使用抽屉名称（如果有）
            drawer_name = src.get('name', src['size'])
            print(f"  来源: {drawer_name} = {src['total']} stack")

        # 检查库存
        key = f"{w}x{h}"
        available = inventory.get(key, 0) if inventory else 0
        to_print = max(0, total_stacks - available)

        # 显示库存使用情况
        if inventory:
            if available > 0:
                print(f"  库存: {min(available, total_stacks)}")
            if to_print > 0:
                print(f"  需打印: {to_print}")
            else:
                print(f"  需打印: 无 (完全使用库存)")

        # 计算打印次数（基于实际需要打印的数量）
        if to_print > max_stacks:
            num_prints = (to_print + max_stacks - 1) // max_stacks
            stacks_per_print = to_print // num_prints
            remainder = to_print % num_prints

            height = stacks_per_print * tile_thickness

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"  打印: {num_prints}次 ({stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                # 累计
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells

                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                print(f"  打印: {num_prints}次 (每次{stacks_per_print} stack, {height:.0f}mm)")
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        elif to_print > 0:
            height = to_print * tile_thickness
            main_g, support_g, time_min = calculate_filament_and_time(cells, to_print)

            print(f"  打印: 1次 ({to_print} stack, {height:.0f}mm)")
            print(f"    耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1
        # else: to_print == 0 means completely covered by inventory, no print needed

    # 打印统计
    print("\n" + "=" * 70)
    print("--- 总计 ---")
    print("=" * 70)
    print(f"总耗材: ~{total_main + total_support:.0f}g")
    print(f"  主耗材: ~{total_main:.0f}g")
    print(f"  支撑耗材: ~{total_support:.0f}g")
    print(f"总打印次数: {total_prints}次")
    print(f"总打印时间: ~{format_time(total_time)}")

    return {
        'total_main': total_main,
        'total_support': total_support,
        'total_filament': total_main + total_support,
        'total_time': total_time,
        'total_prints': total_prints
    }


def batch_mode(input_str, verbose=False, inventory=None, json_output=False):
    """批量计算模式

    Args:
        input_str: 输入字符串
        verbose: 是否详细输出
        inventory: 可选库存字典 {"6x7": 3, ...}
        json_output: 是否输出 JSON 格式
    """
    import re

    # 创建 GridConfig 和 PrinterConfig
    grid_config = _build_grid_config()
    printer_config = _build_printer_config()

    # 解析输入
    # 支持格式: "265x365:2 325x365:2" 或 "265 365 2 325 365 2"
    items = []

    # 方法1: 尝试 "宽x深:份数" 格式
    pattern = r'(\d+)[x×](\d+)(?::(\d+))?'
    matches = re.findall(pattern, input_str)

    if matches:
        for m in matches:
            width = int(m[0])
            depth = int(m[1])
            copies = int(m[2]) if m[2] else 1
            items.append((width, depth, copies))

    # 方法2: 如果解析失败，尝试空格分隔
    if not items:
        parts = input_str.split()
        # 尝试每三个一组
        i = 0
        while i + 2 < len(parts):
            try:
                width = int(parts[i])
                depth = int(parts[i+1])
                copies = int(parts[i+2])
                items.append((width, depth, copies))
                i += 3
            except:
                break

    if not items:
        print("无法解析输入格式")
        print("支持的格式:")
        print("  265x365:2 325x365:2 315x365:2")
        print("  265x365 325x365 315x365 (默认每项1份)")
        print("  265 365 2 325 365 2 315 365 2")
        return

    # 生成抽屉名称映射
    # 规则：唯一尺寸用尺寸命名，重复尺寸加序号
    drawer_names = {}
    size_counts = {}  # {size: count} 用于跟踪每个尺寸的出现次数

    for idx, (width, depth, copies) in enumerate(items):
        size_key = f"{width}×{depth}"
        if size_key not in size_counts:
            size_counts[size_key] = 0
        size_counts[size_key] += 1

    # 第二遍：为每个 item 分配名称
    size_indices = {}  # {size: current_index}
    for idx, (width, depth, copies) in enumerate(items):
        size_key = f"{width}×{depth}"
        if size_key not in size_indices:
            size_indices[size_key] = 1
        else:
            size_indices[size_key] += 1

        # 如果该尺寸只出现一次，直接用尺寸名；否则加序号
        if size_counts[size_key] == 1:
            drawer_names[idx] = size_key
        else:
            drawer_names[idx] = f"{size_key}#{size_indices[size_key]}"

    # 输出调试信息到 stderr（如果需要）
    # JSON 模式下不输出任何调试信息
    def _print(msg):
        if json_output:
            return  # JSON 模式下不打印任何内容
        else:
            print(msg)

    _print(f"解析到 {len(items)} 个抽屉:")
    for idx, (w, d, c) in enumerate(items):
        name = drawer_names[idx]
        _print(f"  {name}: {w}×{d}mm × {c}份")

    # 如果有库存，显示库存信息
    if inventory:
        _print(f"库存: {inventory}")
    _print("")

    # 计算每个尺寸的分割方案
    batch_results = []
    for idx, (width, depth, copies) in enumerate(items):
        result = calculate_single(width, depth, copies, verbose, index=idx, grid_config=grid_config)
        if result:
            batch_results.append(result)
        else:
            _print(f"警告: {width}×{depth}mm 无法生成有效方案")

    if not batch_results:
        _print("错误: 没有有效的尺寸")
        return

    # 根据是否有库存选择不同的优化方式
    if inventory:
        # 使用全局优化（带库存）
        optimized = optimize_batch_global(batch_results, inventory=inventory, grid_config=grid_config, printer_config=printer_config)
        # 更新 batch_results 中的 schemes 为优化后的方案
        if optimized and 'schemes' in optimized:
            for i, scheme in enumerate(optimized['schemes']):
                if i < len(batch_results) and scheme:
                    batch_results[i]['scheme'] = scheme
        # 始终使用 merge_and_optimize 获取合并的瓦片
        merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)
    else:
        # 简单的合并优化
        merged = merge_and_optimize(batch_results, drawer_names, printer_config=printer_config)

    # 打印计划
    stats = print_batch_plan(batch_results, merged, inventory=inventory, json_output=json_output, drawer_names=drawer_names, printer_config=printer_config)
