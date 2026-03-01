# Architect Mode Rules (Non-Obvious Only)

## 架构特点
- 这是一个 Claude Code 插件（Skill 系统），不是传统应用
- 核心 Python 库 (`opengrid/`) + CLI 入口 (`scripts/opengrid.py`) + Agent 技能 (`skills/`)
- 分离设计：Agent 负责交互，脚本负责计算

## 全局可变状态
- `opengrid/core/constants.py` 中的核心常量是全局变量
- `recalculate_derived_constants()` 修改全局状态，影响所有后续计算
- 需要注意调用顺序，避免意外的状态污染

## 配置架构
- 仅支持项目级配置（不是全局配置）
- 配置缓存机制：全局变量 `_config` 缓存配置
- CLI 参数 `-c` 和 `-i` 可以覆盖缓存路径

## 库存管理架构
- 每个项目独立管理库存（通过 `inventory_path` 配置）
- 严格禁止直接编辑库存文件，必须通过 CLI
- 每次操作记录日志，保持一致性
