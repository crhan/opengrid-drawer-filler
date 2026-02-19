#!/usr/bin/env python3
"""
openGrid STL 生成和切片工具
支持 CLI 和 Python 模块导入两种调用方式
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 常量 ===
TILE_SIZE = 28
MAX_Z = 325
FULL_THICKNESS = 6.8 + 0.4

# 获取 skill 目录路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")

# OpenSCAD 路径
OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE = os.path.join(VENDOR_DIR, "QuackWorks", "openGrid", "openGrid.scad")
OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/"

# Bambu Studio 路径
BAMBU_STUDIO_PATH = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
BAMBU_OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/sliced/"
BAMBU_DEFAULT_PRINT_SETTINGS = "/Users/ruohanc/Library/Application Support/BambuStudio/user/1955088115/process/Opengrid堆叠打印.json"

# Orca Slicer 路径
ORCA_SLICER_PATH = "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
ORCA_OUTPUT_DIR = "/Users/ruohanc/Library/CloudStorage/SynologyDrive-homeNAS/3D模型/opengrid/sliced/"
ORCA_MACHINE_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/machine/Bambu Lab P1P 0.4 nozzle.json"
ORCA_PROCESS_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/process/0.20mm Standard @BBL P1P.json"
ORCA_FILAMENT_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/filament/P1P/Bambu PLA Basic @BBL P1P.json"


def get_max_stacks():
    """计算最大stack数量"""
    return int(MAX_Z // FULL_THICKNESS)


def generate_stl(width, height, stacks, verbose=False, force=False):
    """生成单个 STL 文件

    Args:
        width: 瓦片宽度（格数）
        height: 瓦片高度（格数）
        stacks: 堆叠层数
        verbose: 是否输出详细信息
        force: 是否强制重新生成

    Returns:
        (output_path, error): 成功时返回文件路径和None，失败时返回None和错误信息
    """
    # 输入验证
    if width <= 0 or height <= 0 or stacks <= 0:
        return None, f"Invalid parameters: width={width}, height={height}, stacks={stacks}"

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
        "-D", 'Full_or_Lite="Full"',
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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        if verbose:
            print(f"  [DEBUG] Error: {result.stderr}")
        return None, result.stderr

    return output_path, None


def generate_all_stls(scheme, copies, verbose=False, force=False):
    """生成所有 STL 文件（并发执行）

    Args:
        scheme: 分割方案字典，需包含 'tiles' 键
        copies: 打印份数
        verbose: 是否输出详细信息
        force: 是否强制重新生成

    Returns:
        list: 成功生成的 STL 文件路径列表
    """
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
            print(f"    {w}x{h}: {os.path.basename(path)}")

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
                    print(f"  {w}x{h}: 生成失败")
                elif err == "exists":
                    print(f"  {w}x{h}: 已存在（跳过）")
                else:
                    results.append(path)
                    print(f"  {w}x{h}: {os.path.basename(path)}")
            except Exception as e:
                errors.append((w, h, str(e)))
                print(f"  {w}x{h}: 异常 - {e}")

    generated = len(results)
    skipped = len(existing)
    print(f"\n完成: 生成 {generated} 个, 跳过 {skipped} 个, 失败 {len(errors)} 个")

    if errors:
        print("失败列表:")
        for w, h, err in errors:
            print(f"  {w}x{h}: {err}")

    return results

def slice_with_bambu(stl_paths, output_name, print_settings=None, machine_settings=None, verbose=False):
    """使用 Bambu Studio 切片 STL 文件

    Args:
        stl_paths: STL 文件路径列表
        output_name: 输出文件名（不含扩展名）
        print_settings: 打印设置文件路径
        machine_settings: 机器/耗材设置文件路径
        verbose: 是否输出详细信息

    Returns:
        (output_path, error): 成功时返回3MF路径和None，失败时返回None和错误信息
    """
    if not stl_paths:
        return None, "No STL files to slice"

    os.makedirs(BAMBU_OUTPUT_DIR, exist_ok=True)

    output_3mf = os.path.join(BAMBU_OUTPUT_DIR, f"{output_name}.3mf")

    cmd = [
        BAMBU_STUDIO_PATH,
        "--slice", "0",
        "--outputdir", BAMBU_OUTPUT_DIR,
    ]

    if print_settings:
        cmd.extend(["--load-settings", print_settings])

    if machine_settings:
        cmd.extend(["--load-filaments", machine_settings])

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
        if "display" in error_msg.lower() or "gtk" in error_msg.lower():
            return None, "Bambu Studio 需要图形界面，无法在无头模式下运行"
        if verbose:
            print(f"  [DEBUG] Error: {error_msg}")
        return None, error_msg

    if os.path.exists(output_3mf):
        return output_3mf, None
    else:
        for f in os.listdir(BAMBU_OUTPUT_DIR):
            if f.endswith(".3mf"):
                return os.path.join(BAMBU_OUTPUT_DIR, f), None

    return None, "切片完成但未生成输出文件（Bambu Studio 可能需要图形界面）"


def slice_with_orca(stl_paths, output_name, verbose=False):
    """使用 Orca Slicer 切片 STL 文件

    Args:
        stl_paths: STL 文件路径列表
        output_name: 输出文件名（不含扩展名）
        verbose: 是否输出详细信息

    Returns:
        (output_path, error): 成功时返回3MF路径和None，失败时返回None和错误信息
    """
    if not stl_paths:
        return None, "No STL files to slice"

    os.makedirs(ORCA_OUTPUT_DIR, exist_ok=True)

    output_3mf = os.path.join(ORCA_OUTPUT_DIR, f"{output_name}.3mf")

    cmd = [
        ORCA_SLICER_PATH,
        "--arrange", "1",
        "--load-settings", ORCA_MACHINE_PRESET,
        "--load-settings", ORCA_PROCESS_PRESET,
        "--load-filaments", ORCA_FILAMENT_PRESET,
        "--export-3mf", output_3mf,
    ]

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
        if "shader" in error_msg.lower() or "gl_" in error_msg.lower() or "display" in error_msg.lower():
            return None, "Orca Slicer 需要图形界面，无法在无头模式下运行。建议使用 -o 选项在 GUI 中打开 STL 文件。"
        if verbose:
            print(f"  [DEBUG] Error: {error_msg}")
        return None, error_msg

    if os.path.exists(output_3mf):
        return output_3mf, None
    else:
        for f in os.listdir(ORCA_OUTPUT_DIR):
            if f.endswith(".3mf"):
                return os.path.join(ORCA_OUTPUT_DIR, f), None

    return None, "切片完成但未生成输出文件（Orca Slicer 可能需要图形界面）"


def open_in_slicer(stl_paths, slicer="bambu"):
    """在切片器中打开 STL 文件

    Args:
        stl_paths: STL 文件路径列表
        slicer: 切片器类型 ("bambu" 或 "orca")

    Returns:
        (success, error): 成功时返回(True, None)，失败时返回(False, error)
    """
    if not stl_paths:
        return False, "No STL files provided"

    if slicer == "orca":
        cmd = [ORCA_SLICER_PATH] + list(stl_paths)
    else:
        cmd = [BAMBU_STUDIO_PATH] + list(stl_paths)

    try:
        subprocess.Popen(cmd)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='openGrid STL 生成和切片工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成 STL
  python3 scripts/slicer.py -g 7x5x3 10x5x3
  python3 scripts/slicer.py --generate 7x5x3

  # 切片 STL
  python3 scripts/slicer.py --slice file1.stl file2.stl --slicer orca
  python3 scripts/slicer.py -s file.stl --slicer bambu --output my_project

  # 在 slicer 中打开
  python3 scripts/slicer.py -o file.stl --slicer orca
        """
    )

    parser.add_argument('-g', '--generate', nargs='*', metavar='DIMENSION',
                        help='生成 STL，格式: WxHxS (如 7x5x3)')
    parser.add_argument('-s', '--slice', nargs='+', metavar='FILE',
                        help='切片 STL 文件')
    parser.add_argument('-o', '--open', nargs='+', metavar='FILE',
                        help='在 slicer 中打开 STL 文件')
    parser.add_argument('--slicer', type=str, default='bambu',
                        choices=['bambu', 'orca'], help='选择切片器')
    parser.add_argument('--output', '-O', type=str,
                        help='输出文件名（用于切片）')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('-f', '--force', action='store_true', help='强制重新生成')
    parser.add_argument('--print-settings', type=str,
                        help='Bambu Studio 打印设置文件')
    parser.add_argument('--machine-settings', type=str,
                        help='Bambu Studio 机器设置文件')

    args = parser.parse_args()

    if args.generate is None and args.slice is None and args.open is None:
        parser.print_help()
        return

    verbose = args.verbose
    force = args.force
    slicer = args.slicer

    # 处理生成请求
    if args.generate is not None:
        if not args.generate:
            print("警告: -g 需要至少一个维度参数（如 7x5x3）")
            return
        for dim in args.generate:
            # 解析维度: 支持 7x5x3 格式
            if 'x' in dim:
                parts = dim.split('x')
                if len(parts) == 3:
                    try:
                        w, h, s = map(int, parts)
                    except ValueError:
                        print(f"警告: 忽略无效格式 '{dim}'，维度必须是整数")
                        continue
                else:
                    print(f"警告: 忽略无效格式 '{dim}'，期望 WxHxS")
                    continue
            else:
                # 无效格式，跳过
                print(f"警告: 忽略无效格式 '{dim}'，期望 WxHxS")
                continue

            print(f"生成: {w}x{h}, {s} stacks")
            path, err = generate_stl(w, h, s, verbose, force)
            if err and err != "exists":
                print(f"  失败: {err}")
            elif err == "exists":
                print(f"  已存在（跳过）")
            else:
                print(f"  完成: {path}")

    # 处理切片请求
    if args.slice:
        output_name = args.output or "opengrid_output"
        print(f"切片: {len(args.slice)} 个文件 -> {output_name}")

        if slicer == "orca":
            result, err = slice_with_orca(args.slice, output_name, verbose)
        else:
            result, err = slice_with_bambu(
                args.slice, output_name,
                args.print_settings, args.machine_settings, verbose
            )

        if err:
            print(f"切片失败: {err}")
        else:
            print(f"切片完成: {result}")

    # 处理打开请求
    if args.open:
        print(f"在 {slicer} 中打开 {len(args.open)} 个文件")
        success, err = open_in_slicer(args.open, slicer)
        if success:
            print("已打开")
        else:
            print(f"打开失败: {err}")


if __name__ == "__main__":
    main()
