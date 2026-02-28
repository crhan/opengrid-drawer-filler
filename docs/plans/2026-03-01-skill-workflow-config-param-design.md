# SKILL.md 工作流优化 - 配置文件参数化

**Date:** 2026-03-01
**Status:** Approved

## 目标

优化 opengrid-drawer-filler SKILL.md 工作流的第一步：
1. Agent 主动查找配置文件和库存文件位置
2. 通过 `--config` 参数将配置文件路径传给脚本
3. 在 `status` 命令中传入参数确认现状

## 问题

1. `opengrid.py` 没有 `--config` 参数，配置文件只能通过当前工作目录自动查找
2. `status` 命令无法接收配置文件路径和库存文件路径参数
3. Agent 无法主动将配置文件路径传给脚本

## 设计方案

### 1. CLI 添加全局 `--config` 参数

在 `opengrid/cli/__init__.py` 中添加全局参数：

```python
parser = argparse.ArgumentParser(...)
parser.add_argument('-c', '--config', help='配置文件路径')
# ... 子命令解析
```

将 `--config` 传递给 config 模块使用。

### 2. config 模块支持指定配置文件路径

在 `opengrid/config.py` 中：

```python
def load_config(config_path: str = None):
    """加载配置，支持指定配置文件路径"""
    if config_path:
        # 使用指定的配置文件路径
        config_path = Path(config_path)
    else:
        # 自动查找
        config_path = get_config_path()
    # ...
```

### 3. 传递 config 参数到子命令

在 `cli/__init__.py` 中，将 `--config` 传递给子命令的 `func`：

```python
# 解析参数后，将 config 注入到 args
if hasattr(args, 'func') and args.config:
    # 将 config_path 存入全局或传递给命令
```

### 4. SKILL.md 工作流更新

```
Step 1: 查找配置文件和库存文件
  1.1 Agent 在当前目录及父目录向上搜索 opengrid_config.yaml
  1.2 根据配置中的 inventory_path 定位库存文件
  1.3 运行 status 命令并传入参数确认现状

示例命令：
uv run scripts/opengrid.py status --config ./opengrid_config.yaml -i ./inventory.json
```

## 实现步骤

1. 修改 `opengrid/cli/__init__.py` - 添加全局 `--config` 参数
2. 修改 `opengrid/config.py` - 支持指定配置文件路径
3. 修改 `opengrid/cli/commands/status.py` - 确保参数传递正确
4. 更新 `skills/opengrid-drawer-filler/SKILL.md` - 更新工作流描述

## 兼容性

- 不指定 `--config` 时，保持现有行为（自动查找）
- 指定 `--config` 时，优先使用指定路径
