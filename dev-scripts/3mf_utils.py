#!/usr/bin/env python3
"""
3MF 操作工具 - 用于从模板 3MF 加载预设并生成新的 3MF 项目

用法:
    python3 3mf_utils.py extract-presets <input.3mf> <output_dir>
    python3 3mf_utils.py create-project <template.3mf> <stl_files...> <output.3mf>
"""

import zipfile
import json
import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional


def extract_presets(threeMF_path: str, output_dir: str) -> Dict[str, Any]:
    """
    从 3MF 文件中提取预设配置

    Args:
        threeMF_path: 输入 3MF 文件路径
        output_dir: 输出目录

    Returns:
        包含预设信息的字典
    """
    os.makedirs(output_dir, exist_ok=True)

    presets = {
        "print_settings": None,
        "filament_settings": [],
        "machine_settings": None,
        "printer_model": None
    }

    with zipfile.ZipFile(threeMF_path, 'r') as zf:
        # 读取 project_settings.config
        if 'Metadata/project_settings.config' in zf.namelist():
            content = zf.read('Metadata/project_settings.config').decode('utf-8')
            settings = json.loads(content)

            # 保存完整设置
            settings_path = os.path.join(output_dir, 'project_settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)

            # 提取关键信息
            presets["print_settings"] = settings.get("print_settings_id")
            presets["printer_model"] = settings.get("printer_model")

            # 提取耗材设置
            filament_ids = settings.get("filament_settings_id", [])
            for i, fid in enumerate(filament_ids):
                if fid:
                    presets["filament_settings"].append(fid)

            print(f"已提取打印设置: {presets['print_settings']}")
            print(f"已提取打印机: {presets['printer_model']}")

    # 保存预设摘要
    summary_path = os.path.join(output_dir, 'presets_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(presets, f, indent=2)

    return presets


def create_project_from_template(
    template_3mf: str,
    stl_files: List[str],
    output_3mf: str,
    openscad_path: str = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    arrange: bool = True
) -> bool:
    """
    从模板 3MF 创建新项目（使用 OpenSCAD 转换 STL 并替换模型）

    工作流程：
    1. 使用 OpenSCAD 将 STL 转换为 3MF
    2. 解压模板 3MF
    3. 从 OpenSCAD 的 3MF 提取网格数据，创建 Objects/object_*.model
    4. 更新 3dmodel.model 中的引用
    5. 重新打包为 3MF

    Args:
        template_3mf: 模板 3MF 文件
        stl_files: STL 文件列表
        output_3mf: 输出 3MF 文件
        openscad_path: OpenSCAD 可执行文件路径
        arrange: 是否自动排列（暂未实现）

    Returns:
        是否成功
    """
    import subprocess
    import xml.etree.ElementTree as ET
    from uuid import uuid4

    def _strip_namespace(elem):
        """去除 XML 元素的命名空间前缀，转换为默认命名空间格式"""
        # 处理根元素的标签（去掉前缀）
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}')[1]

        # 处理根元素的属性 - 设置默认命名空间
        ns_uri = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        prod_ns_uri = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
        bambustudio_ns = 'http://schemas.bambulab.com/package/2021'

        # 收集需要保留的属性（p:UUID, p:path 等带命名空间的属性）
        preserved_attrs = {}
        attrs_to_remove = []
        for k, v in elem.attrib.items():
            if k.startswith('{http://schemas.microsoft.com/3dmanufacturing/production'):
                # 转换为 p:xxx 格式
                local_name = k.split('}')[1]
                preserved_attrs[f'p:{local_name}'] = v
                attrs_to_remove.append(k)
            elif k.startswith('{'):
                attrs_to_remove.append(k)

        # 移除旧的 xmlns:* 声明
        for attr in attrs_to_remove:
            del elem.attrib[attr]

        # 恢复保留的属性（现在用 p: 前缀）
        for k, v in preserved_attrs.items():
            elem.set(k, v)

        # 设置默认命名空间和其他命名空间（但不带前缀）
        elem.set('xmlns', ns_uri)
        elem.set('xmlns:p', prod_ns_uri)

        # 检查是否有 BambuStudio 命名空间需要保留
        has_bambustudio = False
        for attr in list(elem.attrib.keys()):
            if 'BambuStudio' in attr:
                has_bambustudio = True
                break
        if has_bambustudio:
            elem.set('xmlns:BambuStudio', bambustudio_ns)

        # 递归处理所有子元素 - 只去除标签前缀，不添加 xmlns 属性
        for child in elem:
            _strip_namespace_recursive(child)

        return elem

    def _strip_namespace_recursive(elem):
        """递归去除子元素的命名空间前缀"""
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}')[1]

        # 收集需要保留的属性（p:UUID, p:path 等带命名空间的属性）
        preserved_attrs = {}
        attrs_to_remove = []
        for k, v in elem.attrib.items():
            if k.startswith('{http://schemas.microsoft.com/3dmanufacturing/production'):
                # 转换为 p:xxx 格式
                local_name = k.split('}')[1]
                preserved_attrs[f'p:{local_name}'] = v
                attrs_to_remove.append(k)
            elif k.startswith('{'):
                attrs_to_remove.append(k)

        # 移除旧的 xmlns:* 声明
        for attr in attrs_to_remove:
            del elem.attrib[attr]

        # 恢复保留的属性
        for k, v in preserved_attrs.items():
            elem.set(k, v)

        for child in elem:
            _strip_namespace_recursive(child)

    def _copy_element_recursive(src, dst):
        """递归复制 XML 元素，去除命名空间前缀"""
        for child in src:
            if hasattr(child, 'tag') and child.tag:
                # 去掉前缀
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                new_child = ET.SubElement(dst, tag)
                # 复制属性
                for key, value in child.attrib.items():
                    attr_key = key.split('}')[-1] if '}' in key else key
                    new_child.set(attr_key, value)
                # 递归复制子元素
                _copy_element_recursive(child, new_child)

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = tmpdir

        # 步骤 1: 将每个 STL 转换为 3MF，并提取网格数据
        stl_models = []  # 每个 STL 对应的网格 XML 数据

        for i, stl_file in enumerate(stl_files):
            print(f"转换 {stl_file}...")

            # 创建临时 SCAD 文件
            scad_file = os.path.join(work_dir, f"temp_{i}.scad")
            with open(scad_file, 'w') as f:
                f.write(f'import("{stl_file}");')

            # 使用 OpenSCAD 导出 3MF
            output_3mf_temp = os.path.join(work_dir, f"model_{i}.3mf")
            cmd = [
                openscad_path,
                "-o", output_3mf_temp,
                scad_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"错误: OpenSCAD 转换失败: {result.stderr}")
                return False

            # 从 3MF 中提取网格数据
            with zipfile.ZipFile(output_3mf_temp, 'r') as zf:
                content = zf.read('3D/3dmodel.model').decode('utf-8')
                stl_models.append(content)

            print(f"  -> 已转换为 3MF")

        # 步骤 2: 解压模板 3MF
        template_dir = os.path.join(work_dir, 'template')
        os.makedirs(template_dir)

        with zipfile.ZipFile(template_3mf, 'r') as zf:
            zf.extractall(template_dir)

        # 步骤 3: 读取模板的 3dmodel.model，替换对象
        template_model_file = os.path.join(template_dir, '3D', '3dmodel.model')
        with open(template_model_file, 'r') as f:
            template_content = f.read()

        # 解析 XML - 使用默认命名空间（无前缀）方式解析
        # 3MF 使用默认命名空间，子元素不带前缀
        ns = {
            'core': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02',
            'p': 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
        }

        # 解析模板内容
        root = ET.fromstring(template_content)

        # 获取 resources 和 build 元素
        resources = root.find('core:resources', ns)
        if resources is None:
            resources = root.find('resources')

        build = root.find('core:build', ns)
        if build is None:
            build = root.find('build')

        # 获取 Objects 目录
        objects_dir = os.path.join(template_dir, '3D', 'Objects')

        # 删除旧的 Objects 文件
        if os.path.exists(objects_dir):
            for f in os.listdir(objects_dir):
                if f.endswith('.model'):
                    os.remove(os.path.join(objects_dir, f))
                    print(f"  删除旧对象: {f}")

        # 为每个 STL 替换对象
        # 模板中有 4 个对象，我们按顺序替换
        template_objects = resources.findall('.//core:object', ns)
        if not template_objects:
            template_objects = resources.findall('.//object')

        print(f"模板中有 {len(template_objects)} 个对象，准备替换为 {len(stl_models)} 个 STL")

        # 替换对象
        for i, stl_mesh_xml in enumerate(stl_models):
            if i >= len(template_objects):
                break

            obj = template_objects[i]
            obj_id = obj.get('id')

            # 解析 STL 的网格数据
            stl_root = ET.fromstring(stl_mesh_xml)
            stl_resources = stl_root.find('core:resources', ns)
            if stl_resources is None:
                stl_resources = stl_root.find('resources')

            stl_object = stl_resources.find('core:object', ns)
            if stl_object is None:
                stl_object = stl_resources.find('object')

            # 获取网格数据 - 需要去除命名空间前缀
            mesh = stl_object.find('core:mesh', ns)
            if mesh is None:
                mesh = stl_object.find('mesh')

            # 创建新的 object_*.model 文件
            obj_file = os.path.join(objects_dir, f'object_{i+1}.model')

            # 构建新的 object XML - 使用默认命名空间（无前缀）
            new_obj_root = ET.Element('model')
            new_obj_root.set('unit', 'millimeter')
            new_obj_root.set('xml:lang', 'en-US')
            new_obj_root.set('xmlns', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')
            new_obj_root.set('xmlns:p', 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06')

            new_resources = ET.SubElement(new_obj_root, 'resources')
            new_object = ET.SubElement(new_resources, 'object')
            new_object.set('id', '1')
            new_object.set('type', 'model')
            new_object.set('p:UUID', str(uuid4()))

            # 复制网格数据 - 去除命名空间前缀
            new_mesh = ET.SubElement(new_object, 'mesh')
            for child in mesh:
                # 去除命名空间前缀，复制子元素
                if hasattr(child, 'tag') and child.tag:
                    # 去掉前缀
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    new_child = ET.SubElement(new_mesh, tag)
                    # 复制属性
                    for key, value in child.attrib.items():
                        attr_key = key.split('}')[-1] if '}' in key else key
                        new_child.set(attr_key, value)
                    # 递归复制子元素
                    _copy_element_recursive(child, new_child)

            # 保存 object 文件
            tree = ET.ElementTree(new_obj_root)
            tree.write(obj_file, encoding='utf-8', xml_declaration=True)

            # 更新 3dmodel.model 中的引用
            # 找到对应的 component 并更新 path
            components = obj.findall('.//core:component', ns)
            if not components:
                components = obj.findall('.//component')

            for comp in components:
                comp.set('{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path',
                         f'/3D/Objects/object_{i+1}.model')
                comp.set('objectid', '1')

            print(f"  创建对象: object_{i+1}.model")

        # 删除多余的对象（如果有）
        for i in range(len(stl_models), len(template_objects)):
            obj = template_objects[i]
            obj_id = obj.get('id')
            # 从 build 中移除
            items = build.findall('.//core:item', ns)
            if not items:
                items = build.findall('.//item')
            for item in items:
                if item.get('objectid') == obj_id:
                    build.remove(item)
            # 从 resources 中移除
            resources.remove(obj)
            print(f"  删除对象 id={obj_id}")

        # 保存更新后的 3dmodel.model - 先去除命名空间前缀
        root = _strip_namespace(root)
        tree = ET.ElementTree(root)
        tree.write(template_model_file, encoding='utf-8', xml_declaration=True)

        # 更新 3D/_rels/3dmodel.model.rels 文件，只保留存在的 object_*.model 引用
        rels_file = os.path.join(template_dir, '3D', '_rels', '3dmodel.model.rels')
        if os.path.exists(rels_file):
            with open(rels_file, 'r') as f:
                rels_content = f.read()
            rels_root = ET.fromstring(rels_content)

            # 收集需要保留的 relationship
            new_relationships = []
            for rel in rels_root:
                target = rel.get('Target', '')
                # 只保留我们新创建的文件
                if target.startswith('/3D/Objects/object_'):
                    obj_num = target.split('_')[1].split('.')[0]
                    if int(obj_num) <= len(stl_models):
                        new_relationships.append(rel)

            # 清空并重新添加 - 使用纯 XML 字符串方式避免命名空间前缀问题
            rels_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
            rels_lines.append('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">')
            for i, rel in enumerate(new_relationships):
                target = rel.get('Target', '')
                rel_type = rel.get('Type', 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
                rels_lines.append(f' <Relationship Target="{target}" Id="rel-{i+1}" Type="{rel_type}"/>')
            rels_lines.append('</Relationships>')

            # 写入更新后的rels文件
            with open(rels_file, 'w') as f:
                f.write('\n'.join(rels_lines))
            print(f"  更新了 3dmodel.model.rels，保留 {len(new_relationships)} 个对象引用")

        # 步骤 4: 重新打包为 3MF
        os.makedirs(os.path.dirname(output_3mf) if os.path.dirname(output_3mf) else '.', exist_ok=True)

        with zipfile.ZipFile(output_3mf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, dirs, files in os.walk(template_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, template_dir)
                    zf.write(file_path, arcname)

        print(f"\n已创建项目: {output_3mf}")
        print("预设已保留，模型已替换")

    return True


def list_3mf_contents(threeMF_path: str) -> None:
    """列出 3MF 文件内容"""
    with zipfile.ZipFile(threeMF_path, 'r') as zf:
        print(f"\n=== {threeMF_path} ===")
        print("文件列表:")
        for name in sorted(zf.namelist()):
            info = zf.getinfo(name)
            print(f"  {name}: {info.file_size} bytes")


def find_available_presets() -> Dict[str, List[str]]:
    """查找系统中可用的预设"""
    presets = {
        "machines": [],
        "processes": [],
        "filaments": []
    }

    # OrcaSlicer 预设路径
    orca_paths = [
        "/Applications/OrcaSlicer.app/Contents/Resources/profiles"
    ]

    # BambuStudio 预设路径
    bambu_paths = [
        "/Applications/BambuStudio.app/Contents/Resources/profiles"
    ]

    for base_path in orca_paths + bambu_paths:
        if not os.path.exists(base_path):
            continue

        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), base_path)

                    if '/machine/' in rel_path:
                        presets["machines"].append(rel_path)
                    elif '/process/' in rel_path:
                        presets["processes"].append(rel_path)
                    elif '/filament/' in rel_path:
                        presets["filaments"].append(rel_path)

    return presets


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "extract-presets":
        if len(sys.argv) < 4:
            print("用法: python3 3mf_utils.py extract-presets <input.3mf> <output_dir>")
            sys.exit(1)
        extract_presets(sys.argv[2], sys.argv[3])

    elif command == "list":
        if len(sys.argv) < 3:
            print("用法: python3 3mf_utils.py list <3mf_file>")
            sys.exit(1)
        list_3mf_contents(sys.argv[2])

    elif command == "presets":
        presets = find_available_presets()
        print("\n=== 可用预设 ===")
        print(f"机器: {len(presets['machines'])} 个")
        print(f"工艺: {len(presets['processes'])} 个")
        print(f"耗材: {len(presets['filaments'])} 个")

        print("\n机器预设示例:")
        for m in presets['machines'][:5]:
            print(f"  {m}")

    elif command == "create-project":
        if len(sys.argv) < 5:
            print("用法: python3 3mf_utils.py create-project <template.3mf> <stl1> <stl2> ... <output.3mf>")
            print("示例: python3 3mf_utils.py create-project template.3mf model1.stl model2.stl output.3mf")
            sys.exit(1)
        template = sys.argv[2]
        output = sys.argv[-1]
        stls = sys.argv[3:-1]

        # 检查 OpenSCAD
        openscad_path = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
        if not os.path.exists(openscad_path):
            # 尝试其他路径
            for path in [
                "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
                "/usr/local/bin/openscad",
                "openscad"
            ]:
                if os.path.exists(path) or path == "openscad":
                    openscad_path = path
                    break

        create_project_from_template(template, stls, output, openscad_path)

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
