# split_calc.py CLI 参数简化设计

**Date:** 2026-02-20
**Status:** Approved
**Target:** split_calc.py 重构

## 目标

简化 `split_calc.py` 的 CLI 参数语法，统一单尺寸和批量模式的入口。

## 当前问题

当前有两种运行模式，需要不同的参数格式：

```bash
# 单尺寸模式
python split_calc.py 485 425

# 批量模式
python split_calc.py -b "265x365:2 325x365:2"
```

这导致了：
- 用户学习成本高
- 代码维护两份相似的逻辑
- 输入解析逻辑重复

## 新设计

### CLI 语法

```bash
# 单尺寸
python split_calc.py 485x425
python split_calc.py 485x425 -c 3          # 指定份数

# 多个尺寸（自动识别为批量模式）
python split_calc.py 485x425 265x365:2 325x365

# 预设
python split_calc.py -p klean
python split_calc.py -p klean -c 2         # 预设 + 份数
```

### 参数格式

| 格式 | 示例 | 解析结果 |
|------|------|----------|
| `宽x高` | `485x425` | (485, 425, 1) |
| `宽x高:份数` | `265x365:2` | (265, 365, 2) |
| 预设 | `-p klean` | (270, 170, 1) |

### 模式选择逻辑

1. 解析所有位置参数为尺寸列表
2. 如果有 `-p` 预设参数，预设尺寸加入列表
3. 根据尺寸数量自动选择模式：
   - 1个尺寸 → 单尺寸模式
   - 2+尺寸 → 批量模式

### 移除的参数

- 移除位置参数 `width depth`（两个独立数字）
- 移除 `-b/--batch`（不再需要，参数数量自动决定）

### 保留的参数

- `-c/--copies` - 全局份数（每个尺寸都用此份数）
- `-p/--preset` - 预设
- `-i/--inventory` - 库存文件
- `-j/--json` - JSON 输出
- `-v/--verbose` - 详细输出
- `--list-presets` - 列出预设

## 实现要点

### 1. 统一解析器

创建 `parse_dimensions(args)` 函数：

```python
def parse_dimensions(args):
    """解析位置参数为尺寸列表"""
    items = []
    for arg in args:
        match = re.match(r'(\d+)x(\d+)(?::(\d+))?', arg)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            c = int(match.group(3)) if match.group(3) else 1
            items.append((w, h, c))
    return items
```

### 2. 主函数重构

```python
def main():
    # 解析参数
    dims = parse_dimensions(args.dimensions)  # 位置参数列表

    # 如果有预设，加入列表
    if args.preset:
        preset_dims = parse_preset(args.preset)
        dims.extend(preset_dims)

    # 全局份数覆盖
    if args.copies:
        dims = [(w, h, args.copies) for w, h, c in dims]

    # 自动选择模式
    if len(dims) == 1:
        run_single_mode(dims[0])
    else:
        run_batch_mode(dims)
```

### 3. 内部逻辑复用

- `run_single_mode()` 调用现有的 `find_best_scheme` + `print_plan`
- `run_batch_mode()` 调用现有的 `batch_mode` 逻辑
- 核心计算函数保持不变

## 向后兼容

无。不再支持旧语法：
- `python split_calc.py 485 425`（两个独立数字）
- `python split_calc.py -b "265x365:2"`（显式批量标记）

## 测试用例

```bash
# 单尺寸
python split_calc.py 485x425
python split_calc.py 485x425 -c 3 -j

# 批量
python split_calc.py 485x425 265x365:2
python split_calc.py 265x365 325x365 -j

# 预设
python split_calc.py -p klean
python split_calc.py -p klean -c 2 -j
```
