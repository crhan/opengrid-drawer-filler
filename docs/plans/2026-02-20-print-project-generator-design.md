# openGrid 项目打印计划生成器设计

## 概述

在 STL 生成后自动创建项目目录，包含 STL 文件、3MF 模板和打印计划 HTML 页面。

## 需求

1. **项目目录**：在 config 配置的固定目录下创建项目（`~/3D打印/openGrid-projects/日期-项目名/`）
2. **STL 管理**：将生成的 STL 文件复制到项目目录的 `stl/` 子目录（平铺，不分层）
3. **3MF 模板**：复制 `openGrid_h2d.3mf` 到项目目录
4. **HTML 打印计划**：生成好看的打印计划页面，包含所有项目信息

## 目录结构

```
~/3D打印/openGrid-projects/
└── 2026-02-20-kitchen-drawer/
    ├── project.yaml              # 项目元数据
    ├── print_plan.html          # 打印计划页面
    ├── openGrid_h2d.3mf         # 3MF 模板（从 skill 目录复制）
    └── stl/                     # STL 文件（平铺）
        ├── opengrid_7x5_Full_s2.stl
        └── opengrid_3x5_Full_s2.stl
```

## 配置

### config.yaml 新增项

```yaml
projects:
  # 项目根目录
  projects_dir: "~/3D打印/openGrid-projects"

  # 3MF 模板路径
  template_3mf: "openGrid_h2d.3mf"
```

## 数据结构

### project.yaml

```yaml
name: "kitchen-drawer"
created: "2026-02-20T10:30:00"
status: "pending"

# 抽屉信息
drawers:
  - width: 265
    depth: 365
    copies: 2

# 方案信息
scheme:
  x_splits: [7, 3]
  y_splits: [5, 5]
  tiles:
    - width: 7
      height: 5
      count: 4
      from_inventory: true
    - width: 3
      height: 5
      count: 4
      from_inventory: false

# 统计
stats:
  total_tiles: 8
  total_prints: 4
  total_time: "12.4 分钟"
  total_filament: "45.2g"

# 库存使用
inventory_usage:
  "7x5": 4

# STL 文件列表
stl_files:
  - "stl/opengrid_7x5_Full_s2.stl"
  - "stl/opengrid_3x5_Full_s2.stl"
```

## 模块设计

### 1. ProjectManager 扩展

位置：`opengrid/project/manager.py`

新增方法：

```python
class ProjectManager:
    def create_print_project(self, name, scheme_data, drawer_specs, stl_files):
        """创建打印项目

        Args:
            name: 项目名称
            scheme_data: 方案数据（包含 tiles, stats 等）
            drawer_specs: 抽屉规格列表
            stl_files: STL 文件路径列表

        Returns:
            project_path: 项目目录路径
        """
        # 1. 创建项目目录
        # 2. 复制 3MF 模板
        # 3. 复制 STL 文件（平铺）
        # 4. 生成 project.yaml
        # 5. 生成 print_plan.html
```

### 2. 数据准备模块

位置：`opengrid/ui/presenter.py`

```python
def prepare_project_data(scheme_json, drawer_specs, stl_files):
    """准备传递给项目生成的数据

    Returns:
        dict: 包含所有 HTML 渲染需要的数据
    """
```

### 3. HTML 生成

使用 frontend-design skill 制作好看的打印计划页面。

## HTML 打印计划功能

### 页面结构

1. **项目头部**
   - 项目名称、创建时间
   - 状态标签

2. **基本信息卡片**
   - 抽屉尺寸 × 份数
   - 分割方案
   - 打印机信息

3. **拼接示意图**
   - SVG 可视化

4. **瓦片清单**
   - 按尺寸分组
   - 库存/需打印 标签
   - 数量统计

5. **STL 文件列表**
   - 文件名
   - 点击打开文件

6. **3MF 模板**
   - 打开模板按钮

7. **打印参数建议**
   - 推荐层高
   - 填充率
   - 打印温度

## 流程

```
Agent:
1. 用户选择方案
2. 调用 slicer.py 生成 STL
3. 调用 ProjectManager.create_print_project()
   - 创建项目目录
   - 复制 3MF 模板
   - 复制 STL 文件
   - 生成 project.yaml
   - 生成 print_plan.html
4. 展示项目路径和 HTML 入口
```

## 错误处理

- 项目目录已存在：询问是否覆盖或创建新名称
- 3MF 模板文件不存在：警告，跳过复制
- STL 文件不存在：警告，跳过该文件

## 后续步骤

1. 扩展 ProjectManager
2. 添加 config 配置项
3. 使用 frontend-design skill 制作 HTML 模板
4. 更新 SKILL.md 流程文档
