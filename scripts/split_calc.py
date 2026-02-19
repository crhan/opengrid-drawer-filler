#!/usr/bin/env python3
"""
openGrid 抽屉分割计算器 - 优化版
验证分割方案的合法性，输出最优分割
支持预设、JSON 输出、自动生成 STL
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

TILE_SIZE = 28    # mm
MAX_X = 10        # 最大X方向格数
MAX_Y = 11        # 最大Y方向格数
MIN_TILE = 2      # 最小瓦片格数
FULL_THICKNESS = 6.8 + 0.4  # Full版本单层厚度+间距(mm)
MAX_Z = 325       # 打印机Z轴最大高度(mm)

# 耗材和打印时间估算常量（基于实测数据）
FILAMENT_MAIN_PER_CELL = 1.13     # 主耗材: g/格/层
FILAMENT_SUPPORT_PER_CELL = 0.06  # 支撑耗材: g/格/层 (约主耗材的5.4%)
PRINT_TIME_PER_CELL = 3.1        # 打印时间: 分钟/格/层

# OpenSCAD 路径
OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE = "/Users/ruohanc/Documents/GitHub/QuackWorks/openGrid/openGrid.scad"
OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/"

# Bambu Studio 路径
BAMBU_STUDIO_PATH = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
BAMBU_OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/sliced/"
BAMBU_DEFAULT_PRINT_SETTINGS = "/Users/ruohanc/Library/Application Support/BambuStudio/user/1955088115/process/Opengrid堆叠打印.json"

# Orca Slicer 路径
ORCA_SLICER_PATH = "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
ORCA_OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/sliced/"
# Orca Slicer 内置预设路径
ORCA_MACHINE_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/machine/Bambu Lab P1P 0.4 nozzle.json"
ORCA_PROCESS_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/process/0.20mm Standard @BBL P1P.json"
ORCA_FILAMENT_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/filament/P1P/Bambu PLA Basic @BBL P1P.json"

# 预设抽屉尺寸
PRESETS = {
    "klean": (270, 170, "Klean件盒"),
    "ikea-sunda": (360, 500, "IKEA Sunda"),
    "ikea-kal": (360, 500, "IKEA KAL"),
    "ikea-alex": (360, 500, "IKEA Alex"),
    "standard": (400, 400, "标准抽屉"),
    "small": (300, 300, "小抽屉"),
    "medium": (400, 400, "中抽屉"),
    "large": (500, 500, "大抽屉"),
}


def get_max_stacks():
    """计算最大stack数量"""
    return int(MAX_Z // FULL_THICKNESS)


def get_grid_dimensions(width_mm, depth_mm):
    """计算可用格子数"""
    x = width_mm // TILE_SIZE
    y = depth_mm // TILE_SIZE
    return x, y


def validate_tile(w, h):
    """验证单块瓦片是否合法"""
    return MIN_TILE <= w <= MAX_X and MIN_TILE <= h <= MAX_Y


def split_with_limit(n, parts, max_val):
    """将数字n分割为parts个部分，每个部分不超过max_val"""
    if parts == 1:
        return [[n]] if n <= max_val else []

    results = []

    def recurse(remaining, current):
        if len(current) == parts - 1:
            if MIN_TILE <= remaining <= max_val:
                current.append(remaining)
                results.append(current[:])
                current.pop()
            return

        # 剪枝：如果剩余值太少无法分配给剩余部分，提前退出
        min_needed = MIN_TILE * (parts - len(current) - 1)
        if remaining < min_needed:
            return

        # 剪枝：如果剩余值太多无法分配给剩余部分，提前退出
        max_allowed = max_val * (parts - len(current) - 1)
        if remaining > max_allowed + max_val:
            return

        for i in range(MIN_TILE, min(max_val, remaining - min_needed) + 1):
            current.append(i)
            recurse(remaining - i, current)
            current.pop()

    recurse(n, [])
    return results


def calc_balance(splits):
    """计算分割的均衡度，返回最大值/最小值的比例（越小越均衡）"""
    if not splits or min(splits) == 0:
        return 1
    return max(splits) / min(splits)


def calc_scheme_balance(xs, ys):
    """计算方案的均衡度：取x方向和y方向均衡度的最大值"""
    x_balance = calc_balance(xs)
    y_balance = calc_balance(ys)
    return max(x_balance, y_balance)


def find_best_scheme(x, y, verbose=False):
    """直接寻找最优方案，找到1种尺寸就停止

    修复: 考虑旋转对称性，搜索两个方向并取最优解
    """
    # 首先检查是否需要分割
    if validate_tile(x, y):
        return {
            'x_parts': 1,
            'y_parts': 1,
            'x_splits': [x],
            'y_splits': [y],
            'tiles': [(x, y)],
            'unique_sizes': 1,
            'tile_count': 1
        }

    # 搜索原始方向
    best = _find_best_scheme_impl(x, y, verbose)

    # 如果 x != y，搜索旋转后的方向并比较
    if x != y:
        rotated = _find_best_scheme_impl(y, x, verbose)
        if rotated is not None:
            # 旋转结果：将 x_splits 和 y_splits 交换
            rotated_swapped = {
                'x_parts': rotated['y_parts'],
                'y_parts': rotated['x_parts'],
                'x_splits': rotated['y_splits'],
                'y_splits': rotated['x_splits'],
                'tiles': [(w, h) for h, w in rotated['tiles']],
                'unique_sizes': rotated['unique_sizes'],
                'tile_count': rotated['tile_count'],
                'balance': rotated['balance']
            }
            # 比较：独特尺寸少 > 瓦片数少 > 均衡度好
            if best is None or \
               rotated_swapped['unique_sizes'] < best['unique_sizes'] or \
               (rotated_swapped['unique_sizes'] == best['unique_sizes'] and rotated_swapped['tile_count'] < best['tile_count']) or \
               (rotated_swapped['unique_sizes'] == best['unique_sizes'] and rotated_swapped['tile_count'] == best['tile_count'] and rotated_swapped['balance'] < best['balance']):
                best = rotated_swapped

    return best


def _find_best_scheme_impl(x, y, verbose=False):
    """find_best_scheme 的实际实现"""
    best = None
    candidates_checked = 0

    # 从最少分割开始尝试
    for x_parts in range(2, 8):
        for y_parts in range(1, 5):
            total_tiles = x_parts * y_parts
            if total_tiles > 20:
                continue

            # 生成有效的 X 分割
            x_splits = split_with_limit(x, x_parts, MAX_X)
            if not x_splits:
                continue

            # 生成有效的 Y 分割
            y_splits = split_with_limit(y, y_parts, MAX_Y)
            if not y_splits:
                continue

            # 遍历所有组合，找最优
            for xs in x_splits:
                for ys in y_splits:
                    candidates_checked += 1

                    # 计算瓦片
                    tiles = []
                    unique = set()
                    valid = True

                    for xd in xs:
                        for yd in ys:
                            if not validate_tile(xd, yd):
                                valid = False
                                break
                            tiles.append((xd, yd))
                            unique.add((xd, yd))

                    if not valid:
                        continue

                    balance = calc_scheme_balance(xs, ys)

                    scheme = {
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': tiles,
                        'unique_sizes': len(unique),
                        'tile_count': len(tiles),
                        'balance': balance
                    }

                    # 优先级: 1)独特尺寸最少 2)瓦片数最少 3)均衡度最好
                    if best is None or \
                       (len(unique) < best['unique_sizes']) or \
                       (len(unique) == best['unique_sizes'] and len(tiles) < best['tile_count']) or \
                       (len(unique) == best['unique_sizes'] and len(tiles) == best['tile_count'] and balance < best['balance']):
                        best = scheme
                        if verbose:
                            print(f"  [DEBUG] New best: {len(unique)} sizes, {len(tiles)} tiles, balance={balance:.2f}")

                    # 找到最优解：1种尺寸，停止搜索
                    if len(unique) == 1:
                        if verbose:
                            print(f"  [DEBUG] Checked {candidates_checked} candidates")
                        return best

    if verbose:
        print(f"  [DEBUG] Checked {candidates_checked} candidates, no perfect solution")
    return best


def calculate_filament_and_time(cells, stacks):
    """计算耗材和打印时间"""
    main = cells * FILAMENT_MAIN_PER_CELL * stacks
    support = cells * FILAMENT_SUPPORT_PER_CELL * stacks
    time_min = cells * PRINT_TIME_PER_CELL * stacks
    return main, support, time_min


def format_time(minutes):
    """格式化打印时间"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}h{mins}m"
    return f"{mins}m"


def generate_stl(width, height, stacks, verbose=False, force=False):
    """生成单个 STL 文件"""
    filename = f"opengrid_{width}x{height}_Full_s{stacks}.stl"
    output_dir = os.path.join(OUTPUT_DIR, f"{width}x{height}_Full/")
    output_path = os.path.join(output_dir, filename)

    # 检查文件是否已存在
    if os.path.exists(output_path) and not force:
        return output_path, "exists"

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        OPENSCAD_PATH,
        "-o", output_path,
        "-D", f'Full_or_Lite="Full"',
        "-D", f"Board_Width={width}",
        "-D", f"Board_Height={height}",
        "-D", f"Stack_Count={stacks}",
        "-D", 'Stacking_Method="Ironing"',
        "-D", "Interface_Separation=0.2",
        "-D", 'Screw_Mounting="Everywhere"',
        SCAD_FILE
    ]

    if verbose:
        print(f"  [DEBUG] Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if verbose:
            print(f"  [DEBUG] Error: {result.stderr}")
        return None, result.stderr

    return output_path, None


def slice_with_bambu(stl_paths, output_name, print_settings=None, machine_settings=None, verbose=False):
    """使用 Bambu Studio 切片 STL 文件"""
    if not stl_paths:
        return None, "No STL files to slice"

    os.makedirs(BAMBU_OUTPUT_DIR, exist_ok=True)

    output_3mf = os.path.join(BAMBU_OUTPUT_DIR, f"{output_name}.3mf")

    cmd = [
        BAMBU_STUDIO_PATH,
        "--slice", "0",  # Slice all plates
        "--outputdir", BAMBU_OUTPUT_DIR,
    ]

    # 添加打印设置
    if print_settings:
        cmd.extend(["--load-settings", print_settings])

    # 添加机器设置
    if machine_settings:
        cmd.extend(["--load-filaments", machine_settings])

    # 添加所有 STL 文件
    cmd.extend(stl_paths)

    if verbose:
        print(f"  [DEBUG] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None, "切片超时"
    except Exception as e:
        return None, f"启动失败: {e}"

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        # 检查是否是因为无头模式
        if "display" in error_msg.lower() or "gtk" in error_msg.lower():
            return None, "Bambu Studio 需要图形界面，无法在无头模式下运行"
        if verbose:
            print(f"  [DEBUG] Error: {error_msg}")
        return None, error_msg

    # 检查输出文件
    if os.path.exists(output_3mf):
        return output_3mf, None
    else:
        # 尝试找到输出的文件
        for f in os.listdir(BAMBU_OUTPUT_DIR):
            if f.endswith(".3mf"):
                return os.path.join(BAMBU_OUTPUT_DIR, f), None

    # 没有找到输出文件，但也没有错误 - 可能是无头模式问题
    return None, "切片完成但未生成输出文件（Bambu Studio 可能需要图形界面）"


def slice_with_orca(stl_paths, output_name, verbose=False):
    """使用 Orca Slicer 切片 STL 文件

    注意: Orca Slicer CLI 在 macOS 上需要显示上下文，无法无头运行。
    此函数会尝试运行，但如果失败会返回错误信息。
    """
    if not stl_paths:
        return None, "No STL files to slice"

    os.makedirs(ORCA_OUTPUT_DIR, exist_ok=True)

    output_3mf = os.path.join(ORCA_OUTPUT_DIR, f"{output_name}.3mf")

    cmd = [
        ORCA_SLICER_PATH,
        "--arrange", "1",  # 自动排列
        "--load-settings", ORCA_MACHINE_PRESET,
        "--load-settings", ORCA_PROCESS_PRESET,
        "--load-filaments", ORCA_FILAMENT_PRESET,
        "--export-3mf", output_3mf,
    ]

    # 添加所有 STL 文件
    cmd.extend(stl_paths)

    if verbose:
        print(f"  [DEBUG] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None, "切片超时"
    except Exception as e:
        return None, f"启动失败: {e}"

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        # 检查是否是因为无头模式
        if "shader" in error_msg.lower() or "gl_" in error_msg.lower() or "display" in error_msg.lower():
            return None, "Orca Slicer 需要图形界面，无法在无头模式下运行。建议使用 -o 选项在 GUI 中打开 STL 文件。"
        if verbose:
            print(f"  [DEBUG] Error: {error_msg}")
        return None, error_msg

    # 检查输出文件
    if os.path.exists(output_3mf):
        return output_3mf, None
    else:
        # 尝试找到输出的文件
        for f in os.listdir(ORCA_OUTPUT_DIR):
            if f.endswith(".3mf"):
                return os.path.join(ORCA_OUTPUT_DIR, f), None

    return None, "切片完成但未生成输出文件（Orca Slicer 可能需要图形界面）"


def open_in_slicer(stl_paths, slicer="bambu"):
    """在切片器中打开 STL 文件"""
    if slicer == "orca":
        cmd = [ORCA_SLICER_PATH] + list(stl_paths)
    else:
        cmd = [BAMBU_STUDIO_PATH] + list(stl_paths)

    try:
        subprocess.Popen(cmd)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_all_stls(scheme, copies, verbose=False, force=False):
    """生成所有 STL 文件（并发执行）"""
    # 按尺寸分组统计
    tile_counts = {}
    for w, h in scheme['tiles']:
        key = (w, h)
        tile_counts[key] = tile_counts.get(key, 0) + 1

    max_stacks = get_max_stacks()

    # 收集所有需要生成的任务
    tasks = []
    for (w, h), count in tile_counts.items():
        total_stacks = count * copies

        # 检查是否需要分多次打印
        if total_stacks > max_stacks:
            num_prints = (total_stacks + max_stacks - 1) // max_stacks
            stacks_per_print = total_stacks // num_prints
            remainder = total_stacks % num_prints

            for i in range(num_prints):
                stacks = stacks_per_print + (1 if i < remainder else 0)
                if stacks == 0:
                    continue
                tasks.append((w, h, stacks))
        else:
            tasks.append((w, h, total_stacks))

    print(f"\n--- 生成 STL ({len(tasks)} 个任务) ---")

    # 检查哪些文件已存在
    existing = []
    to_generate = []
    for w, h, stacks in tasks:
        filename = f"opengrid_{w}x{h}_Full_s{stacks}.stl"
        output_dir = os.path.join(OUTPUT_DIR, f"{w}x{h}_Full/")
        output_path = os.path.join(output_dir, filename)

        if os.path.exists(output_path) and not force:
            existing.append((w, h, stacks, output_path))
        else:
            to_generate.append((w, h, stacks, output_path))

    if existing:
        print(f"  已存在: {len(existing)} 个")
        for w, h, stacks, path in existing:
            print(f"    {w}×{h}: {os.path.basename(path)}")

    if not to_generate:
        print("\n所有文件已存在，跳过生成")
        return [p for _, _, _, p in existing]

    print(f"  需要生成: {len(to_generate)} 个")

    # 并发执行生成任务
    results = []
    errors = []

    def generate_task(w, h, stacks):
        return generate_stl(w, h, stacks, verbose, force)

    # 使用线程池并发执行，最多同时运行 2 个 OpenSCAD 进程
    max_workers = min(2, len(to_generate))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(generate_task, w, h, stacks): (w, h, stacks)
            for w, h, stacks, _ in to_generate
        }

        for future in as_completed(future_to_task):
            w, h, stacks = future_to_task[future]
            try:
                path, err = future.result()
                if err and err != "exists":
                    errors.append((w, h, err))
                    print(f"  {w}×{h}: 生成失败")
                elif err == "exists":
                    print(f"  {w}×{h}: 已存在（跳过）")
                else:
                    results.append(path)
                    print(f"  {w}×{h}: {os.path.basename(path)}")
            except Exception as e:
                errors.append((w, h, str(e)))
                print(f"  {w}×{h}: 异常 - {e}")

    generated = len(results)
    skipped = len(existing)
    print(f"\n完成: 生成 {generated} 个, 跳过 {skipped} 个, 失败 {len(errors)} 个")

    if errors:
        print("失败列表:")
        for w, h, err in errors:
            print(f"  {w}×{h}: {err}")

    return results


def print_plan(width, depth, scheme, copies=1, verbose=False):
    """打印分割方案"""
    x, y = get_grid_dimensions(width, depth)

    print("=" * 60)
    print("openGrid 抽屉铺满打印计划")
    print("=" * 60)
    print(f"抽屉尺寸: {width}mm × {depth}mm")
    print(f"有效格子: {x} × {y} = {x * y}格")
    print(f"打印份数: {copies}套")
    print()

    print("--- 分割方案 ---")
    print(f"分割: {scheme['x_parts']}×{scheme['y_parts']}")
    print(f"X方向: {x} = {' + '.join(map(str, scheme['x_splits']))}")
    print(f"Y方向: {y} = {' + '.join(map(str, scheme['y_splits']))}")
    print()

    # 打印排布图
    print("排布:")
    for y_dim in scheme['y_splits']:
        row = ""
        for x_dim in scheme['x_splits']:
            row += f"{x_dim}×{y_dim} "
        print(row)

    print()
    print("--- 瓦片清单 ---")

    # 按尺寸分组统计
    tile_counts = {}
    for w, h in scheme['tiles']:
        key = f"{w}×{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    unique_count = len(tile_counts)
    max_stacks = get_max_stacks()

    # 累计统计
    total_main = 0
    total_support = 0
    total_time = 0
    total_prints = 0

    for size, count in tile_counts.items():
        w, h = map(int, size.split('×'))
        cells = w * h
        total_stacks = count * copies

        # 检查是否需要分多次打印
        if total_stacks > max_stacks:
            # 分成多次打印
            num_prints = (total_stacks + max_stacks - 1) // max_stacks
            stacks_per_print = total_stacks // num_prints
            remainder = total_stacks % num_prints

            height = stacks_per_print * FULL_THICKNESS

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"{size}: {total_stacks} stack (分{num_prints}次打印: {stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                # 剩余部分
                extra_cells_time = remainder * PRINT_TIME_PER_CELL * cells
                extra_cells_main = remainder * FILAMENT_MAIN_PER_CELL * cells
                extra_cells_support = remainder * FILAMENT_SUPPORT_PER_CELL * cells
                total_time_this = time_per * (num_prints - 1) + extra_cells_time
                total_main_this = main_per * (num_prints - 1) + extra_cells_main
                total_support_this = support_per * (num_prints - 1) + extra_cells_support
                print(f"       耗材: {total_main_this:.1f}g, 时间: {format_time(total_time_this)} ({format_time(time_per)}/次 × {num_prints-1}次 + {format_time(extra_cells_time)})")
            else:
                total_time_this = time_per * num_prints
                print(f"{size}: {total_stacks} stack 分{num_prints}次打印 (每次{stacks_per_print} stack, {height:.0f}mm)")
                print(f"       耗材: {main_per * num_prints:.1f}g, 时间: {format_time(total_time_this)} ({format_time(time_per)}/次 × {num_prints}次)")

            # 累计
            total_main += main_per * num_prints
            total_support += support_per * num_prints
            total_time += time_per * num_prints
            total_prints += num_prints

            if remainder > 0:
                total_main += remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += remainder * FILAMENT_SUPPORT_PER_CELL * cells
                total_time += remainder * PRINT_TIME_PER_CELL * cells
        else:
            height = total_stacks * FULL_THICKNESS
            main_g, support_g, time_min = calculate_filament_and_time(cells, total_stacks)

            print(f"{size}: {total_stacks} stack ({height:.0f}mm)")
            print(f"       耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1

    print()
    print("--- 耗材估算 ---")
    print(f"主耗材: ~{total_main:.0f}g")
    print(f"支撑耗材: ~{total_support:.0f}g")
    print(f"总耗材: ~{total_main + total_support:.0f}g ({copies}份)")

    print()
    print("--- 打印时间估算 ---")
    print(f"预计总时间: ~{format_time(total_time)} ({total_prints}次打印)")

    print()
    print("--- 安装说明 ---")
    print("1. 打印 STL")
    print("2. 使用连接件组装")
    print("3. 放入抽屉")

    return {
        'total_main': total_main,
        'total_support': total_support,
        'total_filament': total_main + total_support,
        'total_time': total_time,
        'total_prints': total_prints
    }


def output_json(width, depth, scheme, copies, stats):
    """输出 JSON 格式"""
    # 按尺寸分组
    tile_counts = {}
    for w, h in scheme['tiles']:
        key = f"{w}×{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    tiles_list = []
    for size, count in tile_counts.items():
        w, h = map(int, size.split('×'))
        tiles_list.append({
            "width": w,
            "height": h,
            "count": count
        })

    output = {
        "drawer": {
            "width": width,
            "depth": depth
        },
        "grid": {
            "x": width // TILE_SIZE,
            "y": depth // TILE_SIZE
        },
        "scheme": {
            "x_parts": scheme['x_parts'],
            "y_parts": scheme['y_parts'],
            "x_splits": scheme['x_splits'],
            "y_splits": scheme['y_splits'],
            "tiles": tiles_list
        },
        "stats": {
            "unique_sizes": scheme['unique_sizes'],
            "total_tiles": scheme['tile_count'],
            "total_filament_g": round(stats['total_filament']),
            "total_time_min": int(stats['total_time']),
            "total_prints": stats['total_prints']
        }
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


def list_presets():
    """列出所有预设"""
    print("可用预设:")
    for name, (w, h, desc) in PRESETS.items():
        print(f"  {name:12} {w:4}×{h:4}mm - {desc}")


def parse_batch_input(input_str):
    """ '解析批量输入，如265x365:2 325x365:2 315x365:2'

    支持格式:
    - 265x365:2  (宽度x深度:份数)
    - 265 365 2 (宽度 深度 份数)
    """
    items = []

    # 首先尝试解析 "宽x深:份数" 格式
    import re
    # 匹配 "265x365:2" 或 "265x365x2" 格式
    pattern = r'(\d+)[x×](\d+)[x:(\d+)]?'

    # 按空格分割
    parts = input_str.strip().split()

    for part in parts:
        # 尝试匹配 "宽x深:份数" 格式
        match = re.match(r'(\d+)[x×](\d+)(?::(\d+))?', part)
        if match:
            width = int(match.group(1))
            depth = int(match.group(2))
            copies = int(match.group(3)) if match.group(3) else 1
            items.append((width, depth, copies))
            continue

        # 尝试直接匹配数字（作为宽度）
        if part.isdigit():
            # 可能是单维度，需要更多信息
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


def calculate_single(width, depth, copies=1, verbose=False):
    """计算单个尺寸的分割方案"""
    x, y = get_grid_dimensions(width, depth)

    if x < MIN_TILE or y < MIN_TILE:
        return None

    scheme = find_best_scheme(x, y, verbose)

    if not scheme:
        return None

    return {
        'width': width,
        'depth': depth,
        'copies': copies,
        'grid': (x, y),
        'scheme': scheme
    }


def merge_and_optimize(batch_results):
    """合并多个尺寸的方案，优化共用尺寸

    策略:
    1. 收集所有需要的瓦片尺寸
    2. 统计每个尺寸的总需求数量
    3. 输出合并后的打印计划
    """
    # 收集所有瓦片尺寸及其需求
    all_tiles = {}  # {(w, h): {drawer: count, total: total_count}}

    for result in batch_results:
        if not result:
            continue

        width = result['width']
        depth = result['depth']
        copies = result['copies']
        scheme = result['scheme']

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
            all_tiles[(w, h)]['by_drawer'].append({
                'size': f"{width}×{depth}",
                'copies': copies,
                'tiles_per_copy': count,
                'total': total_for_drawer
            })

    return all_tiles


def print_batch_plan(batch_results, merged_tiles):
    """打印批量打印计划"""
    print("=" * 70)
    print("openGrid 批量打印计划 - 合并优化版")
    print("=" * 70)

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

        print(f"\n{width}×{depth}mm × {copies}份:")
        print(f"  格子: {x} × {y}")
        print(f"  分割: {scheme['x_parts']}×{scheme['y_parts']}")
        print(f"  X: {' + '.join(map(str, scheme['x_splits']))}")
        print(f"  Y: {' + '.join(map(str, scheme['y_splits']))}")

    # 打印合并后的瓦片清单
    print("\n" + "=" * 70)
    print("--- 合并后的瓦片清单（可一起打印）---")
    print("=" * 70)

    max_stacks = get_max_stacks()

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
            print(f"  来源: {src['size']} × {src['copies']}份 = {src['total']} stack")

        # 计算打印次数
        if total_stacks > max_stacks:
            num_prints = (total_stacks + max_stacks - 1) // max_stacks
            stacks_per_print = total_stacks // num_prints
            remainder = total_stacks % num_prints

            height = stacks_per_print * FULL_THICKNESS

            main_per, support_per, time_per = calculate_filament_and_time(cells, stacks_per_print)

            if remainder > 0:
                print(f"  需打印: {num_prints}次 ({stacks_per_print}+{remainder} stack/次, {height:.0f}mm)")
                # 累计
                total_main += main_per * (num_prints - 1) + remainder * FILAMENT_MAIN_PER_CELL * cells
                total_support += support_per * (num_prints - 1) + remainder * FILAMENT_SUPPORT_PER_CELL * cells

                time_main = time_per * (num_prints - 1) + remainder * PRINT_TIME_PER_CELL * cells
                total_time += time_main
            else:
                print(f"  需打印: {num_prints}次 (每次{stacks_per_print} stack, {height:.0f}mm)")
                total_main += main_per * num_prints
                total_support += support_per * num_prints
                total_time += time_per * num_prints

            total_prints += num_prints
        else:
            height = total_stacks * FULL_THICKNESS
            main_g, support_g, time_min = calculate_filament_and_time(cells, total_stacks)

            print(f"  需打印: 1次 ({total_stacks} stack, {height:.0f}mm)")
            print(f"    耗材: {main_g + support_g:.1f}g, 时间: {format_time(time_min)}")

            total_main += main_g
            total_support += support_g
            total_time += time_min
            total_prints += 1

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


def batch_mode(input_str, verbose=False):
    """批量计算模式"""
    import re

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

    print(f"解析到 {len(items)} 个尺寸:")
    for w, d, c in items:
        print(f"  {w}×{d}mm × {c}份")
    print()

    # 计算每个尺寸的分割方案
    batch_results = []
    for width, depth, copies in items:
        result = calculate_single(width, depth, copies, verbose)
        if result:
            batch_results.append(result)
        else:
            print(f"警告: {width}×{depth}mm 无法生成有效方案")

    if not batch_results:
        print("错误: 没有有效的尺寸")
        return

    # 合并优化
    merged = merge_and_optimize(batch_results)

    # 打印计划
    stats = print_batch_plan(batch_results, merged)

    return stats


def interactive_mode():
    """交互式输入"""
    print("openGrid 抽屉分割计算器")
    print("=" * 40)

    # 显示预设
    print("\n可用预设:")
    for name, (w, h, desc) in PRESETS.items():
        print(f"  {name:12} {w}×{h}mm - {desc}")
    print("  custom      自定义尺寸")

    preset = input("\n选择预设 (直接回车使用 custom): ").strip().lower()

    if preset == "" or preset == "custom":
        width = int(input("抽屉宽度 (mm): "))
        depth = int(input("抽屉深度 (mm): "))
    elif preset in PRESETS:
        width, depth = PRESETS[preset][0], PRESETS[preset][1]
        print(f"使用预设: {PRESETS[preset][2]} ({width}×{depth}mm)")
    else:
        print(f"未知预设: {preset}")
        sys.exit(1)

    copies = input("打印份数 (默认1): ").strip()
    copies = int(copies) if copies else 1

    return width, depth, copies


def main():
    parser = argparse.ArgumentParser(
        description='openGrid 抽屉分割计算器 - 优化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 split_calc.py                    # 交互式
  python3 split_calc.py 485 425            # 指定尺寸
  python3 split_calc.py 485 425 -c 3       # 指定份数
  python3 split_calc.py -p klean           # 使用预设
  python3 split_calc.py 485 425 -j         # JSON 输出
  python3 split_calc.py 485 425 -g         # 生成 STL
  python3 split_calc.py 485 425 -g -v      # 生成 STL (详细)

  # 批量模式（自动合并优化）
  python3 split_calc.py -b "265x365:2 325x365:2 315x365:2"
  python3 split_calc.py -b "265x365 325x365 315x365"
  python3 split_calc.py -b "265 365 2 325 365 2 315 365 2"

预设尺寸:
  klean       Klean件盒 270×170mm
  ikea-sunda  IKEA Sunda 360×500mm
  ikea-kal    IKEA KAL 360×500mm
  ikea-alex   IKEA Alex 360×500mm
  standard    标准抽屉 400×400mm
        """
    )

    parser.add_argument('width', nargs='?', type=int, help='抽屉宽度(mm)')
    parser.add_argument('depth', nargs='?', type=int, help='抽屉深度(mm)')
    parser.add_argument('-c', '--copies', type=int, default=1, help='打印份数 (默认1)')
    parser.add_argument('-p', '--preset', type=str, help='预设尺寸 (klean, ikea-sunda, ikea-kal, ikea-alex, standard, small, medium, large)')
    parser.add_argument('-b', '--batch', type=str, help='批量计算: "265x365:2 325x365:2" 或 "265 365 2 325 365 2"')
    parser.add_argument('-j', '--json', action='store_true', help='JSON 格式输出')
    parser.add_argument('-g', '--generate', action='store_true', help='自动生成 STL 文件')
    parser.add_argument('-f', '--force', action='store_true', help='强制重新生成已存在的 STL 文件')
    parser.add_argument('-s', '--slice', action='store_true', help='使用切片器切片（需配合 --slicer 指定）')
    parser.add_argument('--slicer', type=str, default='bambu', choices=['bambu', 'orca'], help='选择切片器: bambu 或 orca (默认 bambu)')
    parser.add_argument('-o', '--open', action='store_true', help='在切片器中打开生成的 STL 文件')
    parser.add_argument('--print-settings', type=str, help='Bambu Studio 打印设置文件 (.json)')
    parser.add_argument('--machine-settings', type=str, help='Bambu Studio 机器/耗材设置文件 (.json)')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--list-presets', action='store_true', help='列出所有预设')
    args = parser.parse_args()

    # 批量模式处理
    if args.batch:
        batch_mode(args.batch, args.verbose)
        return

    # 列出预设
    if args.list_presets:
        list_presets()
        return

    # 交互式模式
    if args.width is None and args.preset is None:
        width, depth, copies = interactive_mode()
    elif args.preset:
        if args.preset not in PRESETS:
            print(f"错误: 未知预设 '{args.preset}'")
            print("\n可用预设:")
            list_presets()
            sys.exit(1)
        width, depth, _ = PRESETS[args.preset]
        copies = args.copies
    else:
        width = args.width
        depth = args.depth
        copies = args.copies

    # 验证参数
    if width is None or depth is None:
        print("错误: 请提供抽屉尺寸或使用预设")
        parser.print_help()
        sys.exit(1)

    if width < 50 or depth < 50:
        print("错误: 尺寸太小")
        sys.exit(1)

    if args.verbose:
        print(f"[DEBUG] Input: {width}mm × {depth}mm, copies={copies}")

    x, y = get_grid_dimensions(width, depth)

    print(f"输入: {width}mm × {depth}mm")
    print(f"格子: {x} × {y}")
    print()

    if x < MIN_TILE or y < MIN_TILE:
        print("错误: 抽屉尺寸太小，无法放置最小瓦片")
        sys.exit(1)

    scheme = find_best_scheme(x, y, args.verbose)

    if not scheme:
        print("错误: 无法生成有效方案!")
        sys.exit(1)

    print(f"最优: {scheme['unique_sizes']}种尺寸, {scheme['tile_count']}块瓦片")
    print()

    stats = print_plan(width, depth, scheme, copies, args.verbose)

    if args.json:
        output_json(width, depth, scheme, copies, stats)

    if args.generate:
        stl_files = generate_all_stls(scheme, copies, args.verbose, args.force)

        # 如果需要在 slicer 中打开
        if args.open and stl_files:
            slicer_name = "Orca Slicer" if args.slicer == "orca" else "Bambu Studio"
            print(f"\n--- 在 {slicer_name} 中打开 ---")
            print(f"  打开 {len(stl_files)} 个 STL 文件...")

            success, err = open_in_slicer(stl_files, args.slicer)
            if success:
                print(f"  已在 {slicer_name} 中打开文件")
                if args.slicer == "orca":
                    print(f"  提示: 请手动选择打印预设并排列模型")
                else:
                    print(f"  提示: 请在右侧面板选择打印预设: 'Opengrid堆叠打印'")
            else:
                print(f"  打开失败: {err}")

        # 如果需要切片
        elif args.slice and stl_files:
            output_name = f"opengrid_{width}x{depth}_c{copies}"
            slicer_name = "Orca Slicer" if args.slicer == "orca" else "Bambu Studio"
            print(f"\n--- {slicer_name} 切片 ---")
            print(f"  输入文件: {len(stl_files)} 个 STL")
            print(f"  输出名称: {output_name}")

            if args.slicer == "orca":
                slice_path, err = slice_with_orca(
                    stl_files,
                    output_name,
                    args.verbose
                )
            else:
                slice_path, err = slice_with_bambu(
                    stl_files,
                    output_name,
                    args.print_settings,
                    args.machine_settings,
                    args.verbose
                )

            if err:
                print(f"  切片失败: {err}")
                print(f"  提示: 可以使用 -o 参数在切片器中手动打开文件")
            else:
                print(f"  切片完成: {os.path.basename(slice_path)}")
                print(f"  保存位置: {slice_path}")

        # 打开 STL 文件
        elif args.open and stl_files:
            slicer_name = "Orca Slicer" if args.slicer == "orca" else "Bambu Studio"
            print(f"\n--- 在 {slicer_name} 中打开 ---")

            success, err = open_in_slicer(stl_files, args.slicer)
            if success:
                print(f"  已在 {slicer_name} 中打开 {len(stl_files)} 个文件")
                if args.slicer == "orca":
                    print(f"  提示: 请手动选择打印预设并排列模型")
                else:
                    print(f"  提示: 请在右侧面板选择打印预设: 'Opengrid堆叠打印'")
            else:
                print(f"  打开失败: {err}")

if __name__ == "__main__":
    main()
