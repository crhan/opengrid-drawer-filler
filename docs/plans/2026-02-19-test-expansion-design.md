# 测试用例扩展设计

**Date:** 2026-02-19
**Topic:** 扩展更完善的测试用例

## 目标

为 opengrid-drawer-filler 项目增加更完善的测试覆盖，包括边界条件、错误处理、批量输入解析等缺失的测试场景。

## 当前状态

- 现有 92 个测试
- 覆盖: 常量、网格计算、瓦片验证、分割算法、平衡评分、方案查找、统计、批量模式、库存管理

## 测试缺口

| 函数/模块 | 状态 |
|-----------|------|
| `parse_batch_input` | ❌ 未测试 |
| `list_presets` | ❌ 未测试 |
| `output_json` | ❌ 未测试 |
| 边界条件 | ❌ 不足 |
| 错误处理 | ❌ 不足 |

## 设计方案

### 方案: 增量扩展 + 边界测试

#### 1. 新增 `test_parse.py` - 批量输入解析测试

```python
class TestParseBatchInput:
    # 测试格式: "265x365:2"
    # 测试格式: "265x365x2"
    # 测试格式: "265 365 2"
    # 测试无效输入
    # 测试空输入
```

#### 2. 新增 `test_boundaries.py` - 边界条件测试

```python
class TestBoundaryConditions:
    # 最小尺寸测试 (TILE_SIZE * MIN_TILE)
    # 最大尺寸测试 (TILE_SIZE * MAX_X/Y)
    # 临界值测试
    # 极端比例测试

class TestErrorHandling:
    # 无效输入测试
    # 异常情况测试
```

#### 3. 扩展现有测试文件

- `test_integration.py`: 增加更多真实抽屉尺寸
- `test_scheme.py`: 增加更多方案组合测试
- `test_batch.py`: 增加更多批量场景

## 测试矩阵

| 类别 | 新增测试数 |
|------|-----------|
| 解析测试 | ~10 |
| 边界条件 | ~15 |
| 错误处理 | ~8 |
| 扩展现有 | ~10 |
| **总计** | **~43** |

## 预期结果

- 测试总数从 92 增加到 ~135
- 覆盖所有公开函数
- 包含边界条件和错误处理

## 实施步骤

1. 创建 `tests/test_parse.py`
2. 创建 `tests/test_boundaries.py`
3. 扩展 `test_integration.py`
4. 运行测试验证
5. 提交代码
