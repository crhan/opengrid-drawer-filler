# 命令参考

## split_calc.py - 方案计算

### 批量计算

```bash
# 格式1: 宽x高:份数（推荐）
python3 scripts/split_calc.py -b "265x365:2 325x365:2"

# 格式2: 宽x高（默认1份）
python3 scripts/split_calc.py -b "265x365 325x365"

# 格式3: 宽 高 份数（空格分隔）
python3 scripts/split_calc.py -b "265 365 2 325 365 2"
```

### 单尺寸计算

```bash
python3 scripts/split_calc.py 485 425        # 指定尺寸
python3 scripts/split_calc.py 485 425 -c 3   # 指定份数
python3 scripts/split_calc.py -p klean      # 使用预设
python3 scripts/split_calc.py 485 425 -j    # JSON 输出
```

### 预设尺寸

```bash
--list-presets                          # 列出所有预设
-p klean                                # Klean件盒 270×170mm
-p ikea-sunda                           # IKEA Sunda 360×500mm
-p ikea-kal                             # IKEA KAL 360×500mm
-p ikea-alex                            # IKEA Alex 360×500mm
-p standard                             # 标准抽屉 400×400mm
```

## slicer.py - STL 生成

```bash
# 假设方案输出 7x5:3 和 10x5:3
python3 scripts/slicer.py -g 7x5x3 10x5x3

# 在 slicer 中打开
python3 scripts/slicer.py -o file.stl --slicer orca
python3 scripts/slicer.py -o file.stl --slicer bambu
```

## 项目管理

```bash
# 创建项目
python3 scripts/project_manager.py create "my-project" "265x365:2"

# 列出项目
python3 scripts/project_manager.py list
```

## 测试

```bash
# 运行所有测试
.venv/bin/python -m pytest

# 运行特定测试文件
.venv/bin/python -m pytest tests/test_scheme.py

# 运行特定测试
.venv/bin/python -m pytest tests/test_scheme.py::TestFindBestScheme::test_no_split_needed
```
