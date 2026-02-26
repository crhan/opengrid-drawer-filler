# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 **Claude Code 插件** (Claude Plugin)，名为 `opengrid-drawer-filler`。

功能：计算抽屉最优瓦片分割方案并生成 STL 文件用于 3D 打印。

## 插件结构

```
opengrid_plugin/                    # 插件根目录
├── .claude-plugin/
│   └── plugin.json                 # 插件清单 (必须)
│
├── skills/                         # Agent Skills
│   ├── opengrid-drawer-filler/     # 主技能：抽屉铺满计算
│   │   ├── SKILL.md               # 技能定义
│   │   └── references/            # 参考文档
│   └── opengrid-drawer-filler-setup/ # 安装配置技能
│
├── opengrid/                       # 核心 Python 库 (技能调用)
│   ├── core/                      # 核心算法
│   ├── stl/                       # STL 生成
│   └── ui/                        # 输出展示
│
├── scripts/                       # CLI 入口脚本
│   ├── split_calc.py              # 批量计算
│   ├── slicer.py                  # STL 生成
│   └── inventory.py               # 库存管理
│
└── tests/                         # 测试目录
```

### 插件清单 (plugin.json)

```json
{
  "name": "opengrid-drawer-filler",
  "skills": "./skills"
}
```

## 开发工作流

### 本地测试插件

使用 `--plugin-dir` 加载插件进行测试：

```bash
claude --plugin-dir /Users/ruohanc/Documents/projects/opengrid_plugin
```

测试技能调用：
```
/opengrid-drawer-filler 265x365
```

### 开发循环

1. 修改代码或技能定义
2. 重启 Claude Code 加载更新
3. 测试功能

### 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_scheme.py

# 运行单个测试
uv run pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed
```

## 常用命令

```bash
# 分割计算
uv run scripts/opengrid.py split 325x460
uv run scripts/opengrid.py split 325x460 -i inventory.json

# JSON 输出
uv run scripts/opengrid.py split 325x460 -j

# 方案对比（生成 HTML）
uv run scripts/opengrid.py split 325x460 -j > scheme_a.json
uv run scripts/opengrid.py split 325x460 -i inventory.json -j > scheme_b.json
uv run scripts/opengrid.py present scheme_a.json scheme_b.json -o comparison.html

# 库存管理
uv run scripts/opengrid.py inventory list
uv run scripts/opengrid.py inventory add 8x8:5 "原因"
uv run scripts/opengrid.py inventory deduct 8x8:2 "原因"
```

## 核心设计原则

**Agent 负责用户交互，脚本负责计算和生成。**

- 脚本不含 `input()` 或交互式提示
- 脚本只做计算，Agent 处理用户交互
- 完整工作流见 [SKILL.md](SKILL.md)

## 库存管理约束

- **禁止直接编辑** `inventory/inventory.json`
- 必须通过脚本修改并提供原因
- 每次操作记录到日志

## 核心常量

- `TILE_SIZE = 28` - 网格单元格大小 (mm)
- `MAX_X = 10`, `MAX_Y = 11` - 最大瓦片尺寸
- `FULL_THICKNESS = 7.2` - 单层厚度
- `MAX_Z = 325` - 打印机 Z 轴限制

### 算法优先级

最小化独特尺寸 → 最小化瓦片总数 → 最大化均衡度
