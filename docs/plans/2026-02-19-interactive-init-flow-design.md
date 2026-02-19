# 交互式初始化流程设计

## 目标

为 opengrid-drawer-filler 创建交互式初始化流程，引导新用户完成首次设置。

## 触发条件

当 `config.yaml` 不存在或 `initialized: false` 时触发初始化流程。

## 交互流程

```
┌─────────────────────────────────────────────────────────────┐
│  初始化流程启动                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  步骤 1: 欢迎 + 介绍                                        │
│  ───────────────────────────────────────────────────────   │
│  - 欢迎使用 opengrid-drawer-filler                          │
│  - 简介：计算抽屉最优瓦片分割方案并生成 STL                  │
│                                                             │
│  步骤 2: 介绍 setup.sh 操作                                 │
│  ───────────────────────────────────────────────────────   │
│  脚本会执行以下 3 个操作：                                  │
│                                                             │
│  1) 安装 OpenSCAD@snapshot                                  │
│     - 通过 Homebrew Cask 安装最新开发版                     │
│     - OpenSCAD 用于生成 3D 模型                            │
│                                                             │
│  2) 克隆 QuackWorks 源码                                    │
│     - GitHub: https://github.com/AndyLevesque/QuackWorks   │
│     - 存放位置: vendor/QuackWorks/                          │
│     - 提供 openGrid 库                                       │
│                                                             │
│  3) 安装 BOSL2 库                                           │
│     - OpenSCAD 必装库                                        │
│     - 存放位置: ~/Library/Application Support/              │
│                 OpenSCAD/libraries/BOSL2                    │
│                                                             │
│  步骤 3: 用户确认                                            │
│  ───────────────────────────────────────────────────────   │
│  是否继续安装？[Y/n]                                         │
│                                                             │
│  步骤 4: 执行 setup.sh                                       │
│  ───────────────────────────────────────────────────────   │
│  运行: bash scripts/setup.sh                                │
│                                                             │
│  步骤 5: 解释 config.yaml                                    │
│  ───────────────────────────────────────────────────────   │
│                                                             │
│  1) output.stl_dir                                          │
│     - 含义: STL 文件输出目录                                 │
│     - 示例: ~/3D打印/opengrid/                              │
│                                                             │
│  2) printer.model                                           │
│     - 含义: 打印机型号                                       │
│     - 选项: a1_mini, a1, p1p, p1s, x1c, x1e, h2d, custom  │
│                                                             │
│  3) printer.custom                                          │
│     - 含义: 自定义打印机参数（当 model=custom 时）          │
│     - 参数: bed_x, bed_y, max_z                             │
│                                                             │
│  4) opengrid.tile_type                                      │
│     - 含义: 瓦片类型                                        │
│     - 选项: Full (6.8mm), Lite (4.0mm), Heavy (13.8mm)    │
│                                                             │
│  5) opengrid.stacking_method                                │
│     - 含义: 堆叠方式                                        │
│     - 选项: Ironing (熨平), Interface Layer (界面层)       │
│                                                             │
│  6) opengrid.interface_separation                           │
│     - 含义: 界面层间隙（mm）                                │
│     - 默认: 0.2                                             │
│                                                             │
│  步骤 6: 用户确认配置                                        │
│  ───────────────────────────────────────────────────────   │
│  - 逐项询问用户                                              │
│  - 提供默认值供选择                                          │
│                                                             │
│  步骤 7: 生成 config.yaml                                    │
│  ───────────────────────────────────────────────────────   │
│  - 写入用户确认的配置                                        │
│  - 设置 initialized: true                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## config.yaml 字段说明

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| initialized | 是 | false | 初始化标记 |
| output.stl_dir | 是 | ~/3D打印/opengrid/ | STL 输出目录 |
| printer.model | 是 | p1p | 打印机型号 |
| printer.custom | 否 | - | 自定义参数 |
| opengrid.tile_type | 否 | Full | 瓦片类型 |
| opengrid.stacking_method | 否 | Ironing | 堆叠方式 |
| opengrid.interface_separation | 否 | 0.2 | 界面间隙 |
| software.openscad | 否 | 系统默认 | OpenSCAD 路径 |

## 打印机预设

| 型号 | bed_x | bed_y | max_z |
|------|-------|-------|-------|
| a1_mini | 120 | 120 | 120 |
| a1 | 180 | 180 | 180 |
| p1p | 256 | 256 | 256 |
| p1s | 256 | 256 | 256 |
| x1c | 256 | 256 | 256 |
| x1e | 256 | 256 | 256 |
| h2d | 300 | 300 | 300 |

## 实现要点

1. **触发检测**: 在 config.py 中添加 `is_initialized()` 函数
2. **交互入口**: 创建 `scripts/init.py` 处理交互流程
3. **配置写入**: 使用 yaml 库生成 config.yaml
4. **错误处理**: 用户中断时保留 initialized: false
