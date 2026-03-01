# Ask Mode Rules (Non-Obvious Only)

## 项目结构
- 这是一个 Claude Code 插件项目
- 核心代码在 `opengrid/` 目录（Python 库）
- CLI 入口在 `scripts/opengrid.py`
- 技能定义在 `skills/opengrid-drawer-filler/`

## 配置位置
- 配置文件 `opengrid_config.yaml` 在**项目目录**中（用户项目，非插件目录）
- 插件本身没有全局配置文件
- 库存文件路径在配置的 `inventory_path` 中指定

## 文档位置
- 算法规则：`skills/opengrid-drawer-filler/references/ALGORITHM.md`
- 配置说明：`skills/opengrid-drawer-filler/references/CONFIG.md`
- 故障排除：`skills/opengrid-drawer-filler/references/TROUBLESHOOTING.md`

## 核心约束
- Agent 负责用户交互，脚本负责计算
- 脚本不含 `input()` 或交互式提示
- 库存修改必须通过 CLI 命令，禁止直接编辑
