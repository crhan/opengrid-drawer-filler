# 全局配置移除重构设计

## 背景

上一次重构将全局库存改为项目级库存，但保留了全局配置 (`config/config.yaml`)。现在需要进一步简化：完全移除全局配置，只保留项目级配置。

## 目标

1. 移除全局配置 (`config/config.yaml`)
2. 简化 `config.py`，只支持项目级配置
3. 简化 `inventory.py`，移除全局默认值
4. 简化 CLI 脚本，移除 `-l/--level` 参数
5. 更新测试用例适配新架构

## 架构

### 新的配置流程

```
用户调用 skill
    ↓
检测 is_project_registered(cwd) = false?
    ↓
提示用户初始化新项目或切换项目
    ↓
用户切换到项目目录（有 opengrid_config.yaml）
    ↓
加载 opengrid_config.yaml
    ↓
从 inventory_path 读取库存
```

### 文件变更

| 文件 | 操作 |
|------|------|
| `config/` 目录 | 删除 |
| `opengrid/config.py` | 简化，移除全局逻辑 |
| `opengrid/inventory.py` | 移除 INVENTORY_FILE 默认值 |
| `scripts/inventory.py` | 移除 `-l/--level` 参数 |
| `scripts/split_calc.py` | 移除 `-l/--level` 参数 |
| `scripts/slicer.py` | 移除 ensure_initialized() 调用 |

## 详细设计

### 1. config.py 简化

**移除的功能：**
- `scope="global"` 支持
- `get_config_path("global")`
- `load_config("global")`
- `get_inventory()` 函数
- 全局配置默认值回退

**保留的功能：**
- `load_config()` - 从 `opengrid_config.yaml` 读取
- `get_printer_config()` - 打印机配置
- `is_initialized()` - 检查初始化状态
- `ensure_initialized()` - 确保已初始化

### 2. inventory.py 简化

**移除：**
- `INVENTORY_FILE` 常量（指向 `inventory/inventory.json`）

**修改 `get_inventory_path()`：**
```python
def get_inventory_path(config):
    """从配置获取库存文件路径"""
    inventory_path = config.get("inventory_path")
    if not inventory_path:
        raise ValueError("未配置 inventory_path，请检查 opengrid_config.yaml")

    p = Path(inventory_path)
    if p.is_absolute():
        return p
    # 相对路径相对于配置文件所在目录
    config_dir = Path.cwd()
    return config_dir / p
```

### 3. CLI 简化

**scripts/inventory.py：**
- 移除 `-l/--level` 参数
- 直接从当前目录的 `opengrid_config.yaml` 读取配置

**scripts/split_calc.py：**
- 移除 `-l/--level` 参数
- 移除 `get_inventory()` 自动加载
- 改为显式通过 `-i/--inventory` 指定库存文件

**scripts/slicer.py：**
- 移除 `ensure_initialized()` 调用（因为在 skill 层面已检查）

### 4. 测试用例修改

需要修改以下测试文件，详细原因见下文：

| 测试文件 | 修改内容 |
|----------|----------|
| `test_config_scope.py` | 大部分测试需要删除或重写 |
| `test_inventory_cli_scope.py` | 移除 `-l` 参数相关测试 |
| `test_inventory.py` | 更新 fixture |
| `conftest.py` | 移除全局 inventory 备份逻辑 |
| `test_inventory_cli_integration.py` | 移除 `-l project` 参数 |

## 测试修改详细说明

### test_config_scope.py

| 测试用例 | 修改 | 理由 |
|----------|------|------|
| `test_get_config_path_global` | **删除** | 已移除全局配置功能 |
| `test_get_config_path_auto_returns_global_when_no_project_config` | **删除** | 不再有全局配置回退 |
| `test_config_scope_detection` | **保留** | 项目级检测仍然有效 |
| `test_default_inventory_path` | **删除** | 不再有默认库存路径 |
| `test_custom_inventory_path` | **保留** | 自定义路径功能保留 |
| `TestInventoryOperationsWithConfig` 类 | **保留** | 配置驱动库存功能保留 |

### test_inventory_cli_scope.py

| 测试用例 | 修改 | 理由 |
|----------|------|------|
| `test_inventory_help_shows_level_option` | **删除** | 已移除 `-l` 参数 |
| `test_list_with_global_level` | **删除** | 已移除全局级别 |
| `test_add_with_project_level` | **修改** | 移除 `-l project` 参数 |
| `test_add_to_global_creates_log_entry` | **修改** | 移除 `-l project` 参数 |
| `test_deduct_inventory_with_level` | **修改** | 移除 `-l project` 参数 |
| `test_undo_with_level` | **修改** | 移除 `-l project` 参数 |
| `TestInventoryCLIDefaultScope` 类 | **删除** | 移除 `-l` 参数后不再需要 |

### test_inventory.py

| 测试用例 | 修改 | 理由 |
|----------|------|------|
| 所有使用 `tmp_inventory` fixture 的测试 | **保留** | 测试仍然有效，fixture 改为创建临时文件 |

### conftest.py

| 修改项 | 修改 | 理由 |
|--------|------|------|
| Inventory 隔离机制 | **删除** | 不再有全局 inventory 需要备份 |
| 全局 inventory 备份/恢复逻辑 | **删除** | 同上 |

### test_inventory_cli_integration.py

| 测试用例 | 修改 | 理由 |
|----------|------|------|
| `run_inventory_cli()` | **修改** | 移除 `-l project` 参数 |
| 所有使用 `run_inventory_cli` 的测试 | **保留** | 其他逻辑不变 |

### test_integration_cli.py

需要检查是否依赖全局配置或 `-l` 参数。

## 验证清单

- [ ] `python -c "from opengrid.config import load_config"` 在非项目目录报错
- [ ] `python -c "from opengrid.config import load_config"` 在项目目录正常加载
- [ ] `scripts/inventory.py list` 在项目目录正常执行
- [ ] `scripts/split_calc.py 265 365` 需要显式指定 `-i inventory.json`
- [ ] 所有测试通过
