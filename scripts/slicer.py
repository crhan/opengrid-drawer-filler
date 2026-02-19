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
ORCA_MACHINE_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/machine/Bambu Lab P1P 0.4 nozzle.json"
ORCA_PROCESS_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/process/0.20mm Standard @BBL P1P.json"
ORCA_FILAMENT_PRESET = "/Applications/OrcaSlicer.app/Contents/Resources/profiles/BBL/filament/P1P/Bambu PLA Basic @BBL P1P.json"


def get_max_stacks():
    """计算最大stack数量"""
    return int(MAX_Z // FULL_THICKNESS)


def main():
    parser = argparse.ArgumentParser(description='openGrid STL 生成和切片工具')
    args = parser.parse_args()
    print("slicer.py 已创建")


if __name__ == "__main__":
    main()
