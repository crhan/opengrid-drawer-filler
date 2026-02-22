# 配置文件详解

## 配置文件位置

- 主配置: `config/config.yaml`
- 配置模板: `config/config.example.yaml`

## 配置模板

```yaml
# 基本设置
initialized: true
printer:
  model: p1s # 打印机型号 (a1_mini, a1, p1p, p1s, x1c, x1e, h2d)
  bed_x: 256 # 热床宽度 mm
  bed_y: 256 # 热床深度 mm
  max_z: 256 # 最大打印高度 mm

# openGrid 参数
opengrid:
  tile_type: Full # 瓦片类型 (Full, Half)
  stacking_method: Ironing # 堆叠方式 (Ironing, Flat)

# 输出设置
output:
  stl_dir: "~/Documents/opengrid/stls/"
  projects_dir: "~/Documents/opengrid/projects/"

# 库存管理（可选）
inventory:
  enabled: true
  file: "inventory.yaml"
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
| h2d | 300 | 300 | 300 |

## 瓦片类型

- `Full`: 完整瓦片，适合常规抽屉
- `Half`: 半高瓦片，适合需要节省材料的场景

## 堆叠方式

- `Ironing`: 熨烫方式堆叠（推荐）
- `Flat`: 平铺方式堆叠
