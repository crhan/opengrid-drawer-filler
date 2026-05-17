"""STL generation via OpenSCAD CLI

调用 wrapper.scad（同目录），通过 -D 注入参数生成单层或多层堆叠的 openGrid 瓦片。
Z 高度 / stack_gap 与 opengrid/core/cost_v2.py 保持一致，避免成本估算与实物高度不一致。
"""
import os
import shutil
import subprocess
from pathlib import Path

from opengrid.config import load_config_or_default
from opengrid.core.constants import TILE_THICKNESS, STACK_GAP_MM


# 路径常量
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
# 直接调 QuackWorks 顶层 openGrid.scad —— 它自带完整入口（Full/Lite/Heavy
# 分发 + Stack_Count 堆叠 + Stacking_Method 切换 + Interface Layer / Ironing），
# 没必要在仓库里再维护一个 wrapper.scad。
QUACKWORKS_SCAD = _REPO_ROOT / "vendor" / "QuackWorks" / "openGrid" / "openGrid.scad"

# macOS Homebrew cask 默认安装位置，shutil.which 找不到 openscad 时的兜底
_DEFAULT_OPENSCAD_MACOS = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"

# 单次 OpenSCAD 调用超时（秒）。复杂瓦片 + 多层堆叠 ~几十秒
_OPENSCAD_TIMEOUT = 120


def _find_openscad() -> str:
    """先 PATH，找不到回 macOS 默认位置。都没有就给清晰的 setup 提示。"""
    found = shutil.which("openscad")
    if found:
        return found
    if Path(_DEFAULT_OPENSCAD_MACOS).exists():
        return _DEFAULT_OPENSCAD_MACOS
    raise FileNotFoundError(
        "找不到 OpenSCAD CLI。"
        "请运行 /opengrid-drawer-filler-setup skill 安装环境（或 `brew install --cask openscad@snapshot`）。"
    )


def _check_quackworks() -> None:
    """submodule 没 init 时显式报错，比让 OpenSCAD 抛通用错好得多。"""
    if not QUACKWORKS_SCAD.exists():
        raise FileNotFoundError(
            f"QuackWorks submodule 未初始化：{QUACKWORKS_SCAD}\n"
            "请运行 `git submodule update --init --recursive` 或 /opengrid-drawer-filler-setup skill。"
        )


def _resolve_stl_dir() -> Path:
    """读 opengrid_config.yaml 的 output.stl_dir，展开 ~ 并返回绝对路径。"""
    config = load_config_or_default()
    raw = config.get("output", {}).get("stl_dir", "~/3D打印/opengrid/")
    return Path(os.path.expanduser(raw)).resolve()


def _resolve_tile_config() -> tuple[str, int, float]:
    """从 config 取 tile_type / tile_size / tile_thickness。"""
    config = load_config_or_default()
    tile_type = config.get("opengrid", {}).get("tile_type", "Full")
    tile_size = config.get("opengrid", {}).get("tile_size", 28)
    tile_thickness = TILE_THICKNESS.get(tile_type, 6.8)
    return tile_type, tile_size, tile_thickness


def generate_stl(
    width: int,
    height: int,
    stacks: int = 1,
    verbose: bool = False,
    force: bool = False,
) -> tuple[Path, str]:
    """生成一块 W×H cells 的 openGrid 瓦片 STL，垂直堆叠 stacks 层。

    Args:
        width: 瓦片宽度（cells）
        height: 瓦片深度（cells）
        stacks: 垂直堆叠层数（≥1）
        verbose: 打印 OpenSCAD 命令行 + warnings
        force: 已存在文件强制重生

    Returns:
        (output_path, status)，status ∈ {"generated", "skipped"}

    Raises:
        FileNotFoundError: OpenSCAD / QuackWorks submodule 缺失
        RuntimeError: OpenSCAD 返回非 0 或没产出文件
        subprocess.TimeoutExpired: 渲染超过 120 秒
    """
    _check_quackworks()
    openscad = _find_openscad()
    tile_type, tile_size, tile_thickness = _resolve_tile_config()

    out_dir = _resolve_stl_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"openGrid_{tile_type}_{width}x{height}x{stacks}.stl"

    if output_path.exists() and not force:
        if verbose:
            print(f"[skip] {output_path} 已存在（用 --force 强制重生）")
        return output_path, "skipped"

    # 原子化策略：先写 hidden tmp（.stl 后缀让 OpenSCAD 接受），成功后 os.replace 替换原文件
    tmp_path = output_path.parent / f".{output_path.stem}.tmp.stl"

    # Ironing 模式下 openGrid.scad 的层间距 = Tile_Thickness + 2 × Interface_Separation。
    # 要跟 cost_v2 的 stack_gap=0.4 对齐，Interface_Separation 必须取 STACK_GAP_MM / 2 = 0.2。
    interface_separation = STACK_GAP_MM / 2

    cmd = [
        openscad,
        "-o", str(tmp_path),
        # —— 核心几何参数 ——
        "-D", f'Full_or_Lite="{tile_type}"',
        "-D", f"Board_Width={width}",
        "-D", f"Board_Height={height}",
        "-D", f"Stack_Count={stacks}",
        "-D", f"Tile_Size={tile_size}",
        "-D", f"Tile_Thickness={tile_thickness}",
        # —— 堆叠：Ironing 模式（单材打印，跟 yaml 默认一致），Z 间距对齐 cost_v2 ——
        "-D", 'Stacking_Method="Ironing - BETA"',
        "-D", f"Interface_Separation={interface_separation}",
        # —— 显式关掉装饰特性（保持跟旧 wrapper.scad 产出的形态一致；
        #     未来要支持螺丝孔/倒角/连接孔时再扩 yaml 配置）——
        "-D", 'Screw_Mounting="None"',
        "-D", 'Chamfers="None"',
        "-D", "Connector_Holes=false",
        "-D", "Add_Adhesive_Base=false",
        str(QUACKWORKS_SCAD),
    ]

    if verbose:
        print(f"[run] {' '.join(cmd)}")

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_OPENSCAD_TIMEOUT
    )

    if proc.returncode != 0:
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(
            f"OpenSCAD 生成失败 (returncode={proc.returncode}):\n{proc.stderr}"
        )

    # OpenSCAD 有时 warning 当 error 但 returncode=0；用文件检查兜底
    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(
            f"OpenSCAD returncode=0 但 STL 文件未生成或为空:\n{proc.stderr}"
        )

    os.replace(tmp_path, output_path)

    if verbose and proc.stderr:
        print(proc.stderr, end="")

    return output_path, "generated"


def generate_all_stls(
    scheme,
    verbose: bool = False,
    force: bool = False,
) -> list[tuple[Path, str]]:
    """遍历 SplitResult.stacks 把所有 stack 都生成 STL。

    Args:
        scheme: SplitResult 实例（必须有 .stacks 属性，元素含 .tile.w/.tile.h/.count）

    Returns:
        list of (path, status) tuples
    """
    results: list[tuple[Path, str]] = []
    if scheme is None or not hasattr(scheme, "stacks"):
        return results
    for stack in scheme.stacks:
        path, status = generate_stl(
            stack.tile.w, stack.tile.h, stack.count,
            verbose=verbose, force=force,
        )
        results.append((path, status))
    return results
