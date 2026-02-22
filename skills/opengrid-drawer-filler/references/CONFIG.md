# 配置文件详解

## 配置文件位置

openGrid 使用项目级配置文件 `opengrid_config.yaml`，必须在项目目录下存在。

## 配置模板

```yaml
# 初始化状态 (设为 true 表示已完成配置)
initialized: true

# 打印机配置
printer:
  model: p1s # 打印机型号 (a1_mini, a1, p1p, p1s, x1c, x1e, h2d)
  # 或使用自定义尺寸:
  # custom:
  #   bed_x: 300
  #   bed_y: 320
  #   max_z: 325

# openGrid 参数
opengrid:
  tile_type: Full # 瓦片类型 (Full, Lite, Heavy)
  stacking_method: Ironing # 堆叠方式 (Ironing, Interface)
  interface_separation: 0.2 # 层间间隙 (mm)
  tile_size: 28 # 网格单元格大小 (mm)

# 输出设置
output:
  stl_dir: "~/3D打印/opengrid/"

# 库存管理 (必需)
inventory_path: "./inventory.json"
```

## 打印机预设

| 型号 | bed_x | bed_y | max_z |
|------|-------|-------|-------|
| a1_mini | 120 | 120 | 120 |
| a1 | 180 | 180 | 180 |
| p1p | 256 | 256 | 256 |
| p1s | 256 | 256 | 256 |
| x1c | 256 | 256 | 256 |
| x1e | 256 | 256 | 256 |
| h2d | 300 | 320 | 325 |

## 瓦片类型

- `Full`: 完整瓦片 (6.8mm)，适合常规抽屉
- `Lite`: 轻量瓦片 (4.0mm)，适合节省材料
- `Heavy`: 重型瓦片 (13.8mm)，适合承重需求

## 堆叠方式

- `Ironing`: 熨烫方式堆叠（推荐），每层带熨烫
- `Interface`: 接口层方式，层间有薄支撑

## 重要说明

1. 配置文件必须在项目目录下（与 `inventory.json` 同一目录）
2. 运行脚本时必须切换到项目目录
3. 库存文件路径通过 `inventory_path` 指定，可以是相对路径或绝对路径
