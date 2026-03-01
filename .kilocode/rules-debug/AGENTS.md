# Debug Mode Rules (Non-Obvious Only)

## 测试超时
- 测试超时设置为 **5秒/测试**
- 超过5秒的测试会被 pytest-timeout 终止
- 运行单个测试：`uv run pytest tests/test_xxx.py::TestClass::test_method`

## 配置问题排查
- 配置文件必须在项目目录中，不是全局配置
- 使用 `-c` 参数指定配置文件路径排查配置加载问题
- 调用 `reload_config()` 清除缓存后重新加载

## 库存问题排查
- 使用 `-i` 参数指定库存文件
- 库存文件路径在配置中指定（inventory_path）
- 检查日志文件追踪库存变更历史

## 常量问题排查
- `MAX_X`, `MAX_Y` 由 `bed_x / TILE_SIZE` 和 `bed_y / TILE_SIZE` 计算得出
- 检查 `recalculate_derived_constants()` 是否被正确调用
- 全局常量修改会影响所有后续计算
