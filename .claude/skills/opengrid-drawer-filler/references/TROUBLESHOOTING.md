# 故障排除

## 配置文件读不到

**Q: 报 `未找到 opengrid_config.yaml`？**

脚本只在当前工作目录查找配置文件。确保：

1. 当前 shell 在仓库根目录（有 `opengrid_config.yaml` 的目录）
2. 或者用 `-c /绝对路径/opengrid_config.yaml` 指定

```bash
# 看看现在在哪
pwd && ls opengrid_config.yaml
```

**Q: 报 `项目未初始化`？**

打开 `opengrid_config.yaml`，确认顶部有 `initialized: true`。本仓库 ship 出来的默认配置就是 true，除非有人手改了。

## 库存读不到

**Q: `inventory list` 显示库存为空但记得加过？**

确认配置的 `inventory_path` 指的就是当前操作的文件：

```bash
grep inventory_path opengrid_config.yaml   # 看配置
cat inventory.json                          # 看实际文件
```

**Q: 想手动改 `inventory.json` 行不行？**

不行。必须走 `uv run scripts/opengrid.py inventory add/deduct/undo`——日志（`log` 数组）丢了就没法审计和回溯了。

## 算不出方案

**Q: 报 "无法生成有效方案"？**

- 抽屉太小（< 28mm 单边）：openGrid 最小单元 28mm，放不下
- 抽屉太大且分割数超限：当前上限 20 块瓦片，再切就拒了
- 单边超过打印机 `max_x * tile_size`：需要换更大打印机或减小瓦片

## STL 生成失败

**Q: `slicer generate` 报 OpenSCAD 找不到？**

```bash
# macOS:
brew install --cask openscad@snapshot

# 还要装 BOSL2 库
git clone https://github.com/revarwin/BOSL2 \
  "$HOME/Library/Application Support/OpenSCAD/libraries/BOSL2"
```

**Q: `slicer slice` 或 `slicer open` 报未实现？**

是的，这俩子命令是占位符。原因：OrcaSlicer CLI 在 macOS 上需要 GUI 上下文，无法无头运行。

**替代方案**：生成 STL 后手动拖进 OrcaSlicer/BambuStudio 打开切片。

## 方案算出来不符合直觉

**Q: 两个方案算出来一模一样？**

如果 `opengrid_config.yaml` 配了 `inventory_path`，`split` 默认会用库存。要算"不考虑库存"的方案 A，必须加 `--no-inventory`：

```bash
# 方案 A：忽略库存
uv run scripts/opengrid.py split 225x255 --no-inventory --json > a.json

# 方案 B：用库存
uv run scripts/opengrid.py split 225x255 --json > b.json
```

**Q: 为什么算法选了独特尺寸更多的方案？**

算法优先级：最小化独特尺寸 → 最小化瓦片总数 → 最大化均衡度。如果"用库存"模式覆盖了某些尺寸，整体打印次数下降，可能会接受更多独特尺寸。详见 [ALGORITHM.md](ALGORITHM.md)。
