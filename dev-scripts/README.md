# 开发辅助脚本

本目录包含开发过程中使用的辅助脚本，这些脚本不是项目正常运行所必需的，主要用于调试、测试和开发辅助。

## 保留脚本

| 脚本 | 描述 | 状态 |
|------|------|------|
| `print_plan.py` | 打印计划输出工具，从 JSON 生成多种格式输出 | ✅ 正常 |
| `verify_scenarios.py` | 库存感知评分系统验证脚本 | ✅ 正常 |
| `integration_test.py` | 端到端集成测试脚本 | ✅ 正常 |

## 已删除脚本

以下脚本已被删除（功能重复、导入错误或不再需要）：

- `3mf_utils.py` - 3MF 文件操作（Bambu Studio 特定功能）
- `config_summary.py` - 配置摘要（功能简单）
- `init.py` - 交互初始化（不再需要）
- `printer.py` - 打印机预设（未被实际使用）
- `project_manager.py` - 项目管理（未被使用）
- `scheme_presenter.py` - 方案展示（功能重复）
- `stl_manager.py` - STL 管理（与 slicer.py 重复）
- `summary.py` - 摘要函数（功能重复）

## 使用说明

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行验证脚本
python3 dev-scripts/verify_scenarios.py --list
python3 dev-scripts/verify_scenarios.py 5

# 运行集成测试
python3 dev-scripts/integration_test.py --list
python3 dev-scripts/integration_test.py 1

# 生成打印计划
python3 dev-scripts/print_plan.py plan.json --text --png --html
```
