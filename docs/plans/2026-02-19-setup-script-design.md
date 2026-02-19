# macOS 一键安装脚本设计

## 目标

为从 0 开始的新用户创建自动化安装脚本，自动安装所有必需软件。

## 架构

```
scripts/setup.sh  (主安装脚本)
├── check_homebrew()        # 检查/安装 Homebrew
├── install_openscad()      # 安装 OpenSCAD Snapshot
├── clone_quackworks()      # 克隆 QuackWorks 仓库到 skill 目录
├── install_bosl2()         # 下载安装 BOSL2 库
├── check_slicer()          # 检查切片软件（可选）
└── verify()                # 验证安装结果
```

## 安装步骤

### 1. 检查 Homebrew

- 检查是否已安装：`brew --version`
- 未安装则提示并提供安装命令

### 2. 安装 OpenSCAD

- 使用 `brew install --cask openscad@snapshot`
- 验证：`/Applications/OpenSCAD.app`

### 3. 克隆 QuackWorks

- 克隆仓库：`https://github.com/AndyLevesque/QuackWorks`
- 目标目录：`{skill_dir}/vendor/QuackWorks`
- SCAD 文件路径：`{skill_dir}/vendor/QuackWorks/openGrid/openGrid.scad`

### 4. 安装 BOSL2

- 克隆仓库：`https://github.com/BelfrySCAD/BOSL2`
- 目标目录：`~/Library/Application Support/OpenSCAD/libraries/BOSL2`

### 5. 切片软件检查（可选）

- 检查 Bambu Studio：`/Applications/BambuStudio.app`
- 检查 Orca Slicer：`/Applications/OrcaSlicer.app`
- 未安装则提示下载链接

### 6. 验证

- 检查 OpenSCAD 是否可执行
- 检查 BOSL2 库是否存在
- 检查 QuackWorks 源码是否存在

## 输出路径

| 组件 | 路径 |
|------|------|
| QuackWorks | `{skill_dir}/vendor/QuackWorks` |
| BOSL2 | `~/Library/Application Support/OpenSCAD/libraries/BOSL2` |
| OpenSCAD | `/Applications/OpenSCAD.app` |

## 代码更新

更新 `split_calc.py` 中的路径常量：

```python
# 获取 skill 目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")

# 更新 SCAD 文件路径
SCAD_FILE = os.path.join(VENDOR_DIR, "QuackWorks", "openGrid", "openGrid.scad")
```

## 使用方式

```bash
# 运行安装脚本
./scripts/setup.sh

# 或带详细输出
./scripts/setup.sh -v
```

## 错误处理

- 每个步骤返回状态码
- 失败时打印错误信息和解决建议
- 支持 `--force` 参数强制重新安装
