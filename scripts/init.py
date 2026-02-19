#!/usr/bin/env python3
"""交互式初始化脚本"""

import os
import sys
import yaml
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.config import DEFAULTS, PRINTER_PRESETS, get_config_path


def print_welcome():
    """打印欢迎信息"""
    print("=" * 50)
    print("欢迎使用 opengrid-drawer-filler")
    print("=" * 50)
    print()
    print("计算抽屉最优瓦片分割方案并生成 STL 文件")
    print()


def explain_setup():
    """介绍 setup.sh 操作"""
    print("【setup.sh 介绍】")
    print("-" * 50)
    print("在开始之前，需要安装以下软件：")
    print()
    print("1) 安装 OpenSCAD@snapshot")
    print("   - 通过 Homebrew Cask 安装最新开发版")
    print("   - OpenSCAD 用于生成 3D 模型")
    print()
    print("2) 克隆 QuackWorks 源码")
    print("   - GitHub: https://github.com/AndyLevesque/QuackWorks")
    print("   - 存放位置: vendor/QuackWorks/")
    print("   - 提供 openGrid 库")
    print()
    print("3) 安装 BOSL2 库")
    print("   - OpenSCAD 必装库")
    print("   - 存放位置: ~/Library/Application Support/")
    print("               OpenSCAD/libraries/BOSL2")
    print()


def ask_continue():
    """询问用户是否继续"""
    while True:
        response = input("\n是否继续安装？(Y/n): ").strip().lower()
        if response in ("", "y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        print("请输入 Y 或 n")


def explain_config():
    """介绍 config.yaml 配置项"""
    print("\n【config.yaml 配置说明】")
    print("-" * 50)
    print()
    print("1) output.stl_dir")
    print("   含义: STL 文件输出目录")
    print("   示例: ~/3D打印/opengrid/")
    print()
    print("2) printer.model")
    print("   含义: 打印机型号")
    print("   选项: a1_mini, a1, p1p, p1s, x1c, x1e, h2d, custom")
    print()
    print("3) printer.custom")
    print("   含义: 自定义打印机参数（当 model=custom 时）")
    print("   参数: bed_x, bed_y, max_z")
    print()
    print("4) opengrid.tile_type")
    print("   含义: 瓦片类型")
    print("   选项: Full (6.8mm), Lite (4.0mm), Heavy (13.8mm)")
    print()
    print("5) opengrid.stacking_method")
    print("   含义: 堆叠方式")
    print("   选项: Ironing (熨平), Interface Layer (界面层)")
    print()
    print("6) opengrid.interface_separation")
    print("   含义: 界面层间隙（mm）")
    print("   默认: 0.2")
    print()


def collect_config():
    """收集用户配置"""
    config = {"initialized": True}

    # 1. output.stl_dir
    print("\n【输出目录】")
    default_dir = DEFAULTS["output"]["stl_dir"]
    response = input(f"STL 输出目录 (默认: {default_dir}): ").strip()
    config["output"] = {"stl_dir": response or default_dir}

    # 2. printer.model
    print("\n【打印机型号】")
    print("可选型号:")
    for model in PRINTER_PRESETS:
        info = PRINTER_PRESETS[model]
        print(f"  - {model}: {info['bed_x']}x{info['bed_y']}x{info['max_z']}")
    print("  - custom: 自定义尺寸")
    default_model = DEFAULTS["printer"]["model"]
    response = input(f"选择打印机 (默认: {default_model}): ").strip().lower()
    model = response or default_model
    config["printer"] = {"model": model}

    if model == "custom":
        print("\n【自定义打印机参数】")
        bed_x = input("bed_x (mm): ").strip()
        bed_y = input("bed_y (mm): ").strip()
        max_z = input("max_z (mm): ").strip()
        config["printer"]["custom"] = {
            "bed_x": int(bed_x) if bed_x else 256,
            "bed_y": int(bed_y) if bed_y else 256,
            "max_z": int(max_z) if max_z else 256,
        }

    # 3. opengrid.tile_type
    print("\n【瓦片类型】")
    print("  - Full: 6.8mm 厚度")
    print("  - Lite: 4.0mm 厚度")
    print("  - Heavy: 13.8mm 厚度")
    default_type = DEFAULTS["opengrid"]["tile_type"]
    response = input(f"选择瓦片类型 (默认: {default_type}): ").strip()
    config["opengrid"] = {"tile_type": response or default_type}

    # 4. opengrid.stacking_method
    print("\n【堆叠方式】")
    print("  - Ironing: 熨平")
    print("  - Interface Layer: 界面层")
    default_method = DEFAULTS["opengrid"]["stacking_method"]
    response = input(f"选择堆叠方式 (默认: {default_method}): ").strip()
    if not response:
        response = default_method
    config["opengrid"]["stacking_method"] = response

    # 5. interface_separation
    default_sep = DEFAULTS["opengrid"]["interface_separation"]
    response = input(f"界面层间隙 mm (默认: {default_sep}): ").strip()
    config["opengrid"]["interface_separation"] = float(response) if response else default_sep

    return config


def save_config(config):
    """保存配置到 config.yaml"""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    print(f"\n配置已保存到: {config_path}")


def main():
    """主函数"""
    print_welcome()
    explain_setup()

    if not ask_continue():
        print("\n初始化已取消。")
        return

    explain_config()
    config = collect_config()
    save_config(config)

    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
