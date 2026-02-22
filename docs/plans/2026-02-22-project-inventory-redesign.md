# 项目库存分离设计

## 背景

当前 openGrid 使用全局库存（存储在 `inventory/inventory.json`），所有项目共享。这导致：
- 不同项目的库存混在一起
- 无法独立跟踪每个项目的瓦片消耗

## 目标

1. 移除全局库存，改为项目级库存
2. 保留全局项目索引，记录所有已初始化的项目目录
3. 当用户不在项目目录时，提示初始化或切换项目

## 架构

### 文件结构

```
~/.opengrid/
└── projects.json          # 项目索引（新增）

项目目录（每个项目独立）：
├── opengrid_config.yaml  # 项目配置
└── inventory.json        # 项目库存
```

### projects.json 结构

```json
{
  "projects": [
    {
      "name": "厨房抽屉",
      "path": "/Users/xxx/opengrid_projects/kitchen",
      "created": "2026-02-22T10:00:00"
    }
  ],
  "last_active": "/Users/xxx/opengrid_projects/kitchen"
}
```

### 配置变更

项目级 `opengrid_config.yaml` 需要指定 `inventory_path`：

```yaml
printer:
  model: h2d
inventory_path: ./inventory.json  # 项目专属库存
initialized: true
```

## 检测逻辑

### 入口检测（Agent 侧）

当用户调用 skill 时：

1. 获取当前工作目录（`Path.cwd()`）
2. 加载 `~/.opengrid/projects.json`
3. 检查当前目录是否为已注册项目：
   - **是**：继续执行，使用项目级库存
   - **否**：提示用户选择：
     - 初始化新项目（调用 setup skill）
     - 切换到已有项目（修改 `last_active`）

### 库存加载

现有 `opengrid/inventory.py` 的 `load_inventory(config=None)` 已支持通过 `config.get("inventory_path")` 指定项目库存文件，只需确保项目配置正确设置即可。

## 任务拆分

1. 创建 `~/.opengrid/projects.json` 索引模块
2. 修改 setup skill，初始化时注册项目到索引
3. 实现项目切换功能
4. 实现项目检测和提示逻辑
5. 清理全局库存文件

## 兼容性

- 现有全局配置 (`config/config.yaml`) 继续工作，但 inventory_path 改为可选
- 不再使用 `inventory/inventory.json`，改为项目级管理
