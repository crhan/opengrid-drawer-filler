# Slicer 模块拆分设计方案

**日期**: 2026-02-19
**目标**: 将 `split_calc.py` 中的 slicer 相关逻辑拆分到独立模块

## 背景

`split_calc.py` 当前同时包含：
1. 分割计算逻辑（瓦片分割、耗材估算）
2. STL 生成逻辑（OpenSCAD 调用）
3. 切片逻辑（Bambu Studio / Orca Slicer 集成）

拆分后职责更清晰，AI 也更容易分别调用。

## 架构

```
scripts/
├── split_calc.py    # 保留：计算逻辑（分割方案、耗材估算）
├── slicer.py        # 新增：STL 生成和切片相关功能
└── 3mf_utils.py     # 现有：3MF 工具函数
```

## 新模块 slicer.py

### 函数清单

| 函数 | 说明 | 从 split_calc 移出 |
|------|------|-------------------|
| `generate_stl(width, height, stacks, verbose, force)` | OpenSCAD 生成单个 STL | 是 |
| `generate_all_stls(scheme, copies, verbose, force)` | 批量生成 STL | 是 |
| `slice_with_bambu(stl_paths, output_name, ...)` | Bambu Studio 切片 | 是 |
| `slice_with_orca(stl_paths, output_name, ...)` | Orca Slicer 切片 | 是 |
| `open_in_slicer(stl_paths, slicer)` | 在 slicer 中打开文件 | 是 |

### 常量（共享）

以下常量需要保留在 split_calc.py 或提取到共享配置：
- `OPENSCAD_PATH`
- `SCAD_FILE`
- `OUTPUT_DIR`
- `BAMBU_STUDIO_PATH`
- `BAMBU_OUTPUT_DIR`
- `BAMBU_DEFAULT_PRINT_SETTINGS`
- `ORCA_SLICER_PATH`
- `ORCA_OUTPUT_DIR`
- `ORCA_MACHINE_PRESET`
- `ORCA_PROCESS_PRESET`
- `ORCA_FILAMENT_PRESET`

建议方案：这些路径常量保留在 slicer.py 中，split_calc.py 不再需要。

### CLI 接口

```bash
# 生成 STL（支持多种格式）
python3 scripts/slicer.py -g "path/to/file.stl"
python3 scripts/slicer.py --generate 7x5:3 10x5:3
python3 scripts/slicer.py --generate --width 7 --height 5 --stacks 3

# 切片 STL
python3 scripts/slicer.py --slice "file1.stl" "file2.stl" --slicer orca
python3 scripts/slicer.py --slice "file.stl" --slicer bambus --output my_project

# 在 slicer 中打开
python3 scripts/slicer.py --open "file1.stl" "file2.stl" --slicer orca
```

### 参数设计

| 参数 | 说明 |
|------|------|
| `-g, --generate` | 生成 STL |
| `--slice` | 切片 STL 文件 |
| `-o, --open` | 在 slicer 中打开 |
| `--slicer` | 选择 slicer (bambu/orca) |
| `-v, --verbose` | 详细输出 |
| `-f, --force` | 强制重新生成 |

## split_calc.py 变更

### 移除的参数

- `-g, --generate`
- `-s, --slice`
- `-o, --open`
- `--slicer`
- `--print-settings`
- `--machine-settings`
- `-f, --force`

### 保留的功能

- 分割计算（`find_best_scheme`）
- 耗材估算（`calculate_filament_and_time`）
- 批量模式（`batch_mode`）
- JSON 输出（`output_json`）
- 预设支持（`PRESETS`）

### 输出变更

原有的 `-g` 输出 STL 路径功能移除后，用户需要手动调用 slicer.py。

## SKILL.md 更新

更新文档反映新的工作流：

1. **分步工作流**
   - `split_calc.py` → 计算分割方案，输出 JSON
   - `slicer.py` → 根据方案生成 STL

2. **新增 slicer.py 使用说明**

3. **移除混合调用方式**
   - 不再支持 `split_calc.py -g` 一步完成

## 实现步骤

1. 创建 `scripts/slicer.py`，复制相关函数
2. 添加 CLI 参数解析
3. 从 `split_calc.py` 移除 slicer 相关代码
4. 更新 `tests/test_split_calc.py`（如有必要）
5. 更新 `SKILL.md` 文档
6. 测试两个脚本独立运行

## 风险与注意事项

1. **向后兼容性** - 移除参数会导致现有调用失败，需在文档中说明
2. **常量重复** - 路径常量可能需要在多处保持同步
3. **测试覆盖** - 确保拆分后的模块独立可用
