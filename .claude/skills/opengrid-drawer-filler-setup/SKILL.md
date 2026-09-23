---
name: opengrid-drawer-filler-setup
description: 首次准备 openGrid 抽屉铺满工具的运行环境——安装 OpenSCAD、初始化 QuackWorks submodule、安装 BOSL2 库。当用户克隆仓库后第一次想用、或运行 slicer generate 报 "OpenSCAD 找不到 / BOSL2 找不到 / openGrid.scad 找不到" 等环境问题、或主动说"装一下环境/setup/初始化"时使用此技能。
compatibility: macOS + Homebrew；Python/uv 由 pyproject.toml 处理，本 skill 不管
---

# openGrid 抽屉铺满 - 环境准备

只负责**生成 STL 所需的系统依赖**。Python 依赖由 `uv sync` 处理，配置和库存由仓库自带的 `opengrid_config.yaml` / `inventory.json` 提供——本 skill 都不管。

## 啥时候要跑

- 第一次克隆仓库
- `slicer generate` 报 OpenSCAD 找不到 / BOSL2 找不到
- `vendor/QuackWorks/` 是空的（忘了 `git submodule update --init`）

只要这三个东西都齐了，本 skill 就不用再跑：

| 依赖 | 位置 | 校验命令 |
|------|------|---------|
| OpenSCAD | macOS `/opt/homebrew/bin/openscad`；Linux nightly AppImage 放进 PATH | `which openscad` |
| QuackWorks SCAD 源码 | `vendor/QuackWorks/openGrid/openGrid.scad` | `ls vendor/QuackWorks/openGrid/openGrid.scad` |
| BOSL2 库 | `<User Library Path>/BOSL2/`（macOS `~/Library/Application Support/OpenSCAD/libraries`，Linux `~/.local/share/OpenSCAD/libraries`） | `openscad --info \| grep "User Library Path"`，再 `ls <该路径>/BOSL2/std.scad` |

## 一键安装

```bash
./scripts/setup.sh
```

脚本会幂等地处理三件事（已装的会跳过）。看到最后打印 `=== setup OK ===` 就行。

## 手动安装（脚本失败时按顺序排查）

### 1. OpenSCAD

```bash
# macOS
brew install --cask openscad@snapshot
# Linux：从 https://openscad.org/downloads.html#snapshots 下 nightly AppImage，chmod +x 后放进 PATH（如 ~/.local/bin/openscad）
```

为什么用 snapshot/nightly：稳定版本对 BOSL2 的部分函数支持不全，openGrid.scad 的某些特性需要 nightly。

### 2. QuackWorks submodule

```bash
git submodule update --init
```

仓库根有 `.gitmodules` 声明 `vendor/QuackWorks → AndyLevesque/QuackWorks`。首次 clone 不会自动拉，必须显式 init。已经 init 过的话这条命令是 no-op。

**不要加 `--recursive`**：QuackWorks 上游有个嵌套子模块 `MultiConnectOpenSCAD` 没写进它的 `.gitmodules`，递归 init 会 `fatal: No url found for submodule path`。openGrid.scad 只依赖 BOSL2，用不到它。

### 3. BOSL2 库

BOSL2 装在 OpenSCAD 的 User Library Path（系统级共享），不放在仓库里。路径因平台而异，以 `openscad --info` 为准：

```bash
# 无头环境下 openscad --info 退出码是 1，但输出正常
LIB_DIR=$(openscad --info 2>/dev/null | sed -n 's/^User Library Path: //p')
BOSL2_DIR="$LIB_DIR/BOSL2"
mkdir -p "$(dirname "$BOSL2_DIR")"
git clone https://github.com/BelfrySCAD/BOSL2 "$BOSL2_DIR"
```

> 为啥不当 submodule：BOSL2 是 OpenSCAD 生态的通用库，多项目共用一份合理；OpenSCAD 默认就从这个目录找 `include <BOSL2/...>`，免去配 `OPENSCADPATH`。

## 验证

```bash
# 试渲染一个 1x1 lite tile，输出非空（约 100KB）STL 才算 OK
openscad -o /tmp/test.stl \
  -D 'Full_or_Lite="Lite"' -D 'Board_Width=1' -D 'Board_Height=1' \
  vendor/QuackWorks/openGrid/openGrid.scad
ls -lh /tmp/test.stl && rm /tmp/test.stl
```

报错通常是 BOSL2 没装好（找不到 `std.scad`）或 submodule 没拉（找不到 `openGrid.scad`）。

## 完成之后

回到主 skill [opengrid-drawer-filler](../opengrid-drawer-filler/SKILL.md)，跑：

```bash
uv run scripts/opengrid.py slicer generate 8x9x1
```
