# openGrid 初始化流程改进计划

> **For Claude:** 使用 `superpowers:executing-plans` 逐步执行此计划。

**目标：** 改进初始化流程，在 split_calc 和 skill 入口统一检查配置，支持非交互环境和默认配置。

**方案：** 在 config.py 添加 `ensure_initialized()` 函数，处理检查和引导逻辑。修改 split_calc.py 和 slicer.py 入口调用该函数。

**技术栈：** Python, YAML, OpenSCAD

---

## Task 1: 修改 config.py

**Files:**
- 修改: `scripts/config.py`

**Step 1: 添加 sys 导入**

文件顶部添加：
```python
import sys
```

**Step 2: 添加 get_bambu_printers 函数**

在 `is_initialized()` 后添加：

```python
def get_bambu_printers():
    """从 BambuStudio.conf 读取已配置的打印机"""
    import re

    conf_path = Path.home() / "Library/Application Support/BambuStudio/BambuStudio.conf"
    if not conf_path.exists():
        return []

    try:
        with open(conf_path) as f:
            content = f.read()
            match = re.search(r'"user_bed_type_list"\s*:\s*\{([^}]+)\}', content)
            if not match:
                return []

            printers = []
            for line in match.group(1).split('\n'):
                key_match = re.search(r'"([^"]+)"\s*:', line)
                if key_match:
                    name = key_match.group(1)
                    model = None
                    if "A1 mini" in name:
                        model = "a1_mini"
                    elif "H2D" in name:
                        model = "h2d"
                    elif "P1P" in name:
                        model = "p1p"
                    elif "P1S" in name:
                        model = "p1s"
                    elif "X1C" in name:
                        model = "x1c"
                    elif "X1E" in name:
                        model = "x1e"
                    elif "A1" in name:
                        model = "a1"

                    if model:
                        printers.append({"name": name, "model": model})
            return printers
    except Exception:
        return []
```

**Step 3: 添加 ensure_initialized 函数**

```python
def ensure_initialized():
    """检查初始化状态，未初始化则提示并退出"""
    if is_initialized():
        return

    config_path = get_config_path()

    print("\n" + "=" * 50)
    print("openGrid 初始化检查")
    print("=" * 50)
    print()
    print("请先完成以下步骤：")
    print()
    print("1) 运行 setup.sh 安装依赖")
    print("   cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler")
    print("   ./scripts/setup.sh")
    print()

    printers = get_bambu_printers()

    print("2) 复制配置文件")
    print("   cp config.example.yaml config.yaml")
    print()

    example_path = config_path.parent / "config.example.yaml"
    if example_path.exists():
        print("【默认配置】")
        with open(example_path) as f:
            example = yaml.safe_load(f)
            example["initialized"] = True
            example["output"]["stl_dir"] = "~/Documents/opengrid/"
            print(f"   initialized: true")
            print(f"   output.stl_dir: {example['output']['stl_dir']}")

        if printers:
            print()
            print("【检测到的打印机】")
            for i, p in enumerate(printers, 1):
                print(f"   {i}) {p['name']} → {p['model']}")
            print()
            print("在 config.yaml 中设置 printer.model")
        else:
            print()
            print("   printer.model: <选择型号>")
            print("   opengrid.tile_type: Full")
            print("   opengrid.stacking_method: Ironing")

    print()
    print("编辑 config.yaml 完成配置后重新运行。")
    print("=" * 50)
    sys.exit(1)
```

**Step 4: 提交**

```bash
git add scripts/config.py
git commit -m "feat: add ensure_initialized with Bambu printer detection"
```

---

## Task 2: 修改 split_calc.py

**Files:**
- 修改: `scripts/split_calc.py:1009-1019`

**Step 1: 替换入口检查逻辑**

将：
```python
if __name__ == "__main__":
    from config import is_initialized, reload_config
    if not is_initialized():
        print("尚未初始化，正在启动初始化流程...")
        import init
        init.main()
        reload_config()
    main()
```

改为：
```python
if __name__ == "__main__":
    from config import ensure_initialized, reload_config
    ensure_initialized()
    reload_config()
    main()
```

**Step 2: 提交**

```bash
git add scripts/split_calc.py
git commit -m "refactor: use ensure_initialized instead of init.main"
```

---

## Task 3: 修改 slicer.py

**Files:**
- 修改: `scripts/slicer.py`

**Step 1: 添加入口检查**

```bash
grep -n "__main__" scripts/slicer.py
```

在入口处添加 `ensure_initialized()` 调用。

**Step 2: 提交**

```bash
git add scripts/slicer.py
git commit -m "feat: add initialization check to slicer.py"
```

---

## Task 4: 更新 SKILL.md

**Files:**
- 修改: `SKILL.md`

**Step 1: 添加初始化说明**

```markdown
## 初始化

首次使用前完成配置：

1. 运行 setup.sh：
   ```bash
   cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
   ./scripts/setup.sh
   ```

2. 复制配置文件：
   ```bash
   cp config.example.yaml config.yaml
   ```

3. 编辑 config.yaml，设置 `initialized: true` 和打印机型号

未配置时运行会显示详细步骤。
```

**Step 2: 提交**

```bash
git add SKILL.md
git commit -m "docs: add initialization instructions"
```

---

## Task 5: 测试验证

**Step 1: 测试未初始化提示**

```bash
# 备份配置
cp config.yaml config.yaml.bak

# 临时禁用初始化
# 删除 config.yaml 或将 initialized 设为 false

# 测试
python3 scripts/split_calc.py 485 425
```

预期：显示初始化提示

**Step 2: 测试正常流程**

```bash
# 恢复配置
cp config.yaml.bak config.yaml

# 测试
python3 scripts/split_calc.py 485 425
```

预期：正常显示计算结果

**Step 3: 提交**

```bash
git commit -m "test: verify initialization flow"
```

---

## 总结

| Task | 内容 |
|------|------|
| 1 | config.py 添加 ensure_initialized（含打印机检测） |
| 2 | split_calc.py 入口调用 |
| 3 | slicer.py 入口调用 |
| 4 | 更新 SKILL.md |
| 5 | 测试验证 |

**计划保存于 `docs/plans/2026-02-20-init-flow-improvement.md`**

执行方式：

1. **子任务模式** - 我逐个调度任务，完成后审查
2. **并行会话** - 在新会话中批量执行
