# openGrid 库存感知分割方案设计

## 目标

为 split_calc.py 添加库存管理功能，使分割算法优先利用已有 openGrid tile 库存，减少不必要的打印。

## 文件结构

```
scripts/
├── split_calc.py        # 核心分割算法（改造评分 + 计划确认后扣库）
├── inventory.py          # 独立库存管理脚本 + 模块 API
└── inventory.json        # 库存数据文件（自动创建）
```

## 数据模型

`scripts/inventory.json`:

```json
{
  "inventory": {
    "7x5": 6,
    "10x5": 3
  },
  "log": [
    {
      "action": "add",
      "items": {"7x5": 6},
      "reason": "打印完成",
      "timestamp": "2026-02-19T10:30:00"
    }
  ]
}
```

- `inventory`: key = `WxH`（格子数），value = stack 数量
- `log`: 操作日志，每条含 action（add/deduct/undo）、items、reason、timestamp

## inventory.py — 库存管理脚本

### CLI 接口

```bash
python3 scripts/inventory.py list                   # 查看库存
python3 scripts/inventory.py add 7x5:6 10x5:3       # 入库
python3 scripts/inventory.py deduct 7x5:3            # 手动扣库
python3 scripts/inventory.py undo                    # 撤销上次操作
```

### 模块 API

```python
INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')

def load_inventory() -> dict[str, int]
    # 返回当前库存 dict，文件不存在时返回空 dict

def save_inventory(inventory: dict[str, int], log_entry: dict) -> None
    # 保存库存并追加日志

def add_inventory(items: dict[str, int], reason: str = "") -> dict[str, int]
    # 入库，返回更新后库存

def deduct_inventory(items: dict[str, int], reason: str = "") -> dict[str, int]
    # 扣库，返回更新后库存。库存不足时 raise ValueError

def undo_last() -> dict[str, int]
    # 撤销最近一次 add/deduct 操作，返回更新后库存

def get_inventory_match(scheme_tiles: list[tuple[int,int]], copies: int, inventory: dict[str, int]) -> dict
    # 计算方案的库存匹配情况
    # 返回: {"from_inventory": {"7x5": 3}, "need_print": {"10x5": 3}, "match_score": 3}
```

## split_calc.py 改动

### 算法改造

`find_best_scheme` 和 `_find_best_scheme_impl` 新增可选参数：

```python
def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
def _find_best_scheme_impl(x, y, verbose=False, inventory=None, copies=1):
```

评分优先级（从高到低）：
1. **库存可满足的 stack 数最多**（新增）
2. 独特尺寸最少
3. 瓦片数最少
4. 均衡度最好

计算库存匹配分数：
```python
def calc_inventory_score(tiles, inventory, copies):
    """tiles 中有多少 stack 可从库存满足"""
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    matched = 0
    for key, count in tile_counts.items():
        needed = count * copies
        available = inventory.get(key, 0)
        matched += min(needed, available)
    return matched
```

当 `inventory` 为 None 时，`inventory_score` 始终为 0，退回到原始评分。

### 输出改造

`print_plan` 新增库存信息展示：

```
--- 库存利用 ---
7×5: 库存 6，需要 3 → 从库存取用 3
10×5: 库存 0，需要 3 → 需新打印 3

--- 打印计划（仅需新打印部分）---
10×5: 3 stack (22mm)
       耗材: 170.9g, 时间: 1h7m
```

### 交互确认

计划输出后新增确认流程：

```python
confirm = input("\n接受此方案并扣除库存？(y/n): ").strip().lower()
if confirm == 'y':
    deduct_inventory(from_inventory_items, reason=f"用于 {width}x{depth} 抽屉")
    print("库存已更新")
```

### 新增 CLI 参数

```python
parser.add_argument('--no-inventory', action='store_true', help='不使用库存')
```

### 批量模式

`batch_mode` 中合并后的瓦片清单同样检查库存，只为差额生成打印计划。

## 测试

- `test_inventory.py`: 测试库存 CRUD、撤销、库存匹配计算
- `test_split_calc.py` 扩展: 测试库存感知评分、无库存时退回原始行为
