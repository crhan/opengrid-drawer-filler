# opengrid-drawer-filler

根据抽屉的物理尺寸（mm），算出怎么用 [openGrid](https://www.printables.com/model/openGrid) 28mm 网格瓦片把它铺满，**最少独特尺寸 → 最少瓦片数 → 最均衡**。可一键生成 STL 给切片器。

这是一个 **clone-and-use 的个人 3D 打印工具**，不是发布到 PyPI 的库。Claude Code 用户克隆之后直接通过 `.claude/skills/opengrid-drawer-filler` 用上，让 Agent 帮你算方案。

## 它解决什么问题

家里有个 325×460mm 的抽屉，想 3D 打印 openGrid 瓦片铺满做收纳——
但抽屉比打印机床还大，得切几块？怎么切最省时间、最少种类？库存里已经有 6×6 一片、8×8 两片，能不能用上？

把尺寸丢给工具：

```bash
uv run scripts/opengrid.py split 325x460
```

它告诉你：用 `3×8 × 2` + `8×8 × 2` 铺满，其中 8×8 直接用库存的两片，还需要打 `3×8` 两块（一次性垂直堆叠两层一盘搞定）。需要 STL？

```bash
uv run scripts/opengrid.py slicer generate 3x8x2
```

直接出文件到 `~/3D打印/opengrid/openGrid_Full_3x8x2.stl`，丢进 BambuStudio/OrcaSlicer 排版打印。

## 首次准备

```bash
git clone --recurse-submodules https://github.com/crhan/opengrid-drawer-filler
cd opengrid-drawer-filler
uv sync
```

生成 STL 还需要 **OpenSCAD + BOSL2 库**。最省心的办法是让 Claude Code 调 `/opengrid-drawer-filler-setup` skill 一键搞定；手动装也行：

```bash
brew install --cask openscad@snapshot
git submodule update --init --recursive   # 拉 QuackWorks SCAD 源码
# 再从 https://github.com/BelfrySCAD/BOSL2 把 BOSL2 装到
# ~/Library/Application Support/OpenSCAD/libraries/BOSL2/
```

## 常用命令

```bash
# 看打印机配置 + 库存
uv run scripts/opengrid.py status
uv run scripts/opengrid.py status --json     # Agent 友好

# 算分割
uv run scripts/opengrid.py split 325x460
uv run scripts/opengrid.py split 325x460 --json > scheme.json
# JSON 输出含 slicer_commands 数组，Agent 拿到直接 exec 即可

# 多个抽屉批量算（合并优化）
uv run scripts/opengrid.py split -b "265x365:2 325x460"

# 库存管理（严格禁止手改 inventory.json）
uv run scripts/opengrid.py inventory list
uv run scripts/opengrid.py inventory add 8x8:5 --reason "收货"
uv run scripts/opengrid.py inventory deduct 8x8:2 --reason "施工 325x460 抽屉"
uv run scripts/opengrid.py inventory undo

# 生成 STL（WxHxS：宽 cells × 深 cells × 垂直堆叠层数）
uv run scripts/opengrid.py slicer generate 7x5x2
uv run scripts/opengrid.py slicer generate 7x5x2 -v   # 打印 OpenSCAD 命令行
uv run scripts/opengrid.py slicer generate 7x5x2 -f   # 已存在文件强制重生

# 方案对比（HTML 报告）
uv run scripts/opengrid.py compare scheme_a.json scheme_b.json -o compare.html

# 项目目录（一次设计任务的方案 + STL + 文档放一起）
uv run scripts/opengrid.py project create kitchen-drawer 325x460
uv run scripts/opengrid.py project list
```

## 跟 Claude Code 一起用

仓库里的 `.claude/skills/opengrid-drawer-filler/SKILL.md` 描述了完整的 Agent 工作流——用户给 Agent 一个尺寸，Agent 自动调上面这些 CLI、把人话表格 / JSON 翻译给用户、问要不要扣库存、最后生成 STL。设计原则是 **"Agent 负责用户交互，脚本负责计算和生成"**——脚本不含 `input()`。

工作流详情见 [.claude/skills/opengrid-drawer-filler/SKILL.md](.claude/skills/opengrid-drawer-filler/SKILL.md)，
项目内部约定见 [CLAUDE.md](CLAUDE.md)。

## 测试

```bash
uv run pytest                            # 全量单元测试（默认跳过 integration）
uv run pytest -m integration             # 跑真实 OpenSCAD 渲染（需 setup 完成）
```

## 依赖致谢

- [QuackWorks](https://github.com/AndyLevesque/QuackWorks) by Andy Levesque——openGrid 的 OpenSCAD 实现（作为 git submodule）
- [BOSL2](https://github.com/BelfrySCAD/BOSL2)——OpenSCAD 标准库
- openGrid 标准本身：<https://www.printables.com/model/openGrid>
