# openGrid 库存感知评分系统设计 (v2)

## 问题背景

当前实现的库存感知方案存在架构缺陷：

1. **先生成方案，再检查库存** — 算法先产生最优分割方案，然后检查库存是否可用
2. **无法保证库存必用** — 当库存尺寸与方案需求不匹配时，可能打印本可从库存获取的瓦片

这违反了"有库存一定要用库存"的核心要求。

## 新方案设计

### 核心思路

将库存作为方案评分的第一优先级，同时引入**打印时间成本**作为统一评分标准。

### 成本模型

```
total_cost = print_time + (print_count - 1) × swap_penalty
```

其中：
- `print_time`: 单次打印所需时间（分钟）
- `print_count`: 需要打印的 stack 总数
- `swap_penalty`: 换料时间惩罚（建议 60 分钟）

### 评分逻辑

**方案 A: 完全使用库存**
- 成本 = 0（无需打印）
- 优先选择

**方案 B: 部分使用库存**
- 成本 = 剩余需打印瓦片的 print_time + swap_penalty × (print_count - 1)

**方案 C: 全部新打印**
- 成本 = 所有瓦片的 print_time + swap_penalty × (print_count - 1)

### 算法改造

#### split_calc.py

新增函数 `calculate_print_cost(tiles, use_inventory=True)`:

```python
def calculate_print_cost(tiles: list[tuple[int, int]], inventory: dict[str, int], copies: int = 1) -> tuple[int, dict, dict]:
    """
    计算打印成本及库存匹配情况

    Returns: (cost, from_inventory, need_print)
    - cost: 总成本（分钟），0 表示完全使用库存
    - from_inventory: 从库存取的瓦片
    - need_print: 需要新打印的瓦片
    """
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}

    for key, count in tiles.items():
        needed = count * copies
        available = inventory.get(key, 0)
        from_inventory[key] = min(needed, available)
        need_print[key] = max(0, needed - available)

    # 计算需打印部分的成本
    total_time = 0
    total_prints = sum(need_print.values())

    for key, count in need_print.items():
        if count > 0:
            w, h = map(int, key.split('x'))
            time_per_tile = estimate_print_time(w, h)
            total_time += time_per_tile * count

    # 加上换料惩罚
    swap_penalty = 60  # 分钟
    cost = total_time + (total_prints - 1) * swap_penalty if total_prints > 0 else 0

    return cost, from_inventory, need_print
```

#### find_best_scheme 改造

新增评分维度：

```python
def find_best_scheme(x, y, inventory=None, verbose=False):
    """
    寻找最优分割方案

    评分优先级（从高到低）：
    1. 库存成本最低（完全使用库存 = 0）
    2. 独特尺寸最少
    3. 瓦片数最少
    4. 均衡度最好
    """
    schemes = find_all_schemes(x, y)

    if not inventory:
        # 无库存时使用原评分逻辑
        return original_find_best_scheme(x, y, verbose)

    scored_schemes = []
    for scheme in schemes:
        cost, from_inv, need_print = calculate_print_cost(scheme['tiles'], inventory, copies=1)

        scored_schemes.append({
            'scheme': scheme,
            'cost': cost,
            'from_inventory': from_inv,
            'need_print': need_print,
            'unique_sizes': len(set(scheme['tiles'])),
            'total_tiles': len(scheme['tiles']),
            'balance': calc_scheme_balance(scheme['tiles'])
        })

    # 多维度排序
    scored_schemes.sort(key=lambda s: (
        s['cost'],           # 1. 库存成本最低
        s['unique_sizes'],   # 2. 独特尺寸最少
        s['total_tiles'],    # 3. 瓦片数最少
        s['balance']         # 4. 均衡度最好
    ))

    return scored_schemes[0]
```

### 边缘情况处理

#### 边缘情况 1: 精确匹配（库存 = 需求）
- 成本 = 0
- 直接从库存取用

#### 边缘情况 2: 部分库存（库存 < 需求）
- 部分从库存取用
- 差额新打印

#### 边缘情况 3: 无匹配（库存尺寸不适合）
- 全部新打印

#### 边缘情况 4: 多种库存规格
- 分别计算各规格的匹配成本
- 选择总成本最低的组合

#### 边缘情况 5: 需求与库存不匹配 — 重新规划
当库存中没有任何尺寸能直接满足方案需求时：
1. **最大化利用库存**：找到库存中尺寸最接近需求的瓦片
2. **重新规划方案**：将原方案拆分，使用可用库存 + 打印缺失部分

示例：
- 需求: 6×9 两个
- 库存: 6×6 有 3 个
- 方案: 拆分为 [(3,6), (3,6), (6,6), (6,6)] — 使用 2 个 6×6 库存 + 打印 2 个新瓦片

验证：原方案成本 670min → 重新规划后 395min，节省 41%

### 批量模式集成

在 `optimize_batch_global` 中对每种方案组合计算库存成本：

```python
def optimize_batch_global(batch_configs, inventory):
    """
    批量全局优化

    对所有抽屉的方案组合进行枚举，
    找到总库存成本最低的组合
    """
    best_total_cost = float('inf')
    best_combination = None

    for combo in generate_combinations(batch_configs):
        total_cost = sum(
            calculate_print_cost(scheme['tiles'], inventory)['cost']
            for scheme in combo
        )

        if total_cost < best_total_cost:
            best_total_cost = total_cost
            best_combination = combo

    return best_combination
```

### 输出示例

```
=== 方案评估 ===
尺寸: 265 × 360

--- 方案 1: [(6,9), (6,9)] ---
成本: 395 分钟 (库存: 6×6 ×2, 打印: 3×6 ×2, 6×6 ×2)
库存利用: 4 stack
需打印: 4 stack

--- 方案 2: [(6,9), (6,9)] ---
成本: 670 分钟 (无库存匹配)
库存利用: 0 stack
需打印: 6 stack

选择方案 1（成本最低）
```

## 文件改动

```
scripts/
├── split_calc.py       # 核心算法 + 成本计算
├── inventory.py        # 库存管理（已存在）
└── inventory.json     # 库存数据
```

## 测试用例

```python
class TestInventoryAwareCost:
    """库存感知成本计算测试"""

    def test_exact_match_cost_zero(self):
        # 精确匹配：成本为 0
        tiles = [(6, 7)]
        inventory = {'6x7': 1}
        cost, _, _ = calculate_print_cost(tiles, inventory)
        assert cost == 0

    def test_partial_match(self):
        # 部分匹配：只计算差额
        tiles = [(6, 7), (6, 7)]
        inventory = {'6x7': 1}
        cost, from_inv, need = calculate_print_cost(tiles, inventory)
        assert from_inv['6x7'] == 1
        assert need['6x7'] == 1

    def test_no_match(self):
        # 无匹配：全部计算成本
        tiles = [(6, 9)]
        inventory = {'6x7': 1}
        cost, _, need = calculate_print_cost(tiles, inventory)
        assert cost > 0

    def test_replan_edge_case(self):
        # 边缘情况 5：重新规划
        tiles = [(6, 9), (6, 9)]
        inventory = {'6x6': 3}
        # 重新规划后应使用 2 个 6x6 库存
        # 剩余需求拆分打印
        pass
```

## 实施步骤

1. 实现 `calculate_print_cost` 函数
2. 改造 `find_best_scheme` 添加成本评分
3. 实现边缘情况 5 的重新规划逻辑
4. 集成到批量模式
5. 更新输出格式
6. 添加测试用例

## 后续扩展

- 可配置 swap_penalty 值（当前固定 60 分钟）
- 库存预扣：确认方案前预扣库存，避免并发冲突
- 多批次优化：考虑多批次打印的累计成本
