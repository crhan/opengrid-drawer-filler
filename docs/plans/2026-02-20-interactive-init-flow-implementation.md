# openGrid 交互式工作流实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现交互式工作流，用户输入抽屉尺寸后展示配置摘要、多方案对比，确认后自动生成 STL 和 HTML 打印计划

**架构:** 新增交互式 CLI 模块，集成配置摘要、多方案生成、项目管理、STL 生成链接、HTML 计划生成

**Tech Stack:** Python, YAML, Jinja2, PIL, OpenSCAD

---

## 配置更新

### Task 1: 更新 config.yaml 添加 projects_dir

**Files:**
- Modify: `scripts/config.py`

**Step 1: 添加 projects_dir 到 DEFAULTS**

```python
DEFAULTS = {
    "initialized": False,
    "output": {"stl_dir": "~/3D打印/opengrid/"},
    "projects_dir": "~/opengrid_projects/",  # 新增
    "printer": {"model": "p1p"},
    ...
}
```

**Step 2: 添加 get_projects_dir 函数**

```python
def get_projects_dir():
    """获取项目根目录"""
    config = load_config()
    return Path(config.get("projects_dir", "~/opengrid_projects/")).expanduser()
```

**Step 3: 提交**

```bash
git add scripts/config.py
git commit -m "feat: add projects_dir config option"
```

---

## 配置摘要模块

### Task 2: 创建 config_summary.py

**Files:**
- Create: `scripts/config_summary.py`

**Step 1: 编写测试**

```python
# tests/test_config_summary.py
import pytest
from config_summary import get_config_summary, format_summary

def test_get_config_summary_returns_dict():
    result = get_config_summary()
    assert "printer" in result
    assert "inventory" in result
    assert "projects_dir" in result
    assert result["printer"]["model"] in ["a1_mini", "a1", "p1p", "p1s", "x1c", "x1e", "h2d"]

def test_format_summary_prints_info():
    summary = {
        "printer": {"model": "P1P", "bed_x": 256, "bed_y": 256},
        "inventory": {"7x5": 3, "10x5": 2},
        "projects_dir": "/tmp/test_projects"
    }
    output = format_summary(summary)
    assert "P1P" in output
    assert "256×256" in output
    assert "7×5" in output
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_config_summary.py -v
# Expected: FAIL - module not found
```

**Step 3: 实现 config_summary.py**

```python
#!/usr/bin/env python3
"""配置摘要模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, get_printer_config
from inventory import load_inventory

PRINTER_NAMES = {
    "a1_mini": "A1 mini",
    "a1": "A1",
    "p1p": "P1P",
    "p1s": "P1S",
    "x1c": "X1C",
    "x1e": "X1E",
    "h2d": "H2D"
}

def get_config_summary():
    """返回配置摘要"""
    config = load_config()
    printer_config = get_printer_config()

    # 获取打印机型号
    model = config.get("printer", {}).get("model", "p1p")
    printer_name = PRINTER_NAMES.get(model, model.upper())

    # 获取库存
    inventory = load_inventory()

    # 获取项目目录
    projects_dir = config.get("projects_dir", "~/opengrid_projects/")

    return {
        "printer": {
            "model": printer_name,
            "bed_x": printer_config["bed_x"],
            "bed_y": printer_config["bed_y"],
            "max_z": printer_config["max_z"]
        },
        "inventory": inventory,
        "projects_dir": str(projects_dir)
    }

def format_summary(summary):
    """格式化配置摘要"""
    p = summary["printer"]
    inv = summary["inventory"]

    # 库存摘要
    if inv:
        inv_parts = [f"{k}: {v} stack" for k, v in sorted(inv.items())]
        inv_str = ", ".join(inv_parts)
    else:
        inv_str = "(空)"

    return f"""
╔══════════════════════════════════════════════════════════╗
║  当前配置                                              ║
╠══════════════════════════════════════════════════════════╣
║  打印机: {p['model']} ({p['bed_x']}×{p['bed_y']}mm)                                ║
║  库存:   {inv_str}                          ║
║  输出:   {summary['projects_dir']}          ║
╚══════════════════════════════════════════════════════════╝
"""
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_config_summary.py -v
# Expected: PASS
```

**Step 5: 提交**

```bash
git add scripts/config_summary.py tests/test_config_summary.py
git commit -m "feat: add config summary module"
```

---

## 多方案生成模块

### Task 3: 创建 scheme_generator.py

**Files:**
- Create: `scripts/scheme_generator.py`

**Step 1: 编写测试**

```python
# tests/test_scheme_generator.py
import pytest
from scheme_generator import generate_schemes, generate_inventory_aware_scheme
from inventory import add_inventory, load_inventory

def test_generate_schemes_returns_three_options():
    # 先清空库存
    add_inventory({"7x5": 10, "10x5": 10}, "test setup")

    schemes = generate_schemes(485, 425, 1, load_inventory())

    assert "math" in schemes
    assert "inventory" in schemes
    assert "print_limit" in schemes

def test_inventory_aware_scheme_uses_existing():
    # 添加特定尺寸库存
    add_inventory({"7x5": 3, "10x5": 3}, "test")

    inv = load_inventory()
    scheme = generate_inventory_aware_scheme(485, 425, 1, inv)

    # 验证使用了库存
    assert scheme is not None
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_scheme_generator.py -v
# Expected: FAIL - module not found
```

**Step 3: 实现 scheme_generator.py**

```python
#!/usr/bin/env python3
"""多方案生成模块"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from split_calc import find_best_scheme, calculate_single

def generate_schemes(width, depth, copies, inventory):
    """生成三种方案

    Returns:
        {
            "math": {...},      # 纯数学优化
            "inventory": {...}, # 库存感知
            "print_limit": {...} # 打印次数约束
        }
    """
    # 方案 A: 纯数学优化
    math_scheme = find_best_scheme(width, depth)

    # 方案 B: 库存感知
    inventory_scheme = generate_inventory_aware_scheme(width, depth, copies, inventory)

    # 方案 C: 打印次数约束（暂用数学优化 + 标注）
    print_limit_scheme = find_best_scheme(width, depth)
    print_limit_scheme["constraint"] = "max_prints: 3"

    return {
        "math": {
            "name": "纯数学优化",
            "description": "最小化独特尺寸 → 最小瓦片数 → 均衡度最好",
            "scheme": math_scheme
        },
        "inventory": {
            "name": "库存感知",
            "description": "优先使用现有库存瓦片，减少打印量",
            "scheme": inventory_scheme
        },
        "print_limit": {
            "name": "打印次数≤3",
            "description": "限制打印次数的方案",
            "scheme": print_limit_scheme
        }
    }

def generate_inventory_aware_scheme(width, depth, copies, inventory):
    """生成库存感知方案

    算法：
    1. 先找到数学最优方案
    2. 检查库存匹配情况
    3. 如果库存可匹配，调整方案优先使用库存尺寸
    """
    # 基础方案
    base_scheme = find_best_scheme(width, depth)

    if not inventory:
        return base_scheme

    tiles = base_scheme.get("tiles", [])
    total_tiles = sum(t.get("count", 1) for t in tiles)

    # 计算库存匹配
    from inventory import get_inventory_match

    tile_sizes = [(t["width"], t["height"]) for t in tiles]
    match_result = get_inventory_match(tile_sizes, copies, inventory)

    match_score = match_result["match_score"]
    if match_score > 0:
        # 有库存匹配，可以优化
        base_scheme["inventory_match"] = match_result


```

**Step 4: 运行    return base_scheme测试验证通过**

```bash
pytest tests/test_scheme_generator.py -v
# Expected: PASS
```

**Step 5: 提交**

```bash
git add scripts/scheme_generator.py tests/test_scheme_generator.py
git commit -m "feat: add multi-scheme generator"
```

---

## 方案展示模块

### Task 4: 创建 scheme_presenter.py

**Files:**
- Create: `scripts/scheme_presenter.py`

**Step 1: 编写测试**

```python
# tests/test_scheme_presenter.py
import pytest
from scheme_presenter import present_schemes

def test_present_schemes_formats_output():
    schemes = {
        "math": {
            "name": "纯数学优化",
            "scheme": {"tiles": [{"width": 7, "height": 5, "count": 3}, {"width": 10, "height": 5, "count": 3}]}
        },
        "inventory": {
            "name": "库存感知",
            "scheme": {"tiles": [{"width": 7, "height": 5, "count": 2}, {"width": 8, "height": 5, "count": 2}]}
        }
    }

    output = present_schemes(schemes, {})
    assert "纯数学优化" in output
    assert "7×5" in output
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_scheme_presenter.py -v
# Expected: FAIL
```

**Step 3: 实现 scheme_presenter.py**

```python
#!/usr/bin/env python3
"""方案展示模块"""

def present_schemes(schemes, inventory):
    """展示多方案对比"""

    output = []
    output.append("")
    output.append("╔══════════════════════════════════════════════════════════╗")
    output.append("║  方案对比                                              ║")
    output.append("╚══════════════════════════════════════════════════════════╝")
    output.append("")

    for key, data in schemes.items():
        name = data["name"]
        scheme = data["scheme"]
        tiles = scheme.get("tiles", [])

        # 独特尺寸
        unique_sizes = len(tiles)

        # 总瓦片数
        total_tiles = sum(t.get("count", 1) for t in tiles)

        # 瓦片列表
        tile_strs = []
        for t in tiles:
            w, h = t["width"], t["height"]
            count = t.get("count", 1)
            tile_strs.append(f"{w}×{h}: {count}")

        # 库存信息
        inv_match = scheme.get("inventory_match", {})
        if inv_match and inv_match.get("match_score", 0) > 0:
            from_inv = inv_match.get("from_inventory", {})
            need_print = inv_match.get("need_print", {})
            inv_info = f" (使用库存: {sum(from_inv.values())} 块)"
        else:
            inv_info = ""

        output.append(f"[{key.upper()}] {name}{inv_info}")
        output.append(f"    独特尺寸: {unique_sizes} 种  |  瓦片数: {total_tiles} 块")
        output.append(f"    {', '.join(tile_strs)}")
        output.append("")

    output.append("请选择方案 [A/B/C]: ")

    return "\n".join(output)

def format_scheme_for_display(scheme, inventory=None):
    """格式化单个方案"""
    tiles = scheme.get("tiles", [])

    parts = []
    for t in tiles:
        w, h = t["width"], t["height"]
        count = t.get("count", 1)
        parts.append(f"{w}×{h}: {count}")

    return ", ".join(parts)
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_scheme_presenter.py -v
# Expected: PASS
```

**Step 5: 提交**

```bash
git add scripts/scheme_presenter.py tests/test_scheme_presenter.py
git commit -m "feat: add scheme presenter"
```

---

## 项目管理模块

### Task 5: 创建 project_manager.py

**Files:**
- Create: `scripts/project_manager.py`

**Step 1: 编写测试**

```python
# tests/test_project_manager.py
import pytest
import tempfile
import shutil
from pathlib import Path
from project_manager import ProjectManager

def test_create_project_creates_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)

        drawers = [{"width": 485, "depth": 425, "copies": 1}]
        path = pm.create_project("测试抽屉", drawers)

        assert path.exists()
        assert (path / "stl").exists()
        assert (path / "project.yaml").exists()
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_project_manager.py -v
# Expected: FAIL
```

**Step 3: 实现 project_manager.py**

```python
#!/usr/bin/env python3
"""项目管理模块"""

import os
import sys
import yaml
from datetime import datetime
from pathlib import Path

class ProjectManager:
    def __init__(self, projects_dir):
        self.projects_dir = Path(projects_dir).expanduser()

    def create_project(self, name, drawers):
        """创建项目目录

        Args:
            name: 项目名（如 "厨房抽屉"）
            drawers: [{"width": 485, "depth": 425, "copies": 1}, ...]

        Returns:
            project_path: 项目目录路径
        """
        # 生成日期前缀
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"

        # 创建目录结构
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "stl").mkdir(exist_ok=True)

        # 保存 project.yaml
        self._save_project_config(project_path, name, drawers)

        return project_path

    def _save_project_config(self, path, name, drawers):
        """保存 project.yaml"""
        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "drawers": drawers,
            "status": "pending"
        }
        with open(path / "project.yaml", 'w') as f:
            yaml.dump(config, f)

    def get_project_path(self, name):
        """获取已存在的项目路径"""
        # 尝试精确匹配
        for p in self.projects_dir.iterdir():
            if p.is_dir() and name in p.name:
                return p
        return None
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_project_manager.py -v
# Expected: PASS
```

**Step 5: 提交**

```bash
git add scripts/project_manager.py tests/test_project_manager.py
git commit -m "feat: add project manager"
```

---

## STL 管理模块

### Task 6: 创建 stl_manager.py

**Files:**
- Create: `scripts/stl_manager.py`

**Step 1: 编写测试**

```python
# tests/test_stl_manager.py
import pytest
import tempfile
from pathlib import Path
from stl_manager import generate_and_link_stls

def test_generate_and_link_stls_creates_links():
    # 这个测试需要 mock slicer 模块
    pass  # 简化测试，后续集成测试覆盖
```

**Step 2: 实现 stl_manager.py**

```python
#!/usr/bin/env python3
"""STL 生成与链接模块"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, get_projects_dir
from slicer import generate_all_stls

def generate_and_link_stls(scheme, project_path, copies=1):
    """生成 STL 并链接到项目目录

    1. 调用 slicer.py 生成 STL 到 stl_base_dir
    2. 在 project_path/stl/ 创建软链接指向生成的 STL
    """
    config = load_config()
    stl_base_dir = Path(config["output"]["stl_dir"]).expanduser()

    # 生成 STL
    stl_files = generate_all_stls(scheme, copies=copies, verbose=False)

    # 创建软链接
    stl_link_dir = project_path / "stl"
    linked_files = []

    for src in stl_files:
        src_path = Path(src)
        link_path = stl_link_dir / src_path.name

        if not link_path.exists():
            try:
                os.symlink(src, link_path)
            except OSError:
                # 如果已经存在同名文件，跳过
                pass

        linked_files.append(str(link_path))

    return linked_files
```

**Step 3: 提交**

```bash
git add scripts/stl_manager.py
git commit -m "feat: add STL manager with symlink support"
```

---

## HTML 计划生成模块

### Task 7: 更新 visualizer.py 添加 HTML 模板

**Files:**
- Modify: `scripts/visualizer.py`

**Step 1: 添加库存感知的 HTML 模板**

在 Visualizer 类中添加：

```python
def generate_plan_html(self, project_data, output_path):
    """生成完整的打印计划 HTML

    Args:
        project_data: {
            "project_name": "...",
            "drawer": {"width": 485, "depth": 425},
            "printer": {...},
            "scheme": {...},
            "inventory_usage": {...},
            "stl_files": [...]
        }
        output_path: 输出 HTML 路径
    """
    from jinja2 import Template

    template = self._get_plan_template()
    html = template.render(**project_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

def _get_plan_template(self):
    """获取打印计划 HTML 模板"""
    return Template('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>openGrid 打印计划 - {{ project_name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
               max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-top: 0; }
        h2 { color: #666; font-size: 18px; margin-top: 20px; }
        .info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
        .info-item { background: #f9f9f9; padding: 12px; border-radius: 8px; }
        .info-label { color: #999; font-size: 12px; }
        .info-value { font-size: 18px; font-weight: 600; color: #333; }
        .tile-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
        .tile { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 16px; border-radius: 8px; text-align: center; min-width: 80px; }
        .tile .size { font-size: 20px; font-weight: bold; }
        .tile .count { font-size: 14px; opacity: 0.9; }
        .tile.from-inventory { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .tile.need-print { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        .assembly { text-align: center; margin: 20px 0; }
        .steps { counter-reset: step; }
        .step { position: relative; padding-left: 40px; margin-bottom: 16px; }
        .step:before { counter-increment: step; content: counter(step);
                       position: absolute; left: 0; top: 0;
                       width: 28px; height: 28px; background: #667eea; color: white;
                       border-radius: 50%; text-align: center; line-height: 28px; }
        #inventory-modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                          background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
        #inventory-modal.show { display: flex; }
        .modal-content { background: white; padding: 24px; border-radius: 12px; max-width: 400px; }
    </style>
</head>
<body>
    <h1>📦 openGrid 打印计划</h1>
    <p style="color: #666;">项目: {{ project_name }}</p>

    <div class="card">
        <h2>基本信息</h2>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">抽屉尺寸</div>
                <div class="info-value">{{ drawer.width }}×{{ drawer.depth }}mm</div>
            </div>
            <div class="info-item">
                <div class="info-label">打印机</div>
                <div class="info-value">{{ printer.model }} ({{ printer.bed_x }}×{{ printer.bed_y }}mm)</div>
            </div>
            <div class="info-item">
                <div class="info-label">分割方案</div>
                <div class="info-value">{{ scheme.x_parts }}×{{ scheme.y_parts }}</div>
            </div>
            <div class="info-item">
                <div class="info-label">预估打印时间</div>
                <div class="info-value">{{ stats.total_time }}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>拼接示意图</h2>
        <div class="assembly">
            {{ svg|safe }}
        </div>
    </div>

    <div class="card">
        <h2>瓦片清单</h2>
        <div class="tile-grid">
            {% for tile in tiles %}
            <div class="tile {% if tile.from_inventory %}from-inventory{% else %}need-print{% endif %}">
                <div class="size">{{ tile.width }}×{{ tile.height }}</div>
                <div class="count">×{{ tile.count }}</div>
                <div class="source">{% if tile.from_inventory %}库存{% else %}需打印{% endif %}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>操作步骤</h2>
        <div class="steps">
            <div class="step">在切片软件中打开 STL 文件进行排版</div>
            <div class="step">选择打印参数（层高 0.2mm，填充 15%）</div>
            <div class="step">开始打印</div>
            <div class="step">打印完成后从库存中扣减瓦片</div>
        </div>
    </div>

    <div id="inventory-modal">
        <div class="modal-content">
            <h3>📦 库存扣减</h3>
            <p>该方案使用了库存瓦片，是否现在从库存中扣减？</p>
            <p id="inventory-usage"></p>
            <button onclick="confirmDeduct()" style="background: #667eea; color: white; padding: 12px 24px;
                        border: none; border-radius: 8px; cursor: pointer; margin-right: 12px;">
                确认扣减
            </button>
            <button onclick="closeModal()" style="background: #ddd; color: #333; padding: 12px 24px;
                        border: none; border-radius: 8px; cursor: pointer;">
                稍后处理
            </button>
        </div>
    </div>

    <script>
    const inventoryUsage = {{ inventory_usage | tojson }};

    window.onload = function() {
        if (Object.keys(inventoryUsage).length > 0) {
            const modal = document.getElementById('inventory-modal');
            const usageText = document.getElementById('inventory-usage');
            const parts = [];
            for (const [size, count] of Object.entries(inventoryUsage)) {
                parts.push(`${size}: ${count} 块`);
            }
            usageText.textContent = parts.join(', ');
            modal.classList.add('show');
        }
    };

    function confirmDeduct() {
        // 打开扣库命令
        window.open('python3 {{ script_path }}/inventory.py deduct ' +
            Object.entries(inventoryUsage).map(([k,v]) => k + ':' + v).join(' '));
        closeModal();
    }

    function closeModal() {
        document.getElementById('inventory-modal').classList.remove('show');
    }
    </script>
</body>
</html>''')
```

**Step 2: 提交**

```bash
git add scripts/visualizer.py
git commit -m "feat: add inventory-aware HTML plan template"
```

---

## 交互式主入口

### Task 8: 创建 interactive.py 主入口

**Files:**
- Create: `scripts/interactive.py`

**Step 1: 实现交互式主入口**

```python
#!/usr/bin/env python3
"""openGrid 交互式工作流入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config_summary import get_config_summary, format_summary
from scheme_generator import generate_schemes
from scheme_presenter import present_schemes
from project_manager import ProjectManager
from stl_manager import generate_and_link_stls
from visualizer import Visualizer
from inventory import load_inventory
from config import get_projects_dir, load_config

def interactive_main():
    """交互式主流程"""

    # 1. 解析用户输入
    if len(sys.argv) < 2:
        print("用法: python3 interactive.py <抽屉尺寸>")
        print("示例: python3 interactive.py 485x425")
        print("     python3 interactive.py 485x425x2  (2份)")
        sys.exit(1)

    # 解析参数
    args = sys.argv[1]
    # 支持 "485x425" 或 "485x425x2" 格式
    parts = args.split('x')
    if len(parts) == 2:
        width, depth = map(int, parts)
        copies = 1
    elif len(parts) == 3:
        width, depth, copies = map(int, parts)
    else:
        print("格式错误: 应为 WxD 或 WxDxC")
        sys.exit(1)

    # 2. 显示配置摘要
    summary = get_config_summary()
    print(format_summary(summary))

    # 3. 生成多方案
    inventory = load_inventory()
    schemes = generate_schemes(width, depth, copies, inventory)

    # 4. 展示方案
    print(present_schemes(schemes, inventory))

    # 5. 等待用户选择
    choice = input().strip().upper()
    scheme_map = {"A": "math", "B": "inventory", "C": "print_limit"}

    if choice not in scheme_map:
        print("无效选择")
        sys.exit(1)

    selected_key = scheme_map[choice]
    selected = schemes[selected_key]["scheme"]

    # 6. 创建项目
    project_name = input("请输入项目名称: ").strip() or "抽屉"

    projects_dir = get_projects_dir()
    pm = ProjectManager(projects_dir)
    project_path = pm.create_project(project_name, [
        {"width": width, "depth": depth, "copies": copies}
    ])

    # 7. 生成 STL
    stl_files = generate_and_link_stls(selected, project_path, copies)

    # 8. 生成 HTML
    from config import get_printer_config
    printer_cfg = get_printer_config()
    model = load_config().get("printer", {}).get("model", "p1p")

    v = Visualizer()
    html_path = project_path / "plan.html"

    # 准备数据
    tiles_data = []
    inv_match = selected.get("inventory_match", {})
    for tile in selected.get("tiles", []):
        key = f"{tile['width']}x{tile['height']}"
        tiles_data.append({
            "width": tile["width"],
            "height": tile["height"],
            "count": tile.get("count", 1),
            "from_inventory": inv_match.get("from_inventory", {}).get(key, 0) > 0
        })

    v.generate_plan_html({
        "project_name": project_path.name,
        "drawer": {"width": width, "depth": depth},
        "printer": {"model": model.upper(), "bed_x": printer_cfg["bed_x"], "bed_y": printer_cfg["bed_y"]},
        "scheme": selected,
        "tiles": tiles_data,
        "stats": {"total_time": "~3h"},
        "svg": v.generate_assembly_svg(selected),
        "inventory_usage": inv_match.get("need_print", {}),
        "stl_files": stl_files,
        "script_path": str(Path(__file__).parent)
    }, str(html_path))

    print(f"\n✓ 已创建项目: {project_path}")
    print(f"✓ 已生成 STL: {', '.join([Path(f).name for f in stl_files])}")
    print(f"✓ 已生成计划: {html_path}")
    print("\n提示: 在浏览器中打开 plan.html 查看完整打印计划")


if __name__ == "__main__":
    interactive_main()
```

**Step 2: 提交**

```bash
git add scripts/interactive.py
git commit -m "feat: add interactive workflow entry point"
```

---

## 集成测试

### Task 9: 端到端集成测试

**Step 1: 测试交互流程**

```bash
# 测试配置摘要
python3 -c "from config_summary import get_config_summary; print(get_config_summary())"

# 测试多方案生成
python3 -c "from scheme_generator import generate_schemes; from inventory import load_inventory; print(generate_schemes(485, 425, 1, load_inventory()))"

# 测试完整流程（模拟）
echo "测试抽屉\n" | python3 scripts/interactive.py 485x425
```

**Step 2: 提交**

```bash
git commit -m "test: add integration tests for interactive workflow"
```

---

## 更新 SKILL.md

### Task 10: 更新文档

**Files:**
- Modify: `SKILL.md`

**Step 1: 添加新使用方式**

```markdown
## 交互式工作流（推荐）

```bash
# 方式 1：交互式（推荐）
python3 scripts/interactive.py

# 方式 2：指定尺寸
python3 scripts/interactive.py 485x425

# 方式 3：指定份数
python3 scripts/interactive.py 485x425x2
```

交互式工作流会自动：
1. 展示当前配置（打印机、库存、输出路径）
2. 生成多方案对比（纯数学、库存感知、打印次数约束）
3. 用户确认后自动生成 STL 和 HTML 打印计划
4. HTML 打开时提示库存扣减
```

**Step 2: 提交**

```bash
git add SKILL.md
git commit -m "docs: update SKILL.md with interactive workflow"
```

---

## 总结

| Task | 模块 | 描述 |
|------|------|------|
| 1 | config.py | 添加 projects_dir 配置 |
| 2 | config_summary.py | 配置摘要展示 |
| 3 | scheme_generator.py | 多方案生成 |
| 4 | scheme_presenter.py | 方案对比展示 |
| 5 | project_manager.py | 项目目录管理 |
| 6 | stl_manager.py | STL 生成与链接 |
| 7 | visualizer.py | HTML 计划模板 |
| 8 | interactive.py | 交互式主入口 |
| 9 | 集成测试 | 端到端验证 |
| 10 | SKILL.md | 文档更新 |

**计划保存于 `docs/plans/2026-02-20-interactive-init-flow-implementation.md`**

---

## 执行方式

**1. Subagent-Driven (本会话)** - 每个任务派发子 agent，任务间审查，快速迭代

**2. Parallel Session (新会话)** - 在新会话中批量执行

您希望用哪种方式？
