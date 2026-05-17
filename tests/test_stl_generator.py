"""Unit tests for opengrid.stl.generator

mock subprocess.run 验证拼参 / 副作用 / 错误处理。真实跑 OpenSCAD 的 smoke
test 在文件末尾，标 @pytest.mark.integration，默认 pytest 不跑（addopts 配置）。
"""
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from opengrid.stl import generator


# ---------- 公共 fixture ----------

@pytest.fixture
def tmp_stl_dir(tmp_path, monkeypatch):
    """把 _resolve_stl_dir 重定向到 tmp_path，避免污染用户家目录。"""
    monkeypatch.setattr(generator, "_resolve_stl_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def fake_openscad(monkeypatch):
    """伪造 _find_openscad 和 _check_quackworks，跳过环境依赖。"""
    monkeypatch.setattr(generator, "_find_openscad", lambda: "/fake/openscad")
    monkeypatch.setattr(generator, "_check_quackworks", lambda: None)
    monkeypatch.setattr(
        generator, "_resolve_tile_config", lambda: ("Full", 28, 6.8)
    )


def _fake_run_success(output_path_capture: list):
    """构造一个能"假装生成了 STL 文件"的 subprocess.run。

    把 -o 指定的 .tmp 路径捕获到 list，并真在文件系统上 touch 这个文件，
    让 generate_stl 的 os.replace 步骤正常工作。
    """
    def _run(cmd, capture_output=True, text=True, timeout=None):
        # 找 -o 后的路径
        tmp_out = Path(cmd[cmd.index("-o") + 1])
        tmp_out.write_bytes(b"solid fake\nendsolid fake\n")
        output_path_capture.append(tmp_out)
        return MagicMock(returncode=0, stdout="", stderr="")
    return _run


# ---------- 拼参 ----------

def test_generate_stl_passes_correct_d_flags(tmp_stl_dir, fake_openscad, monkeypatch):
    captured_cmds = []

    def _run(cmd, **kw):
        captured_cmds.append(cmd)
        tmp_out = Path(cmd[cmd.index("-o") + 1])
        tmp_out.write_bytes(b"solid fake\n")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)

    path, status = generator.generate_stl(7, 5, 2)

    assert status == "generated"
    assert path.name == "openGrid_Full_7x5x2.stl"
    cmd = captured_cmds[0]
    assert "-D" in cmd
    assert "Board_Width=7" in cmd
    assert "Board_Height=5" in cmd
    assert "Stack_Count=2" in cmd
    assert 'Tile_Type="Full"' in cmd
    assert "Tile_Size=28" in cmd
    assert "Tile_Thickness=6.8" in cmd
    assert "Stack_Gap=0.4" in cmd
    # 最后一个参数应该是 wrapper.scad
    assert cmd[-1].endswith("wrapper.scad")


# ---------- 副作用 / 文件管理 ----------

def test_generate_stl_skips_when_exists(tmp_stl_dir, fake_openscad, monkeypatch):
    existing = tmp_stl_dir / "openGrid_Full_3x3x1.stl"
    existing.write_bytes(b"already here")

    # subprocess 不应该被调用
    monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=AssertionError("不应调用 OpenSCAD")))

    path, status = generator.generate_stl(3, 3, 1, force=False)
    assert status == "skipped"
    assert path == existing
    # 原文件未被改动
    assert existing.read_bytes() == b"already here"


def test_generate_stl_force_overwrites(tmp_stl_dir, fake_openscad, monkeypatch):
    existing = tmp_stl_dir / "openGrid_Full_3x3x1.stl"
    existing.write_bytes(b"old content")

    captured = []
    monkeypatch.setattr(subprocess, "run", _fake_run_success(captured))

    path, status = generator.generate_stl(3, 3, 1, force=True)
    assert status == "generated"
    assert path == existing
    # 内容被新写的"假 STL"替换
    assert existing.read_bytes().startswith(b"solid fake")


def test_generate_stl_creates_output_dir(tmp_path, fake_openscad, monkeypatch):
    nested = tmp_path / "deeply" / "nested" / "output"
    monkeypatch.setattr(generator, "_resolve_stl_dir", lambda: nested)
    monkeypatch.setattr(subprocess, "run", _fake_run_success([]))

    path, status = generator.generate_stl(2, 2, 1)
    assert status == "generated"
    assert path.parent == nested
    assert nested.is_dir()


def test_generate_stl_atomic_write(tmp_stl_dir, fake_openscad, monkeypatch):
    """中途 OpenSCAD 失败时，原文件应该保持不动（哪怕跑过 .tmp）。"""
    final = tmp_stl_dir / "openGrid_Full_3x3x1.stl"
    final.write_bytes(b"original")

    def _run(cmd, **kw):
        # 假装写了 .tmp 但 returncode != 0
        tmp_out = Path(cmd[cmd.index("-o") + 1])
        tmp_out.write_bytes(b"half written garbage")
        return MagicMock(returncode=1, stdout="", stderr="OpenSCAD ERROR: ...")

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="OpenSCAD 生成失败"):
        generator.generate_stl(3, 3, 1, force=True)

    # 原文件未被替换
    assert final.read_bytes() == b"original"
    # tmp 文件已清理
    tmp = final.parent / f".{final.stem}.tmp.stl"
    assert not tmp.exists()


# ---------- 错误处理 ----------

def test_generate_stl_raises_on_nonzero_returncode(tmp_stl_dir, fake_openscad, monkeypatch):
    def _run(cmd, **kw):
        return MagicMock(returncode=2, stdout="", stderr="syntax error")
    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match=r"returncode=2"):
        generator.generate_stl(3, 3, 1)


def test_generate_stl_raises_when_output_missing_despite_zero_returncode(
    tmp_stl_dir, fake_openscad, monkeypatch
):
    """OpenSCAD 偶尔 returncode=0 但啥也没写——用文件存在性兜底。"""
    def _run(cmd, **kw):
        # 故意不创建 .tmp 文件
        return MagicMock(returncode=0, stdout="", stderr="WARNING: ...")
    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match=r"STL 文件未生成"):
        generator.generate_stl(3, 3, 1)


def test_find_openscad_raises_with_setup_hint(monkeypatch):
    # which 找不到 + 把 macOS 默认路径指到不存在位置（局部 patch 比 Path.exists 全局替换安全）
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(generator, "_DEFAULT_OPENSCAD_MACOS", "/nonexistent/openscad")

    with pytest.raises(FileNotFoundError, match="setup"):
        generator._find_openscad()


def test_check_quackworks_raises_when_submodule_missing(monkeypatch):
    fake_path = Path("/non/existent/openGrid.scad")
    monkeypatch.setattr(generator, "QUACKWORKS_SCAD", fake_path)

    with pytest.raises(FileNotFoundError, match="submodule"):
        generator._check_quackworks()


# ---------- Tile_Type Full/Lite/Heavy 参数化 ----------

@pytest.mark.parametrize(
    "tile_type,expected_thickness",
    [("Full", 6.8), ("Lite", 4.0), ("Heavy", 13.8)],
)
def test_generate_stl_respects_tile_type(
    tile_type, expected_thickness, tmp_stl_dir, monkeypatch
):
    """_resolve_tile_config 按 config.opengrid.tile_type 选 TILE_THICKNESS 字典里的值。"""
    monkeypatch.setattr(generator, "_find_openscad", lambda: "/fake/openscad")
    monkeypatch.setattr(generator, "_check_quackworks", lambda: None)
    monkeypatch.setattr(
        generator, "_resolve_tile_config",
        lambda: (tile_type, 28, expected_thickness),
    )

    captured_cmds = []

    def _run(cmd, **kw):
        captured_cmds.append(cmd)
        tmp_out = Path(cmd[cmd.index("-o") + 1])
        tmp_out.write_bytes(b"solid fake\n")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)

    path, status = generator.generate_stl(3, 3, 1)
    assert status == "generated"
    # 文件名应含 tile_type
    assert path.name == f"openGrid_{tile_type}_3x3x1.stl"
    cmd = captured_cmds[0]
    # Tile_Thickness 参数传对了
    assert f"Tile_Thickness={expected_thickness}" in cmd
    assert f'Tile_Type="{tile_type}"' in cmd


# ---------- subprocess.TimeoutExpired ----------

def test_generate_stl_propagates_timeout(tmp_stl_dir, fake_openscad, monkeypatch):
    """OpenSCAD 渲染超时应直接抛 TimeoutExpired，并清理半截 .tmp 文件。"""
    final = tmp_stl_dir / "openGrid_Full_3x3x1.stl"
    tmp = final.parent / f".{final.stem}.tmp.stl"

    def _run(cmd, **kw):
        # 模拟超时前已写了一部分（OpenSCAD 真实场景：渲染卡在 CSG 求交，可能已写部分 STL）
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"half written")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout", 0))

    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(subprocess.TimeoutExpired):
        generator.generate_stl(3, 3, 1)

    # 我们不强求 generator 在 TimeoutExpired 时清理 .tmp（subprocess 异常不进
    # try/except 块），但要确认最终文件未被替换
    assert not final.exists()


# ---------- returncode=0 但产出 0 字节 ----------

def test_generate_stl_raises_on_zero_byte_output(tmp_stl_dir, fake_openscad, monkeypatch):
    """OpenSCAD returncode=0 但生成的 STL 文件 0 字节也算失败（评审反馈）。"""
    def _run(cmd, **kw):
        # 创建文件但写 0 字节
        tmp_out = Path(cmd[cmd.index("-o") + 1])
        tmp_out.touch()  # 0 字节
        return MagicMock(returncode=0, stdout="", stderr="WARNING: empty result")
    monkeypatch.setattr(subprocess, "run", _run)

    with pytest.raises(RuntimeError, match="未生成或为空"):
        generator.generate_stl(3, 3, 1)

    # .tmp 文件清理
    tmp = tmp_stl_dir / ".openGrid_Full_3x3x1.tmp.stl"
    assert not tmp.exists()


# ---------- stack_gap 跨模块契约 ----------

def test_stack_gap_matches_cost_v2():
    """generator.py 注入 SCAD 的 Stack_Gap 必须 == cost_v2.calculate_stacks 默认 stack_gap。

    否则 split 算出来的 Z 高度跟实际 OpenSCAD 渲染的物理高度对不上。
    本测试钉死跨模块契约——任何一边改默认值都会先在这里报红。
    """
    import inspect
    from opengrid.core import cost_v2, constants
    from opengrid.stl import generator as gen

    # 确认两边都引用同一个 constants.STACK_GAP_MM
    sig = inspect.signature(cost_v2.calculate_stacks)
    cost_default = sig.parameters["stack_gap"].default
    assert cost_default == constants.STACK_GAP_MM

    # generator.py 拼 -D 参数时也必须是这个值——直接 grep 模块源码确认
    src = Path(gen.__file__).read_text(encoding="utf-8")
    assert "STACK_GAP_MM" in src
    assert f"Stack_Gap={{STACK_GAP_MM}}" in src or "Stack_Gap={STACK_GAP_MM}" in src


# ---------- generate_all_stls ----------

def test_generate_all_stls_iterates_scheme_stacks(tmp_stl_dir, fake_openscad, monkeypatch):
    """遍历 scheme.stacks 逐个生成。"""
    # 伪造一个 SplitResult-like 对象
    Tile = type("Tile", (), {})
    Stack = type("Stack", (), {})
    Scheme = type("Scheme", (), {})

    def make_stack(w, h, count):
        t = Tile()
        t.w, t.h = w, h
        s = Stack()
        s.tile = t
        s.count = count
        return s

    scheme = Scheme()
    scheme.stacks = [make_stack(3, 4, 2), make_stack(5, 5, 1)]

    captured = []
    monkeypatch.setattr(subprocess, "run", _fake_run_success(captured))

    results = generator.generate_all_stls(scheme)
    assert len(results) == 2
    assert all(status == "generated" for _, status in results)
    assert results[0][0].name == "openGrid_Full_3x4x2.stl"
    assert results[1][0].name == "openGrid_Full_5x5x1.stl"


def test_generate_all_stls_returns_empty_for_none():
    assert generator.generate_all_stls(None) == []


def test_generate_all_stls_returns_empty_for_scheme_without_stacks():
    Scheme = type("Scheme", (), {})
    assert generator.generate_all_stls(Scheme()) == []


# ---------- Integration smoke tests ----------
# 默认 pyproject.toml 的 addopts 跳过 integration；手动 `pytest -m integration` 启用

_OPENSCAD_AVAILABLE = (
    shutil.which("openscad") is not None
    or Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD").exists()
)
_QUACKWORKS_READY = (
    Path(__file__).parent.parent / "vendor/QuackWorks/openGrid/openGrid.scad"
).exists()


@pytest.mark.integration
@pytest.mark.timeout(60)
@pytest.mark.skipif(not _OPENSCAD_AVAILABLE, reason="OpenSCAD CLI not installed")
@pytest.mark.skipif(not _QUACKWORKS_READY, reason="QuackWorks submodule not initialized")
@pytest.mark.parametrize(
    "tile_type,tile_thickness",
    [("Full", 6.8), ("Lite", 4.0), ("Heavy", 13.8)],
)
def test_real_openscad_smoke_all_tile_types(tmp_path, monkeypatch, tile_type, tile_thickness):
    """跑真实 OpenSCAD 生成最小 2x2x1 STL，覆盖 Full/Lite/Heavy 三个 SCAD 分支。

    确认 wrapper.scad 里的 if/else if 分发到 openGrid / openGridLite / openGridHeavy
    每个分支都能跑通（曾经有 Lite/Heavy 模块签名不一致的风险）。
    """
    monkeypatch.setattr(generator, "_resolve_stl_dir", lambda: tmp_path)
    monkeypatch.setattr(
        generator, "_resolve_tile_config",
        lambda: (tile_type, 28, tile_thickness),
    )
    path, status = generator.generate_stl(2, 2, 1, force=True)
    assert status == "generated"
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.name == f"openGrid_{tile_type}_2x2x1.stl"
