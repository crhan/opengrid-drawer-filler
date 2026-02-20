#!/usr/bin/env python3
"""STL 生成与链接模块"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from slicer import generate_all_stls


def generate_and_link_stls(scheme, project_path, copies=1, verbose=False, force=False):
    """生成 STL 并链接到项目目录

    1. 调用 slicer.py 生成 STL 到 stl_base_dir
    2. 在 project_path/stl/ 创建软链接指向生成的 STL
    """
    config = load_config()
    stl_base_dir = Path(config["output"]["stl_dir"]).expanduser()

    # 确保输出目录存在
    stl_base_dir.mkdir(parents=True, exist_ok=True)

    # 生成 STL
    stl_files = generate_all_stls(scheme, copies=copies, verbose=verbose, force=force)

    # 创建软链接
    stl_link_dir = project_path / "stl"
    linked_files = []

    for src in stl_files:
        src_path = Path(src)
        link_path = stl_link_dir / src_path.name

        if not link_path.exists():
            try:
                os.symlink(src, link_path)
            except OSError:
                # 如果已经存在同名文件，跳过
                pass

        linked_files.append(str(link_path))

    return linked_files
