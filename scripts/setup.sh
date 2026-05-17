#!/bin/bash
# 准备 STL 生成所需的系统依赖。幂等，可重复运行。
# 详细说明见 .claude/skills/opengrid-drawer-filler-setup/SKILL.md

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOSL2_DIR="$HOME/Library/Application Support/OpenSCAD/libraries/BOSL2"
QUACKWORKS_SCAD="$REPO_ROOT/vendor/QuackWorks/openGrid/openGrid.scad"

echo "=== openGrid-drawer-filler setup ==="
echo "仓库: $REPO_ROOT"
echo ""

# 1. OpenSCAD
echo "[1/3] OpenSCAD"
if command -v openscad &> /dev/null; then
    echo -e "  ${YELLOW}已装${NC} ($(which openscad))"
else
    if ! command -v brew &> /dev/null; then
        echo -e "  ${RED}缺 Homebrew，去 https://brew.sh 装一下${NC}"
        exit 1
    fi
    echo "  brew install --cask openscad@snapshot ..."
    brew install --cask openscad@snapshot
    echo -e "  ${GREEN}装好${NC}"
fi

# 2. QuackWorks submodule
echo "[2/3] QuackWorks submodule"
if [ -f "$QUACKWORKS_SCAD" ]; then
    echo -e "  ${YELLOW}已 init${NC} ($QUACKWORKS_SCAD)"
else
    echo "  git submodule update --init --recursive ..."
    git -C "$REPO_ROOT" submodule update --init --recursive
    if [ ! -f "$QUACKWORKS_SCAD" ]; then
        echo -e "  ${RED}submodule 拉完但找不到 $QUACKWORKS_SCAD${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}OK${NC}"
fi

# 3. BOSL2
echo "[3/3] BOSL2"
if [ -d "$BOSL2_DIR/.git" ]; then
    echo -e "  ${YELLOW}已装${NC} ($BOSL2_DIR)"
else
    mkdir -p "$(dirname "$BOSL2_DIR")"
    echo "  git clone BelfrySCAD/BOSL2 ..."
    git clone --depth=1 https://github.com/BelfrySCAD/BOSL2 "$BOSL2_DIR"
    echo -e "  ${GREEN}装好${NC}"
fi

# 烟测：渲染一个最小 lite tile
echo ""
echo "烟测：渲染 1x1 lite tile ..."
TEST_STL=$(mktemp -t opengrid_setup_test.XXXXXX.stl)
trap 'rm -f "$TEST_STL"' EXIT
if openscad -o "$TEST_STL" \
    -D 'Full_or_Lite="Lite"' \
    -D 'Board_Width=1' -D 'Board_Height=1' \
    "$QUACKWORKS_SCAD" 2>&1 | tail -3; then
    if [ -s "$TEST_STL" ]; then
        SIZE=$(wc -c < "$TEST_STL" | tr -d ' ')
        echo -e "  ${GREEN}OK${NC} ($SIZE bytes)"
    else
        echo -e "  ${RED}STL 文件是空的${NC}"
        exit 1
    fi
else
    echo -e "  ${RED}OpenSCAD 渲染失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== setup OK ===${NC}"
echo "下一步: uv run scripts/opengrid.py slicer generate 8x9x1"
