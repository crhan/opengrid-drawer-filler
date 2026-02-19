# macOS 一键安装脚本实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 为新用户创建自动化安装脚本，自动安装 OpenSCAD、克隆 QuackWorks、安装 BOSL2。

**Architecture:** 创建 Shell 脚本 `scripts/setup.sh`，更新 `split_calc.py` 使用 skill 目录内的 vendor 文件。

**Tech Stack:** Shell (bash), Homebrew, Git

---

## Task 1: 创建安装脚本框架

**Files:** Create `scripts/setup.sh`

```bash
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
```

**验证:** `chmod +x scripts/setup.sh && ./scripts/setup.sh`

---

## Task 2: 添加 check_homebrew

**Files:** Modify `scripts/setup.sh`

```bash
check_homebrew() {
    echo -e "\n${YELLOW}检查 Homebrew...${NC}"
    if command -v brew &> /dev/null; then
        echo -e "${GREEN}✓ Homebrew 已安装${NC}"
        return 0
    fi
    echo -e "${RED}✗ Homebrew 未安装${NC}"
    echo "运行: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    return 1
}
check_homebrew
```

---

## Task 3: 添加 install_openscad

**Files:** Modify `scripts/setup.sh`

```bash
install_openscad() {
    echo -e "\n${YELLOW}检查 OpenSCAD...${NC}"
    if [ -d "/Applications/OpenSCAD.app" ] && [ "$FORCE" = false ]; then
        echo -e "${GREEN}✓ OpenSCAD 已安装${NC}"
        return 0
    fi
    echo -e "${YELLOW}安装 OpenSCAD Snapshot...${NC}"
    brew install --cask openscad@snapshot
    [ -d "/Applications/OpenSCAD.app" ] && echo -e "${GREEN}✓ OpenSCAD 安装成功${NC}"
}
install_openscad
```

---

## Task 4: 添加 clone_quackworks

**Files:** Modify `scripts/setup.sh`

```bash
clone_quackworks() {
    echo -e "\n${YELLOW}检查 QuackWorks...${NC}"
    if [ -d "$QUACKWORKS_DIR" ] && [ "$FORCE" = false ]; then
        echo -e "${GREEN}✓ QuackWorks 已存在${NC}"
        return 0
    fi
    rm -rf "$QUACKWORKS_DIR"
    mkdir -p "$VENDOR_DIR"
    git clone https://github.com/AndyLevesque/QuackWorks "$QUACKWORKS_DIR"
    [ -f "$QUACKWORKS_DIR/openGrid/openGrid.scad" ] && echo -e "${GREEN}✓ QuackWorks 克隆成功${NC}"
}
clone_quackworks
```

---

## Task 5: 添加 install_bosl2

**Files:** Modify `scripts/setup.sh`

```bash
install_bosl2() {
    echo -e "\n${YELLOW}检查 BOSL2...${NC}"
    if [ -d "$BOSL2_DIR" ] && [ "$FORCE" = false ]; then
        echo -e "${GREEN}✓ BOSL2 已安装${NC}"
        return 0
    fi
    rm -rf "$BOSL2_DIR"
    mkdir -p "$(dirname "$BOSL2_DIR")"
    git clone https://github.com/BelfrySCAD/BOSL2 "$BOSL2_DIR"
    [ -f "$BOSL2_DIR/BOSL2.scad" ] && echo -e "${GREEN}✓ BOSL2 安装成功${NC}"
}
install_bosl2
```

---

## Task 6: 添加 check_slicer

**Files:** Modify `scripts/setup.sh`

```bash
check_slicer() {
    echo -e "\n${YELLOW}检查切片软件...${NC}"
    [ -d "/Applications/BambuStudio.app" ] && echo -e "${GREEN}✓ Bambu Studio${NC}" || echo -e "${YELLOW}△ Bambu Studio (下载: https://bambulab.com/bambustudio)${NC}"
    [ -d "/Applications/OrcaSlicer.app" ] && echo -e "${GREEN}✓ Orca Slicer${NC}" || echo -e "${YELLOW}△ Orca Slicer (下载: https://github.com/SoftFever/OrcaSlicer)${NC}"
}
check_slicer
```

---

## Task 7: 添加 verify

**Files:** Modify `scripts/setup.sh`

```bash
verify() {
    echo -e "\n${YELLOW}验证安装结果...${NC}"
    local ok=true
    [ -d "/Applications/OpenSCAD.app" ] || { echo -e "${RED}✗ OpenSCAD${NC}"; ok=false; }
    [ -f "$QUACKWORKS_DIR/openGrid/openGrid.scad" ] || { echo -e "${RED}✗ QuackWorks${NC}"; ok=false; }
    [ -f "$BOSL2_DIR/BOSL2.scad" ] || { echo -e "${RED}✗ BOSL2${NC}"; ok=false; }
    echo ""
    [ "$ok" = true ] && echo -e "${GREEN}=== 安装完成 ===${NC}" || echo -e "${RED}=== 部分安装失败 ===${NC}"
}
verify
```

---

## Task 8: 更新 split_calc.py 路径

**Files:** Modify `scripts/split_calc.py:27-30`

原代码：
```python
OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE = "/Users/ruohanc/Documents/GitHub/QuackWorks/openGrid/openGrid.scad"
```

替换为：
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")

OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
SCAD_FILE = os.path.join(VENDOR_DIR, "QuackWorks", "openGrid", "openGrid.scad")
```

**验证:** `python3 scripts/split_calc.py --help`

---

## Task 9: 测试脚本

```bash
./scripts/setup.sh
ls -la scripts/vendor/QuackWorks/openGrid/openGrid.scad
ls -la ~/Library/Application\ Support/OpenSCAD/libraries/BOSL2/BOSL2.scad
```

---

## Task 10: 更新 CLAUDE.md

添加安装说明：
```markdown
## 首次安装

首次使用运行：
```bash
cd {skill_dir}
./scripts/setup.sh
```

脚本安装：OpenSCAD Snapshot、QuackWorks、BOSL2。
```

---

**Plan complete. Two execution options:**

**1. Subagent-Driven** - 我为每个任务派遣 subagent，任务间审查

**2. Parallel Session** - 新会话使用 executing-plans

**Which approach?**
