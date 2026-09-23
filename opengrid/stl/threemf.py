"""把 STL 打包成带打印预设的 BambuStudio 项目 3MF（未切片），纯 Python，不需要切片软件

3MF = zip + XML。打包内容照 BambuStudio 2.x 自己导出的单盘项目：
- 3D/Objects/object_1.model    网格（顶点平移到包围盒中心，BambuStudio 导入 STL 时也是这么做的）
- 3D/3dmodel.model             组件引用 + build item（transform 把物体放到盘面上）
- Metadata/model_settings.config  物体名 / 挤出机 / 盘面归属
- Metadata/project_settings.config 打印机 + 工艺 + 耗材预设（来自模板，只改擦料塔位置）

模板 templates/h2d_pla_support.project_settings.config 取自 2026-02-20 实际打印成功的
"老妈抽屉"项目（ha-bambulab 缓存的 10133794-opengrid_老妈抽屉_plate_2.gcode.3mf）：
H2D 0.4 + Opengrid堆叠打印 + [Bambu PLA Basic, Bambu Support For PLA/PETG]，
支撑接触面用 2 号专用支撑材料（跟 PLA 不粘，堆叠层能掰开）。
"""
from __future__ import annotations

import json
import struct
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_SETTINGS = _TEMPLATE_DIR / "h2d_pla_support.project_settings.config"
# 模板对应 opengrid_config.yaml 里的 printer.model
TEMPLATE_PRINTER = "h2d"

# 模板 project_settings 的版本；3dmodel.model 的 Application 必须跟它一致，
# BambuStudio 按这个判断配置格式（数组形状随版本变）
_APP_VERSION = "02.05.00.66"

# 物体离可打印区域边缘、擦料塔离物体的间距 (mm)
_MARGIN = 5
_TOWER_GAP = 10
# 擦料塔占地估算：宽度来自 prime_tower_width，深度随打印高度和换料量变，
# 堆叠瓦片换料少，按 60mm 方块保守估
_TOWER_DEPTH = 60


@dataclass
class Mesh:
    vertices: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]]

    def bbox(self):
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def read_stl(path: Path) -> Mesh:
    """读 ASCII / 二进制 STL，按坐标去重顶点"""
    data = Path(path).read_bytes()
    index: dict[tuple[float, float, float], int] = {}
    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []

    def vid(v):
        i = index.get(v)
        if i is None:
            i = index[v] = len(vertices)
            vertices.append(v)
        return i

    # 二进制 STL 的头部也可能以 "solid" 开头，用长度校验区分
    is_binary = len(data) >= 84 and len(data) == 84 + 50 * struct.unpack_from("<I", data, 80)[0]
    if is_binary:
        count = struct.unpack_from("<I", data, 80)[0]
        for n in range(count):
            f = struct.unpack_from("<12f", data, 84 + 50 * n)
            triangles.append(tuple(vid(tuple(f[3 + 3 * k: 6 + 3 * k])) for k in range(3)))
    else:
        tri = []
        for line in data.decode("ascii", errors="replace").splitlines():
            parts = line.split()
            if parts and parts[0] == "vertex":
                tri.append(vid((float(parts[1]), float(parts[2]), float(parts[3]))))
                if len(tri) == 3:
                    triangles.append(tuple(tri))
                    tri = []
    if not triangles:
        raise ValueError(f"STL 里没有三角面: {path}")
    return Mesh(vertices, triangles)


def _fmt(x: float) -> str:
    return f"{x:.9g}"


def _rect_overlap(a, b) -> bool:
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a, b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _usable_area(settings: dict) -> tuple[float, float, float, float]:
    """两个喷嘴都能打到的区域（H2D: x 25~325）；单喷嘴机型退化为 printable_area"""
    def rect(points):
        pts = [tuple(map(float, p.split("x"))) for p in points]
        xs, ys = zip(*pts)
        return min(xs), min(ys), max(xs), max(ys)

    areas = [rect(a.split(",")) for a in settings.get("extruder_printable_area", [])] \
        or [rect(settings["printable_area"])]
    return (max(a[0] for a in areas), max(a[1] for a in areas),
            min(a[2] for a in areas), min(a[3] for a in areas))


def plan_layout(size_x: float, size_y: float, settings: dict):
    """物体放公共区域左下角，擦料塔放右边或上边的空位。

    Returns:
        (object_center_xy, tower_xy_or_None, warnings)
    """
    ux0, uy0, ux1, uy1 = _usable_area(settings)
    warnings = []
    if size_x > ux1 - ux0 or size_y > uy1 - uy0:
        warnings.append(f"物体 {size_x:.0f}×{size_y:.0f}mm 超出双喷嘴公共区域 "
                        f"{ux1 - ux0:.0f}×{uy1 - uy0:.0f}mm")
    ox0, oy0 = ux0 + _MARGIN, uy0 + _MARGIN
    obj = (ox0, oy0, ox0 + size_x, oy0 + size_y)
    center = (ox0 + size_x / 2, oy0 + size_y / 2)

    if settings.get("enable_prime_tower") != "1":
        return center, None, warnings

    tw = float(settings.get("prime_tower_width", 60))
    candidates = [
        (obj[2] + _TOWER_GAP, oy0),           # 物体右侧
        (ox0, obj[3] + _TOWER_GAP),           # 物体上方
        (obj[2] + _TOWER_GAP, obj[3] - _TOWER_DEPTH),
    ]
    for tx, ty in candidates:
        tower = (tx, ty, tx + tw, ty + _TOWER_DEPTH)
        inside = tower[0] >= ux0 and tower[1] >= uy0 and tower[2] <= ux1 and tower[3] <= uy1
        if inside and not _rect_overlap(tower, obj):
            return center, (tx, ty), warnings
    warnings.append("盘面放不下擦料塔（物体太大），在 BambuStudio 里手动挪一下擦料塔或关掉它")
    return center, None, warnings


def _model_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
    )


def _object_model(mesh: Mesh, offset) -> str:
    ox, oy, oz = offset
    out = [_model_xml(),
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n',
           f'  <object id="1" p:UUID="00010000-{uuid.uuid4().hex[8:12]}-4c03-9d28-{uuid.uuid4().hex[:12]}" type="model">\n',
           '   <mesh>\n    <vertices>\n']
    out += [f'     <vertex x="{_fmt(x - ox)}" y="{_fmt(y - oy)}" z="{_fmt(z - oz)}"/>\n' for x, y, z in mesh.vertices]
    out.append('    </vertices>\n    <triangles>\n')
    out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in mesh.triangles]
    out.append('    </triangles>\n   </mesh>\n  </object>\n </resources>\n <build/>\n</model>\n')
    return "".join(out)


def _root_model(title: str, transform: str) -> str:
    today = date.today().isoformat()
    meta = {
        "Application": f"BambuStudio-{_APP_VERSION}",
        "BambuStudio:3mfVersion": "1",
        "CreationDate": today,
        "ModificationDate": today,
        "Title": title,
    }
    lines = [_model_xml()]
    lines += [f' <metadata name="{k}">{v}</metadata>\n' for k, v in meta.items()]
    lines.append(
        ' <resources>\n'
        f'  <object id="2" p:UUID="00000001-{uuid.uuid4().hex[:4]}-4c03-9d28-{uuid.uuid4().hex[:12]}" type="model">\n'
        '   <components>\n'
        f'    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="00010000-{uuid.uuid4().hex[:4]}-40ff-9872-{uuid.uuid4().hex[:12]}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>\n'
        '   </components>\n  </object>\n </resources>\n'
        f' <build p:UUID="{uuid.uuid4()}">\n'
        f'  <item objectid="2" p:UUID="00000002-{uuid.uuid4().hex[:4]}-4553-aec9-{uuid.uuid4().hex[:12]}" transform="{transform}" printable="1"/>\n'
        ' </build>\n</model>\n'
    )
    return "".join(lines)


def _model_settings(name: str, face_count: int, half_z: float) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="{name}"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{face_count}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="{name}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="{name}"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="0"/>
      <metadata key="source_offset_y" value="0"/>
      <metadata key="source_offset_z" value="{_fmt(half_z)}"/>
      <mesh_stat face_count="{face_count}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Flush"/>
    <metadata key="filament_maps" value="2 1"/>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="78"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="2" instance_id="0" transform="1 0 0 0 1 0 0 0 1 0 0 {_fmt(half_z)}" offset="0 0 0" />
  </assemble>
</config>
'''


_CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
</Types>'''

_ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''

_MODEL_RELS = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''


def build_3mf(stl_path: Path, out_path: Path, settings_path: Path = DEFAULT_SETTINGS) -> list[str]:
    """STL → 单盘 BambuStudio 项目 3MF（原子写入）

    Returns:
        警告列表（放不下擦料塔、超出公共区域、超高等），空表示一切正常

    Raises:
        ValueError: STL 为空 / 物体高于打印机 Z 轴
    """
    stl_path, out_path = Path(stl_path), Path(out_path)
    settings = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    mesh = read_stl(stl_path)
    (x0, y0, z0), (x1, y1, z1) = mesh.bbox()
    size_x, size_y, size_z = x1 - x0, y1 - y0, z1 - z0

    max_z = float(settings.get("printable_height", 0) or 0)
    if max_z and size_z > max_z:
        raise ValueError(f"{stl_path.name} 高 {size_z:.1f}mm，超出打印机 Z 轴 {max_z:.0f}mm")

    (cx, cy), tower, warnings = plan_layout(size_x, size_y, settings)
    if tower:
        settings["wipe_tower_x"] = [_fmt(tower[0])]
        settings["wipe_tower_y"] = [_fmt(tower[1])]

    center = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    half_z = size_z / 2
    name = stl_path.name
    transform = f"1 0 0 0 1 0 0 0 1 {_fmt(cx)} {_fmt(cy)} {_fmt(half_z)}"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("3D/3dmodel.model", _root_model(out_path.stem, transform))
        z.writestr("3D/_rels/3dmodel.model.rels", _MODEL_RELS)
        z.writestr("3D/Objects/object_1.model", _object_model(mesh, center))
        z.writestr("Metadata/model_settings.config", _model_settings(name, len(mesh.triangles), half_z))
        z.writestr("Metadata/project_settings.config", json.dumps(settings, indent=4, ensure_ascii=False))
        z.writestr("Metadata/filament_sequence.json", json.dumps({"plate_1": {"sequence": []}}))
    tmp.replace(out_path)
    return warnings
