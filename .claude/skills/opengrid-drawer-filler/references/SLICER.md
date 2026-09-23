# Slicer 集成

## 现状：自动生成项目 3MF（未切片）

`uv run scripts/opengrid.py slicer 3mf WxHxS` 纯 Python 把 STL 打包成 BambuStudio 项目 3MF，
预设取自模板 `opengrid/stl/templates/h2d_pla_support.project_settings.config`（H2D + Opengrid堆叠打印 +
PLA 本体 / Support For PLA/PETG 接触面）。实现见 `opengrid/stl/threemf.py`。

打开后在 BambuStudio 里点切片即可，不用再手动选预设、耗材。

## 更新模板

模板来自打印机实际打过的项目：ha-bambulab 集成会把每次打印的 `.gcode.3mf` 缓存在
`~/config/homeassistant/www/media/ha-bambulab/*/prints/`，从里面挑一个效果好的，取出
`Metadata/project_settings.config` 覆盖模板即可；同时把 `threemf.py` 的 `_APP_VERSION`
改成该文件 `version` 字段（数组形状随 BambuStudio 版本变，必须一致）。

也可以在 BambuStudio 里另存一个项目 3MF，取同一个文件。

## 切片（未实现）

BambuStudio / OrcaSlicer CLI 需要图形上下文（OpenGL），无头环境跑不了，所以 3MF 里不含 G-code。
