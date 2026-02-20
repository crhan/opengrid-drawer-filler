# Print Project Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 STL 生成后自动创建项目目录，包含 STL 文件、3MF 模板和打印计划 HTML 页面

**Architecture:** 扩展现有的 ProjectManager，添加创建打印项目的方法；在 config 中添加项目目录配置；使用 frontend-design skill 制作 HTML 模板

**Tech Stack:** Python, Jinja2, YAML, HTML/CSS

---

## Task 1: Update config.yaml with project settings

**Files:**
- Modify: `config/config.yaml`
- Modify: `config/config.example.yaml`

**Step 1: Add project settings to config.yaml**

```yaml
# 在 config.yaml 末尾添加
projects:
  # 项目根目录
  projects_dir: "~/3D打印/openGrid-projects"

  # 3MF 模板路径 (相对于 skill 目录)
  template_3mf: "openGrid_h2d.3mf"
```

**Step 2: Update example config**

在 `config/config.example.yaml` 末尾添加相同配置

---

## Task 2: Create test for ProjectManager

**Files:**
- Create: `tests/test_project.py`

**Step 1: Write failing test**

```python
import pytest
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from opengrid.project.manager import ProjectManager


class TestProjectManager:
    def test_create_project_with_stl_files(self):
        """Test creating project with STL files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pm = ProjectManager(tmpdir)

            # Mock scheme data
            scheme_data = {
                "scheme": {
                    "x_splits": [7, 3],
                    "y_splits": [5, 5],
                    "tiles": [
                        {"width": 7, "height": 5, "count": 4, "from_inventory": True},
                        {"width": 3, "height": 5, "count": 4, "from_inventory": False},
                    ]
                },
                "stats": {
                    "total_tiles": 8,
                    "total_prints": 4,
                    "total_time": "12.4 分钟",
                    "total_filament": "45.2g"
                },
                "inventory_usage": {"7x5": 4}
            }

            drawer_specs = [{"width": 265, "depth": 365, "copies": 2}]

            # Create temp STL files for testing
            stl_dir = Path(tmpdir) / "stl_temp"
            stl_dir.mkdir()
            stl_file = stl_dir / "test.stl"
            stl_file.write_text("dummy stl")

            project_path = pm.create_print_project(
                name="test-project",
                scheme_data=scheme_data,
                drawer_specs=drawer_specs,
                stl_files=[str(stl_file)]
            )

            # Verify project structure
            assert (project_path / "project.yaml").exists()
            assert (project_path / "print_plan.html").exists()
            assert (project_path / "stl" / "test.stl").exists()
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
.venv/bin/python -m pytest tests/test_project.py -v
```

Expected: FAIL (module doesn't exist or method doesn't exist)

---

## Task 3: Extend ProjectManager with create_print_project method

**Files:**
- Modify: `opengrid/project/manager.py`

**Step 1: Add imports and update class**

```python
import shutil
import yaml
from datetime import datetime
from pathlib import Path

class ProjectManager:
    def __init__(self, projects_dir, template_3mf_path=None, skill_dir=None):
        self.projects_dir = Path(projects_dir).expanduser()
        self.template_3mf_path = template_3mf_path
        self.skill_dir = Path(skill_dir) if skill_dir else Path(__file__).parent.parent

    def create_print_project(self, name, scheme_data, drawer_specs, stl_files):
        """Create a print project with STL files and HTML plan

        Args:
            name: Project name
            scheme_data: Scheme data dict with keys: scheme, stats, inventory_usage
            drawer_specs: List of drawer specs
            stl_files: List of STL file paths to copy

        Returns:
            Path: Project directory path
        """
        # 1. Create project directory with date prefix
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        project_path = self.projects_dir / f"{date_prefix}-{name}"
        project_path.mkdir(parents=True, exist_ok=True)

        # 2. Create stl subdirectory
        stl_dir = project_path / "stl"
        stl_dir.mkdir(exist_ok=True)

        # 3. Copy STL files (flattened)
        for stl_path in stl_files:
            src = Path(stl_path)
            if src.exists():
                dst = stl_dir / src.name
                shutil.copy2(src, dst)

        # 4. Copy 3MF template if exists
        if self.template_3mf_path:
            template_src = Path(self.template_3mf_path)
            if template_src.exists():
                shutil.copy2(template_src, project_path / template_src.name)

        # 5. Save project.yaml
        self._save_project_yaml(project_path, name, scheme_data, drawer_specs, stl_files)

        # 6. Generate HTML plan
        self._generate_html_plan(project_path, name, scheme_data, drawer_specs, stl_files)

        return project_path

    def _save_project_yaml(self, project_path, name, scheme_data, drawer_specs, stl_files):
        """Save project.yaml"""
        tiles = scheme_data.get("scheme", {}).get("tiles", [])

        config = {
            "name": name,
            "created": datetime.now().isoformat(),
            "status": "pending",
            "drawers": drawer_specs,
            "scheme": scheme_data.get("scheme", {}),
            "stats": scheme_data.get("stats", {}),
            "inventory_usage": scheme_data.get("inventory_usage", {}),
            "stl_files": [f"stl/{Path(f).name}" for f in stl_files]
        }

        with open(project_path / "project.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def _generate_html_plan(self, project_path, name, scheme_data, drawer_specs, stl_files):
        """Generate HTML print plan"""
        from opengrid.ui.presenter import generate_print_plan_html

        generate_print_plan_html(
            project_path=project_path,
            project_name=name,
            scheme_data=scheme_data,
            drawer_specs=drawer_specs,
            stl_files=stl_files
        )
```

---

## Task 4: Create presenter module for HTML data preparation

**Files:**
- Create: `opengrid/ui/presenter.py`

**Step 1: Create presenter module**

```python
"""HTML presenter for print plan"""

import json
from pathlib import Path


def prepare_project_data(project_name, scheme_data, drawer_specs, stl_files):
    """Prepare data for HTML template

    Args:
        project_name: str
        scheme_data: dict with scheme, stats, inventory_usage
        drawer_specs: list of drawer specs
        stl_files: list of STL file paths

    Returns:
        dict: Data for template rendering
    """
    scheme = scheme_data.get("scheme", {})
    stats = scheme_data.get("stats", {})
    inventory_usage = scheme_data.get("inventory_usage", {})

    # Prepare tiles with source info
    tiles = scheme.get("tiles", [])
    for tile in tiles:
        key = f"{tile['width']}x{tile['height']}"
        tile['from_inventory'] = key in inventory_usage

    # Prepare drawer info
    drawer_info = []
    for d in drawer_specs:
        drawer_info.append({
            "width": d["width"],
            "depth": d["depth"],
            "copies": d.get("copies", 1)
        })

    # Prepare STL files info
    stl_info = []
    for f in stl_files:
        p = Path(f)
        stl_info.append({
            "name": p.name,
            "path": f"stl/{p.name}",
            "size": p.stat().st_size if p.exists() else 0
        })

    return {
        "project_name": project_name,
        "drawers": drawer_info,
        "scheme": scheme,
        "stats": stats,
        "tiles": tiles,
        "inventory_usage": inventory_usage,
        "stl_files": stl_info,
    }


def generate_print_plan_html(project_path, project_name, scheme_data, drawer_specs, stl_files):
    """Generate HTML print plan

    Args:
        project_path: Path to project directory
        project_name: str
        scheme_data: dict
        drawer_specs: list
        stl_files: list
    """
    from opengrid.ui.visualizer import Visualizer

    data = prepare_project_data(project_name, scheme_data, drawer_specs, stl_files)

    # Generate SVG
    v = Visualizer()
    scheme = scheme_data.get("scheme", {})
    svg = v.generate_assembly_svg(scheme)

    # For now, use simple HTML generation
    # Will be replaced with frontend-design in Task 5
    html = _generate_simple_html(data, svg)

    with open(project_path / "print_plan.html", 'w', encoding='utf-8') as f:
        f.write(html)


def _generate_simple_html(data, svg):
    """Generate simple HTML (placeholder for frontend-design)"""
    from jinja2 import Template

    template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>openGrid 打印计划 - {{ project_name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .tile-grid { display: flex; gap: 12px; flex-wrap: wrap; }
        .tile { padding: 16px; border-radius: 8px; color: white; text-align: center; }
        .from-inventory { background: #11998e; }
        .need-print { background: #eb3349; }
        .stl-list a { display: block; padding: 8px; color: #667eea; }
    </style>
</head>
<body>
    <h1>📦 openGrid 打印计划</h1>
    <p>{{ project_name }}</p>

    <div class="card">
        <h2>抽屉信息</h2>
        {% for drawer in drawers %}
        <p>{{ drawer.width }}×{{ drawer.depth }}mm × {{ drawer.copies }}份</p>
        {% endfor %}
    </div>

    <div class="card">
        <h2>拼接示意图</h2>
        {{ svg|safe }}
    </div>

    <div class="card">
        <h2>瓦片清单</h2>
        <div class="tile-grid">
            {% for tile in tiles %}
            <div class="tile {% if tile.from_inventory %}from-inventory{% else %}need-print{% endif %}">
                {{ tile.width }}×{{ tile.height }} × {{ tile.count }}
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h2>STL 文件</h2>
        <div class="stl-list">
            {% for stl in stl_files %}
            <a href="{{ stl.path }}" target="_blank">{{ stl.name }}</a>
            {% endfor %}
        </div>
    </div>
</body>
</html>'''

    t = Template(template)
    return t.render(**data, svg=svg)
```

**Step 2: Run tests**

```bash
cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
.venv/bin/python -m pytest tests/test_project.py -v
```

Expected: PASS

---

## Task 5: Design HTML with frontend-design skill

**Files:**
- Modify: `opengrid/ui/presenter.py`

**Step 1: Invoke frontend-design skill**

Use the frontend-design skill to create a beautiful print plan HTML.

**Step 2: Replace simple HTML with designed HTML**

Replace `_generate_simple_html` with the designed HTML template.

---

## Task 6: Integrate with slicer workflow

**Files:**
- Modify: `scripts/slicer.py` or SKILL.md

**Step 1: Document new workflow**

Update SKILL.md to include the new project creation step:

```
### Step 5: 创建项目目录 (新增)

用户选择方案后，除了生成 STL，还可以创建项目目录：

调用 ProjectManager：

```python
from opengrid.project.manager import ProjectManager
from opengrid.config import load_config

config = load_config()
pm = ProjectManager(
    projects_dir=config['projects']['projects_dir'],
    template_3mf_path=config['projects']['template_3mf']
)

project_path = pm.create_print_project(
    name="kitchen-drawer",
    scheme_data=scheme_json,
    drawer_specs=[{"width": 265, "depth": 365, "copies": 2}],
    stl_files=["path/to/stl1.stl", "path/to/stl2.stl"]
)
```
```

---

## Task 7: Run full integration test

**Files:**
- Test: Full workflow

**Step 1: Test end-to-end**

```bash
# 1. Generate STL
.venv/bin/python scripts/slicer.py -g 7x5x2 3x5x2

# 2. Test project creation
.venv/bin/python -c "
from opengrid.project.manager import ProjectManager
pm = ProjectManager('~/3D打印/openGrid-projects', 'openGrid_h2d.3mf')
path = pm.create_print_project('test', {...}, [{'width': 265, 'depth': 365, 'copies': 2}], ['stl/file.stl'])
print(f'Project created: {path}')
"
```

---

## Task 8: Commit

```bash
git add -A
git commit -m "feat: add print project generator with HTML plan"
```
