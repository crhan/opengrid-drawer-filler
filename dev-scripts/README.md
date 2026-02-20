# 开发辅助脚本

本目录包含开发过程中使用的辅助脚本，这些脚本不是项目正常运行所必需的，主要用于调试、测试和开发辅助。

## 脚本列表

| 脚本 | 描述 | 状态 |
|------|------|------|
| `print_plan.py` | 打印计划输出工具，从 JSON 生成多种格式输出 | ✅ 可运行 |
| `printer.py` | 打印机预设常量定义 | ✅ 可运行（无主函数） |
| `3mf_utils.py` | 3MF 文件操作工具 | ⚠️ 需参数 |
| `config_summary.py` | 配置摘要工具 | ⚠️ 无主函数 |
| `init.py` | 初始化脚本 | ❌ 导入错误 |
| `integration_test.py` | 集成测试脚本 | ❌ 导入错误 |
| `project_manager.py` | 项目管理工具 | ⚠️ 无主函数 |
| `scheme_presenter.py` | 方案展示工具 | ⚠️ 无主函数 |
| `stl_manager.py` | STL 管理工具 | ❌ 导入错误 |
| `summary.py` | 摘要函数 | ❌ 导入错误 |
| `verify_scenarios.py` | 场景验证脚本 | ❌ 导入错误 |

## 使用说明

这些脚本主要用于开发调试，一般不需要直接运行。如需使用，请确保 Python 环境已正确配置：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行脚本
python3 dev-scripts/<script_name>.py
```

### 可直接运行的脚本

**print_plan.py** - 打印计划输出工具：
```bash
# 从文件生成
python3 dev-scripts/print_plan.py plan.json --text --png --html

# 从 stdin 读取
cat plan.json | python3 dev-scripts/print_plan.py --stdin --text
```

**printer.py** - 打印机预设（作为模块导入使用）：
```python
from dev_scripts.printer import PRINTER_PRESETS
```

### 状态说明

- ✅ 可运行：脚本可以正常执行
- ⚠️ 需参数/无主函数：脚本需要传入参数或作为模块导入使用
- ❌ 导入错误：脚本有导入路径问题，需要修复

## 注意事项

- 这些脚本的导入路径可能需要根据实际目录结构调整
- 部分脚本依赖 `opengrid` 核心库，请确保库已正确安装
- 建议优先使用 `scripts/` 目录中的正式脚本
