"""STL → BambuStudio 项目 3MF 打包"""
import json
import struct
import zipfile
import xml.etree.ElementTree as ET

import pytest

from opengrid.stl.threemf import DEFAULT_SETTINGS, build_3mf, plan_layout, read_stl

# 一个 112×280×14mm 的长方体（4x10 格、2 层堆叠的外包尺寸），12 个三角面
_BOX = (112.0, 280.0, 14.0)


def _box_triangles(sx, sy, sz, x0=-56.0, y0=-140.0, z0=0.0):
    p = [(x0 + dx * sx, y0 + dy * sy, z0 + dz * sz) for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return [[p[i] for i in f] for f in faces]


def _write_ascii(path, tris):
    lines = ["solid t"]
    for t in tris:
        lines += ["facet normal 0 0 0", "outer loop"] + [f"vertex {x} {y} {z}" for x, y, z in t] + ["endloop", "endfacet"]
    path.write_text("\n".join(lines + ["endsolid t"]))


def _write_binary(path, tris):
    data = b"solid-looking header".ljust(80, b" ") + struct.pack("<I", len(tris))
    for t in tris:
        data += struct.pack("<12fH", 0, 0, 0, *[c for v in t for c in v], 0)
    path.write_bytes(data)


@pytest.mark.parametrize("writer", [_write_ascii, _write_binary])
def test_read_stl_dedups_vertices(tmp_path, writer):
    stl = tmp_path / "box.stl"
    writer(stl, _box_triangles(*_BOX))
    mesh = read_stl(stl)
    assert len(mesh.vertices) == 8
    assert len(mesh.triangles) == 12


def test_build_3mf_structure_and_settings(tmp_path):
    stl = tmp_path / "openGrid_Full_4x10x2.stl"
    _write_ascii(stl, _box_triangles(*_BOX))
    out = tmp_path / "out.3mf"
    warnings = build_3mf(stl, out)
    assert warnings == []

    z = zipfile.ZipFile(out)
    for name in z.namelist():
        if name.endswith((".model", ".rels", ".xml")) or name == "Metadata/model_settings.config":
            ET.fromstring(z.read(name))

    # 网格平移到包围盒中心：z -7~7
    obj = z.read("3D/Objects/object_1.model").decode()
    assert 'z="-7"' in obj and 'z="7"' in obj

    # build item 把物体抬回 z=7，且整块落在双喷嘴公共区域 x 25~325
    root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    t = [float(v) for v in root.find("m:build/m:item", ns).get("transform").split()]
    cx, cy, cz = t[9:12]
    assert cz == 7
    assert 25 <= cx - 56 and cx + 56 <= 325 and 0 <= cy - 140 and cy + 140 <= 320

    s = json.loads(z.read("Metadata/project_settings.config"))
    assert s["print_settings_id"] == "Opengrid堆叠打印"
    # 接触面必须是专用支撑材料，不能是 PLA Basic（否则堆叠层粘死）
    iface = s["filament_settings_id"][int(s["support_interface_filament"]) - 1]
    assert "Support" in iface
    # 擦料塔不能压在物体上
    tx, ty = float(s["wipe_tower_x"][0]), float(s["wipe_tower_y"][0])
    assert tx >= cx + 56 or ty >= cy + 140


def test_layout_warns_when_tower_does_not_fit():
    settings = json.loads(DEFAULT_SETTINGS.read_text(encoding="utf-8"))
    _, tower, warnings = plan_layout(280, 308, settings)  # 10x11 格
    assert tower is None
    assert any("擦料塔" in w for w in warnings)


def test_too_tall_is_error(tmp_path):
    stl = tmp_path / "tall.stl"
    _write_ascii(stl, _box_triangles(112, 280, 400))
    with pytest.raises(ValueError, match="Z 轴"):
        build_3mf(stl, tmp_path / "out.3mf")
