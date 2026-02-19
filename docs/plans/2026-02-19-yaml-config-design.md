# YAML 配置文件设计

## 目标

为 skill 添加 YAML 配置文件系统，支持用户自定义输出路径、打印机参数等。

## 文件结构

```
config.example.yaml    # 模板文件（提交到git）
config.yaml           # 用户配置文件（不提交到git，添加到.gitignore）
```

## 配置内容

### 必需配置

```yaml
output:
  stl_dir: "~/3D打印/opengrid/"           # STL 输出目录
```

### 打印机配置

```yaml
printer:
  # 机型预设或自定义
  model: "P1P"                             # 或 custom

  # 自定义参数（当 model=custom 时使用）
  custom:
    bed_x: 256
    bed_y: 256
    max_z: 256
```

### openGrid 参数（可选，有默认值）

```yaml
opengrid:
  tile_type: "Full"           # Full / Lite / Heavy
  stacking_method: "Ironing"   # Ironing / Interface Layer
  interface_separation: 0.2
  tile_size: 28
```

### 软件路径（可选，有默认值）

```yaml
software:
  openscad: "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
  bambustudio: "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
  orca: "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"
```

## Bambu 机型预设

| 机型 | bed_x | bed_y | max_z |
|------|-------|-------|-------|
| a1_mini | 120 | 120 | 120 |
| a1 | 180 | 180 | 180 |
| p1p | 256 | 256 | 256 |
| p1s | 256 | 256 | 256 |
| x1c | 256 | 256 | 256 |
| x1e | 256 | 256 | 256 |
| h2d | 300 | 300 | 300 |

## 初次使用问题

用户在首次使用 skill 时需要回答：

1. **STL 文件输出到哪里？** - 用户输入路径
2. **打印机选哪个？** - 从预设选择或自定义输入
3. **openGrid 类型用哪个？** - Full / Lite / Heavy

## 实现要点

- 配置文件使用 `yaml` 库读取
- 优先加载 `config.yaml`，缺失则使用代码内硬编码默认值
- 添加 `config.yaml` 到 `.gitignore`
- 代码中使用配置替换现有的硬编码路径常量
