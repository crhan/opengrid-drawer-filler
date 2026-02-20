# Slicer 集成

## Orca Slicer CLI

**注意**: Orca Slicer CLI 在 macOS 上需要显示上下文（OpenGL），无法无头运行。

**已测试的功能**:

- `--arrange 1` - 自动排列模型
- `--load-settings` - 加载机器/工艺设置
- `--load-filaments` - 加载耗材设置
- `--export-3mf` - 导出 3MF 项目

**当前限制**: CLI 需要 GUI 环境运行，无法在服务器/无界面环境使用。

## 替代方案

1. **直接打开 STL**: 使用 `-o` 选项在 OrcaSlicer/BambuStudio 中打开生成的 STL
2. **手动排版**: 在 slicer 中手动排列模型并选择预设
3. **使用 3MF 模板**: 手动创建包含预设的 3MF 项目，后续复用

## 使用示例

```bash
# 在 OrcaSlicer 中打开 STL
python3 scripts/slicer.py -o output.stl --slicer orca

# 在 BambuStudio 中打开 STL
python3 scripts/slicer.py -o output.stl --slicer bambu
```
