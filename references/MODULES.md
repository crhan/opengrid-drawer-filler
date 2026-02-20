# 模块 API

## 方案计算

```python
from scripts.split_calc import find_best_scheme, get_grid_dimensions

x, y = get_grid_dimensions(485, 425)
scheme = find_best_scheme(x, y)
```

## STL 生成

```python
from scripts.slicer import generate_stl, generate_all_stls

path, err = generate_stl(7, 5, 3, verbose=True, force=False)
```

## 项目管理

```python
from scripts.project_manager import ProjectManager

pm = ProjectManager("~/opengrid_projects/")
project_path = pm.create_project("my-project", drawers)
```

## HTML 生成

```python
from scripts.visualizer import Visualizer

v = Visualizer()
v.generate_html(project_path, scheme, tiles)
```

## 库存管理

```python
from scripts.inventory import Inventory

inv = Inventory("inventory/inventory.json")
inv.load()
inv.add("7x5", 5)
inv.save()
```

## 配置加载

```python
from scripts.config import load_config

config = load_config()
printer = config["printer"]
```
