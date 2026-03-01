# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## 非显而易见的项目规范

### 测试超时
- 测试超时设置为 **5秒/测试**（在 `pytest.ini` 中），不是常见的30秒或更长

### 配置系统
- 配置文件 `opengrid_config.yaml` 必须在**项目目录**中（不是全局配置）
- 配置有缓存机制：在 `opengrid/config.py` 中，`load_config()` 使用全局变量 `_config` 缓存配置
- 修改配置后调用 `reload_config()` 清除缓存

### 库存管理
- **禁止直接编辑** `inventory.json`，必须通过 CLI 命令修改
- 使用命令：`uv run scripts/opengrid.py inventory add/deduct`
- 每次操作自动记录日志

### 核心常量是全局可变状态
- `opengrid/core/constants.py` 中的 `MAX_X`, `MAX_Y`, `TILE_SIZE` 等是全局变量
- 调用 `recalculate_derived_constants()` 会修改这些全局变量
- 这会影响所有后续计算，需要注意调用顺序

### 尺寸解析格式
- 支持两种乘号：`x` 和 `×`（Unicode U+00D7）
- 示例：`265x365` 和 `265×365` 等效

### CLI 参数传递
- 配置文件和库存文件路径通过 `-c` 和 `-i` 参数传递
- 必须在有 `opengrid_config.yaml` 的目录下运行，或使用绝对路径

## 测试命令
```bash
# 运行所有测试
uv run pytest

# 运行单个测试
uv run pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed
```

## 常用命令
```bash
# 分割计算
uv run scripts/opengrid.py split 325x460

# 使用库存
uv run scripts/opengrid.py -i inventory.json split 325x460

# 查看状态
uv run scripts/opengrid.py -c ./opengrid_config.yaml status
```
