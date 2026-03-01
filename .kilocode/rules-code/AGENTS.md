# Code Mode Rules (Non-Obvious Only)

## 核心常量修改
- `opengrid/core/constants.py` 中的 `MAX_X`, `MAX_Y`, `TILE_SIZE` 等是全局变量
- 修改配置后必须调用 `recalculate_derived_constants()` 重新计算
- 这些全局变量影响所有后续计算，调用顺序很重要

## 配置缓存
- `opengrid/config.py` 使用全局变量 `_config` 缓存配置
- 测试时修改配置后调用 `reload_config()` 清除缓存
- CLI 参数 `-c` 和 `-i` 指定的路径会覆盖缓存

## 库存文件
- **禁止直接编辑** `inventory.json`
- 必须通过 CLI 命令修改：`uv run scripts/opengrid.py inventory add/deduct`
- 直接编辑会导致日志不一致

## 尺寸解析
- 支持 `x` 和 `×`（Unicode U+00D7）两种乘号
- 两种格式等效：`265x365` = `265×365`
