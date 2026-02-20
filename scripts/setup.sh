#!/bin/bash
set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENDOR_DIR="$SKILL_DIR/vendor"
QUACKWORKS_DIR="$VENDOR_DIR/QuackWorks"
BOSL2_DIR="$HOME/Library/Application Support/OpenSCAD/libraries/BOSL2"
VENV_DIR="$SKILL_DIR/.venv"

# 参数
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force) FORCE=true; shift ;;
        -h|--help) echo "Usage: $0 [-f|--force]"; exit 0 ;;
        *) shift ;;
    esac
done

echo "=== opengrid-drawer-filler 安装 ==="

# 0. 创建 Python venv
install_venv() {
    echo "0/4 创建 Python 虚拟环境..."
    if [ "$FORCE" = true ] || [ ! -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}Python venv 创建完成${NC}"
    else
        echo -e "${YELLOW}Python venv 已存在${NC}"
    fi
}

# 安装 Python 依赖
install_python_deps() {
    echo "安装 Python 依赖..."
    "$VENV_DIR/bin/pip" install --quiet pyyaml pytest Pillow
    echo -e "${GREEN}Python 依赖安装完成${NC}"
}

# 检查 Homebrew
check_brew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}错误: 需要安装 Homebrew${NC}"
        echo "访问: https://brew.sh"
        exit 1
    fi
    echo -e "${GREEN}Homebrew 已安装${NC}"
}

# 1. 安装 OpenSCAD
install_openscad() {
    echo "2/4 安装 OpenSCAD@snapshot..."
    if ! brew list --cask openscad@snapshot &> /dev/null; then
        brew install --cask openscad@snapshot
        echo -e "${GREEN}OpenSCAD@snapshot 安装完成${NC}"
    else
        echo -e "${YELLOW}OpenSCAD@snapshot 已安装${NC}"
    fi
}

# 2. 克隆 QuackWorks
install_quackworks() {
    echo "3/4 克隆 QuackWorks..."
    mkdir -p "$VENDOR_DIR"
    if [ ! -d "$QUACKWORKS_DIR" ]; then
        git clone https://github.com/AndyLevesque/QuackWorks "$QUACKWORKS_DIR"
        echo -e "${GREEN}QuackWorks 克隆完成${NC}"
    else
        echo -e "${YELLOW}QuackWorks 已存在${NC}"
    fi
}

# 3. 安装 BOSL2
install_bosl2() {
    echo "4/4 安装 BOSL2..."
    mkdir -p "$BOSL2_DIR"
    if [ ! -d "$BOSL2_DIR/.git" ]; then
        git clone https://github.com/revarwin/BOSL2 "$BOSL2_DIR"
        echo -e "${GREEN}BOSL2 安装完成${NC}"
    else
        echo -e "${YELLOW}BOSL2 已安装${NC}"
    fi
}

# 运行安装
check_brew
install_venv
install_python_deps
install_openscad
install_quackworks
install_bosl2

echo ""
echo -e "${GREEN}=== 安装完成 ===${NC}"
echo ""
echo "使用说明:"
echo "  运行脚本: .venv/bin/python scripts/split_calc.py 485 425"
echo "  运行测试: .venv/bin/python -m pytest"
