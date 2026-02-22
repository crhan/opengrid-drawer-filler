# 全局/项目级配置与库存分离设计

## 目标

支持配置和库存的全局（技能目录）和项目（当前工作目录）两级管理，通过配置文件名检测自动切换。

## 设计原则

1. **完全独立** - 项目级和全局级完全分开，通过配置文件名检测
2. **配置驱动库存位置** - inventory 位置在配置中指定，灵活可配置
3. **向后兼容** - 不影响现有全局配置的使用方式

## 配置文件设计

### 全局配置

- **位置**: `{skill_dir}/config/config.yaml`
- **文件名**: `config.yaml`（固定）

### 项目配置

- **位置**: `{当前目录}/opengrid_config.yaml`
- **文件名**: `opengrid_config.yaml`（检测标识）

### 配置文件结构

```yaml
# 全局配置示例
initialized: true
printer:
  model: p1p
output:
  stl_dir: ~/3D打印/opengrid/
projects_dir: ~/opengrid_projects/
opengrid:
  tile_type: Full
  stacking_method: Ironing
software:
  openscad: /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
# inventory_path: 可选，默认使用全局 inventory

---

# 项目配置示例 (opengrid_config.yaml)
printer:
  model: h2d  # 覆盖全局
inventory_path: ./my_project/inventory.json  # 项目级库存
output:
  stl_dir: ./stl_output/  # 项目级输出目录
```

### 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `inventory_path` | string | 库存文件路径，可为相对或绝对路径 |
| 其他字段 | - | 直接覆盖全局配置 |

## 库存文件设计

### 库存位置确定逻辑

1. 加载全局配置
2. 加载项目配置（如存在），覆盖全局
3. 从配置中读取 `inventory_path`
4. 如果 `inventory_path` 存在，则使用；否则使用全局 inventory

### 库存文件格式

保持现有 JSON 格式不变：

```json
{
  "inventory": {
    "8x8": 5,
    "6x7": 3
  },
  "log": [
    {
      "timestamp": "2024-01-01T00:00:00",
      "action": "add",
      "items": {"8x8": 5},
      "reason": "购买新材料"
    }
  ]
}
```

## 实现要点

### 1. 配置加载重构

```python
# opengrid/config.py

def get_config_path(scope="auto"):
    """获取配置文件路径

    Args:
        scope: "global" | "project" | "auto" (默认自动检测)
    """
    skill_dir = Path(__file__).parent.parent
    if scope == "global":
        return skill_dir / "config" / "config.yaml"

    # auto 或 project
    project_config = Path.cwd() / "opengrid_config.yaml"
    if project_config.exists() or scope == "project":
        return project_config

    return skill_dir / "config" / "config.yaml"

def load_config(scope="auto"):
    """加载配置，支持全局/项目级"""
    if scope == "project" or (scope == "auto" and _is_project_mode()):
        project_config = load_single_config(get_config_path("project"))
        global_config = load_single_config(get_config_path("global"))
        # 合并：项目覆盖全局
        return merge_config(global_config, project_config)
    return load_single_config(get_config_path(scope))

def _is_project_mode():
    """检测是否为项目模式"""
    return (Path.cwd() / "opengrid_config.yaml").exists()
```

### 2. 库存加载重构

```python
# opengrid/inventory.py

def get_inventory_path(config=None):
    """从配置获取库存文件路径"""
    if config is None:
        config = load_config()

    inventory_path = config.get("inventory_path")
    if inventory_path:
        return Path(inventory_path)

    # 默认使用全局 inventory
    skill_dir = Path(__file__).parent.parent
    return skill_dir / "inventory" / "inventory.json"

def load_inventory(config=None):
    """加载库存"""
    inv_file = get_inventory_path(config)
    # ... 现有逻辑
```

### 3. 初始化流程更新

首次初始化时，引导用户设置：
1. 全局配置（现有流程）
2. 项目配置（新增）
   - 指定 `inventory_path`（可选）
   - 可以指向项目目录内的 inventory

### 4. CLI 参数

```bash
# 指定使用全局配置/库存
.venv/bin/python scripts/split_calc.py 265 365 -l global

# 指定使用项目配置/库存
.venv/bin/python scripts/split_calc.py 265 365 -l project

# 自动检测（默认）
.venv/bin/python scripts/split_calc.py 265 365 -l auto
```

## 目录结构示例

```
~/opengrid_projects/
├── my_drawer_1/
│   ├── opengrid_config.yaml      # 项目配置
│   └── my_inventory.json        # 项目库存
│
├── my_drawer_2/
│   ├── opengrid_config.yaml
│   └── inventory/               # 也可以用目录
│       └── inventory.json
│
└── shared_inventory/
    └── inventory.json           # 共享库存
```

## 迁移策略

1. **向后兼容** - 现有全局配置不变
2. **平滑升级** - 不强制要求项目配置
3. **显式指定** - CLI 参数 `-l` 可强制指定级别

## 测试用例

1. 全局配置加载
2. 项目配置覆盖全局
3. 项目配置指定外部 inventory 路径
4. 自动检测项目模式
5. CLI 参数强制指定级别
6. 库存操作在项目/全局级别正确执行
