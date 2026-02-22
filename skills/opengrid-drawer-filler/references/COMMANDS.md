# 命令参考

## split_calc.py - 方案计算

### 基本用法

```bash
# 单尺寸计算
python3 scripts/split_calc.py 485 425

# 指定份数
python3 scripts/split_calc.py 485 425 -c 3

# 批量计算（多个尺寸）
python3 scripts/split_calc.py 265x365:2 325x365:2
```

### 库存使用

```bash
# 使用库存（通过 -i 指定库存文件）
python3 scripts/split_calc.py 265x365:2 -i inventory.json

# 不使用库存
python3 scripts/split_calc.py 265x365:2 -i ""

# 库存文件为空时效果等同于不使用库存
```

### 输出选项

```bash
# JSON 输出
python3 scripts/split_calc.py 485 425 -j

# 详细输出
python3 scripts/split_calc.py 485 425 -v

# 使用预设
python3 scripts/split_calc.py -p klean
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

## inventory.py - 库存管理

**注意**：必须在项目目录下运行（与 opengrid_config.yaml 同一目录）

```bash
# 查看库存
python3 scripts/inventory.py list

# 添加库存 (格式: 宽x高:数量)
python3 scripts/inventory.py add 8x8:5 6x7:3 "入库原因：购买新材料"

# 扣减库存
python3 scripts/inventory.py deduct 8x8:2 "扣减原因：打印使用"

# 撤销上次操作
python3 scripts/inventory.py undo
```

## slicer.py - STL 生成

```bash
# 生成 STL（指定瓦片尺寸和层数）
python3 scripts/slicer.py -g 7x5x3 10x5x3

# 在 slicer 中打开
python3 scripts/slicer.py -o file.stl --slicer orca
python3 scripts/slicer.py -o file.stl --slicer bambu
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
