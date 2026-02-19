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
