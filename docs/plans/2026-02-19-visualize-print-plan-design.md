# openGrid 打印计划可视化设计

## 背景

当前 `split_calc.py` 承担了过多职责：计算分割方案、输出文本、生成 JSON。为了保持单一职责原则，将展示输出逻辑拆分到独立脚本。

## 目标

优化输出打印计划的视觉效果，用图形展示切分后的 opengrid 瓦片拼接方式。

## 架构

### 职责划分

| 脚本 | 职责 |
|------|------|
| `scripts/split_calc.py` | 只负责计算分割方案，输出 JSON 方案数据 |
| `scripts/print_plan.py` (新) | 消费方案数据，生成文本/Markdown/HTML/PNG 等多种格式 |

### 数据接口

通过 JSON 进行解耦：

```json
{
  "drawer": { "width": 485, "depth": 425 },
  "grid": { "x": 17, "y": 15 },
  "scheme": {
    "x_parts": 2,
    "y_parts": 1,
    "x_splits": [9, 8],
    "y_splits": [15],
    "tiles": [
      { "width": 9, "height": 15, "count": 1 },
      { "width": 8, "height": 15, "count": 1 }
    ]
  },
  "stats": { ... }
}
```

## 功能设计

### 1. 命令行接口

```bash
# 基础用法：读取 JSON 方案文件
python3 scripts/print_plan.py plan.json

# 生成可视化
python3 scripts/print_plan.py plan.json --visualize

# 生成 HTML 报告
python3 scripts/print_plan.py plan.json --html

# 批量模式：处理多个方案
python3 scripts/print_plan.py plan1.json plan2.json --html --png

# 管道输入
cat plan.json | python3 scripts/print_plan.py --visualize
```

### 2. 输出格式

#### 文本 (默认)
- 现有终端输出格式
- 简化的 ASCII 排布图

#### Markdown 报告
- 标题、尺寸信息
- 内嵌 base64 拼接示意图
- 瓦片清单表格
- 耗材估算

#### HTML 报告
- 可交互拼接图（悬停显示瓦片详情）
- 批量模式下可切换查看不同抽屉
- 响应式布局

#### PNG 图片
- 拼接示意图：自适应画布，不同尺寸瓦片用不同颜色
- 瓦片清单图：按尺寸分组展示

### 3. 颜色映射

根据瓦片尺寸动态计算颜色：

```python
def get_tile_color(size_key, all_sizes):
    """尺寸越大颜色越暖（蓝->红）"""
    min_size = min(all_sizes)
    max_size = max(all_sizes)
    normalized = (size_key - min_size) / (max_size - min_size)
    hue = 240 * (1 - normalized)  # 240=蓝, 0=红
    return f"hsl({hue}, 70%, 60%)"
```

### 4. 批量模式

- 每个抽屉尺寸单独生成拼接图
- 额外生成"合并清单图"对比所有尺寸

## 文件结构

```
scripts/
├── split_calc.py      # 现有，负责计算
├── print_plan.py      # 新增，负责展示
└── visualizer.py      # 新增，可视化核心模块

output/                 # 默认输出目录
├── {width}x{depth}/
│   ├── assembly.png
│   ├── assembly.html
│   ├── tiles.png
│   └── tiles.html
└── merged/
    ├── assembly_1.png
    ├── assembly_2.png
    └── merged_tiles.png
```

## 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| PNG 生成 | Pillow | Python 内置图像库，稳定可靠 |
| HTML 生成 | Jinja2 | 模板化，易于维护 |
| 交互 | 原生 SVG + JavaScript | 无需额外依赖 |

## 实现计划

1. 创建 `scripts/visualizer.py` - 可视化核心模块
2. 创建 `scripts/print_plan.py` - 主脚本，解析参数、调用 visualizer
3. 修改 `split_calc.py` - 支持 `-o json` 输出到文件而非 stdout
4. 添加测试

## 验收标准

- [ ] `python3 scripts/print_plan.py plan.json` 输出文本计划
- [ ] `python3 scripts/print_plan.py plan.json --html` 生成 HTML 报告
- [ ] `python3 scripts/print_plan.py plan.json --visualize` 生成 PNG 图片
- [ ] 批量模式正常工作
- [ ] 拼接图清晰展示瓦片尺寸和颜色区分
