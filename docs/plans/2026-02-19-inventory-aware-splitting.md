# Inventory-Aware Splitting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add inventory management to split_calc.py so the splitting algorithm prioritizes reusing existing openGrid tile stock, reducing unnecessary prints.

**Architecture:** New `inventory.py` module handles CRUD + undo for a JSON-based inventory file. `split_calc.py` imports it, passes inventory data into `find_best_scheme` to bias the scoring function toward schemes that match existing stock. After outputting the plan, an interactive prompt confirms and deducts inventory.

**Tech Stack:** Python 3.12+, pytest, JSON file storage

---

### Task 1: Create inventory.py with load/save and data model

**Files:**
- Create: `scripts/inventory.py`
- Create: `tests/test_inventory.py`

**Step 1: Write the failing tests for load/save**

```python
"""tests/test_inventory.py - inventory module tests"""
import pytest
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import inventory


@pytest.fixture
def tmp_inventory(tmp_path, monkeypatch):
    """Create a temp inventory file and patch INVENTORY_FILE"""
    inv_file = tmp_path / "inventory.json"
    monkeypatch.setattr(inventory, 'INVENTORY_FILE', str(inv_file))
    return inv_file


class TestLoadSave:
    def test_load_empty_when_no_file(self, tmp_inventory):
        result = inventory.load_inventory()
        assert result == {}

    def test_load_existing(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6, "10x5": 3},
            "log": []
        }))
        result = inventory.load_inventory()
        assert result == {"7x5": 6, "10x5": 3}

    def test_save_creates_file(self, tmp_inventory):
        inventory.save_inventory(
            {"7x5": 6},
            {"action": "add", "items": {"7x5": 6}, "reason": "test"}
        )
        data = json.loads(tmp_inventory.read_text())
        assert data["inventory"] == {"7x5": 6}
        assert len(data["log"]) == 1
        assert data["log"][0]["action"] == "add"

    def test_save_appends_log(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": [{"action": "add", "items": {"7x5": 3}, "reason": "first"}]
        }))
        inventory.save_inventory(
            {"7x5": 6},
            {"action": "add", "items": {"7x5": 3}, "reason": "second"}
        )
        data = json.loads(tmp_inventory.read_text())
        assert len(data["log"]) == 2
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inventory.py -v`
Expected: FAIL (module not found or functions missing)

**Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
openGrid 库存管理模块
管理 openGrid tile 的库存，支持入库、扣库、撤销操作。
"""

import json
import os
import sys
from datetime import datetime

INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')


def _load_data():
    """加载完整的库存数据（含日志）"""
    if not os.path.exists(INVENTORY_FILE):
        return {"inventory": {}, "log": []}
    with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_data(data):
    """保存完整的库存数据"""
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_inventory():
    """返回当前库存 dict，文件不存在时返回空 dict"""
    data = _load_data()
    return data.get("inventory", {})


def save_inventory(inv, log_entry):
    """保存库存并追加日志"""
    data = _load_data()
    data["inventory"] = inv
    log_entry["timestamp"] = datetime.now().isoformat()
    data["log"].append(log_entry)
    _save_data(data)
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inventory.py::TestLoadSave -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add scripts/inventory.py tests/test_inventory.py
git commit -m "feat: add inventory module with load/save"
```

---

### Task 2: Add inventory add/deduct operations

**Files:**
- Modify: `scripts/inventory.py`
- Modify: `tests/test_inventory.py`

**Step 1: Write the failing tests**

Add to `tests/test_inventory.py`:

```python
class TestAddInventory:
    def test_add_new_items(self, tmp_inventory):
        result = inventory.add_inventory({"7x5": 6, "10x5": 3}, reason="打印完成")
        assert result == {"7x5": 6, "10x5": 3}

    def test_add_to_existing(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": []
        }))
        result = inventory.add_inventory({"7x5": 3}, reason="追加")
        assert result == {"7x5": 6}

    def test_add_logs_operation(self, tmp_inventory):
        inventory.add_inventory({"7x5": 6}, reason="test add")
        data = json.loads(tmp_inventory.read_text())
        assert data["log"][-1]["action"] == "add"
        assert data["log"][-1]["items"] == {"7x5": 6}


class TestDeductInventory:
    def test_deduct_basic(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6, "10x5": 3},
            "log": []
        }))
        result = inventory.deduct_inventory({"7x5": 3}, reason="用于抽屉")
        assert result == {"7x5": 3, "10x5": 3}

    def test_deduct_exact(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 3},
            "log": []
        }))
        result = inventory.deduct_inventory({"7x5": 3}, reason="全部用完")
        assert result == {}  # 0 的 key 应被移除

    def test_deduct_insufficient_raises(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 2},
            "log": []
        }))
        with pytest.raises(ValueError, match="库存不足"):
            inventory.deduct_inventory({"7x5": 5}, reason="超出")

    def test_deduct_missing_key_raises(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {},
            "log": []
        }))
        with pytest.raises(ValueError, match="库存不足"):
            inventory.deduct_inventory({"7x5": 1}, reason="不存在")
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inventory.py::TestAddInventory tests/test_inventory.py::TestDeductInventory -v`
Expected: FAIL

**Step 3: Write implementation**

Add to `scripts/inventory.py`:

```python
def add_inventory(items, reason=""):
    """入库，返回更新后库存"""
    inv = load_inventory()
    for key, count in items.items():
        inv[key] = inv.get(key, 0) + count
    save_inventory(inv, {"action": "add", "items": items, "reason": reason})
    return inv


def deduct_inventory(items, reason=""):
    """扣库，返回更新后库存。库存不足时 raise ValueError"""
    inv = load_inventory()
    # 先检查所有项是否够
    for key, count in items.items():
        available = inv.get(key, 0)
        if available < count:
            raise ValueError(
                f"库存不足: {key} 需要 {count}，仅有 {available}"
            )
    # 扣除
    for key, count in items.items():
        inv[key] -= count
        if inv[key] == 0:
            del inv[key]
    save_inventory(inv, {"action": "deduct", "items": items, "reason": reason})
    return inv
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inventory.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add scripts/inventory.py tests/test_inventory.py
git commit -m "feat: add inventory add/deduct operations"
```

---

### Task 3: Add undo operation

**Files:**
- Modify: `scripts/inventory.py`
- Modify: `tests/test_inventory.py`

**Step 1: Write the failing tests**

Add to `tests/test_inventory.py`:

```python
class TestUndoLast:
    def test_undo_add(self, tmp_inventory):
        inventory.add_inventory({"7x5": 6}, reason="打印")
        result = inventory.undo_last()
        assert result == {}

    def test_undo_deduct(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6},
            "log": []
        }))
        inventory.deduct_inventory({"7x5": 3}, reason="用于抽屉")
        result = inventory.undo_last()
        assert result == {"7x5": 6}

    def test_undo_empty_log_raises(self, tmp_inventory):
        with pytest.raises(ValueError, match="没有可撤销的操作"):
            inventory.undo_last()

    def test_undo_already_undone_raises(self, tmp_inventory):
        inventory.add_inventory({"7x5": 6}, reason="打印")
        inventory.undo_last()
        with pytest.raises(ValueError, match="没有可撤销的操作"):
            inventory.undo_last()
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inventory.py::TestUndoLast -v`
Expected: FAIL

**Step 3: Write implementation**

Add to `scripts/inventory.py`:

```python
def undo_last():
    """撤销最近一次 add/deduct 操作，返回更新后库存"""
    data = _load_data()
    log = data.get("log", [])

    # 找到最近一次非 undo 操作
    last_entry = None
    for entry in reversed(log):
        if entry["action"] != "undo":
            last_entry = entry
            break

    if last_entry is None:
        raise ValueError("没有可撤销的操作")

    inv = data["inventory"]
    items = last_entry["items"]

    if last_entry["action"] == "add":
        # 撤销入库 = 扣除
        for key, count in items.items():
            inv[key] = inv.get(key, 0) - count
            if inv[key] <= 0:
                inv.pop(key, None)
    elif last_entry["action"] == "deduct":
        # 撤销扣库 = 加回
        for key, count in items.items():
            inv[key] = inv.get(key, 0) + count

    # 从日志中移除被撤销的条目
    log.remove(last_entry)

    # 记录 undo 操作
    undo_entry = {
        "action": "undo",
        "items": items,
        "reason": f"撤销 {last_entry['action']}",
        "timestamp": datetime.now().isoformat()
    }
    log.append(undo_entry)

    data["inventory"] = inv
    data["log"] = log
    _save_data(data)
    return inv
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inventory.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add scripts/inventory.py tests/test_inventory.py
git commit -m "feat: add inventory undo operation"
```

---

### Task 4: Add inventory CLI

**Files:**
- Modify: `scripts/inventory.py`

**Step 1: Write the CLI main function**

Add to `scripts/inventory.py`:

```python
def print_inventory():
    """打印当前库存"""
    inv = load_inventory()
    if not inv:
        print("库存为空")
        return
    print("当前库存:")
    for key in sorted(inv.keys()):
        w, h = key.split('x')
        count = inv[key]
        print(f"  {w}×{h}: {count} stack")
    total = sum(inv.values())
    print(f"\n共 {len(inv)} 种尺寸, {total} stack")


def parse_items(args):
    """解析 '7x5:6 10x5:3' 格式"""
    import re
    items = {}
    for arg in args:
        match = re.match(r'(\d+)x(\d+):(\d+)', arg)
        if match:
            key = f"{match.group(1)}x{match.group(2)}"
            items[key] = int(match.group(3))
        else:
            print(f"格式错误: {arg} (应为 WxH:N，如 7x5:6)")
            sys.exit(1)
    return items


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 inventory.py list              查看库存")
        print("  python3 inventory.py add 7x5:6 10x5:3  入库")
        print("  python3 inventory.py deduct 7x5:3       扣库")
        print("  python3 inventory.py undo               撤销上次操作")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        print_inventory()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("用法: python3 inventory.py add 7x5:6 10x5:3")
            sys.exit(1)
        items = parse_items(sys.argv[2:])
        result = add_inventory(items, reason="手动入库")
        print("入库完成:")
        for key, count in items.items():
            print(f"  {key}: +{count}")
        print_inventory()
    elif cmd == "deduct":
        if len(sys.argv) < 3:
            print("用法: python3 inventory.py deduct 7x5:3")
            sys.exit(1)
        items = parse_items(sys.argv[2:])
        try:
            result = deduct_inventory(items, reason="手动扣库")
            print("扣库完成:")
            for key, count in items.items():
                print(f"  {key}: -{count}")
            print_inventory()
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
    elif cmd == "undo":
        try:
            result = undo_last()
            print("已撤销上次操作")
            print_inventory()
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Manual smoke test**

Run:
```bash
python3 scripts/inventory.py list
python3 scripts/inventory.py add 7x5:6 10x5:3
python3 scripts/inventory.py list
python3 scripts/inventory.py deduct 7x5:2
python3 scripts/inventory.py undo
python3 scripts/inventory.py list
```

Expected: list shows items, add/deduct/undo work, list reflects changes.

**Step 3: Commit**

```bash
git add scripts/inventory.py
git commit -m "feat: add inventory CLI (list/add/deduct/undo)"
```

---

### Task 5: Add get_inventory_match helper

**Files:**
- Modify: `scripts/inventory.py`
- Modify: `tests/test_inventory.py`

**Step 1: Write the failing tests**

Add to `tests/test_inventory.py`:

```python
class TestGetInventoryMatch:
    def test_full_match(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 6},
            "log": []
        }))
        inv = inventory.load_inventory()
        # scheme has 3 tiles of 7x5, copies=2 -> need 6 total
        result = inventory.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5)],
            copies=2,
            inv=inv
        )
        assert result["from_inventory"] == {"7x5": 6}
        assert result["need_print"] == {}
        assert result["match_score"] == 6

    def test_partial_match(self, tmp_inventory):
        tmp_inventory.write_text(json.dumps({
            "inventory": {"7x5": 2},
            "log": []
        }))
        inv = inventory.load_inventory()
        # need 3 tiles of 7x5 (copies=1)
        result = inventory.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5)],
            copies=1,
            inv=inv
        )
        assert result["from_inventory"] == {"7x5": 2}
        assert result["need_print"] == {"7x5": 1}
        assert result["match_score"] == 2

    def test_no_match(self, tmp_inventory):
        inv = {}
        result = inventory.get_inventory_match(
            tiles=[(7, 5), (10, 5)],
            copies=1,
            inv=inv
        )
        assert result["from_inventory"] == {}
        assert result["need_print"] == {"7x5": 1, "10x5": 1}
        assert result["match_score"] == 0

    def test_mixed_sizes(self, tmp_inventory):
        inv = {"7x5": 10, "10x5": 1}
        # tiles: 3x 7x5, 3x 10x5, copies=2 -> need 6x 7x5, 6x 10x5
        result = inventory.get_inventory_match(
            tiles=[(7, 5), (7, 5), (7, 5), (10, 5), (10, 5), (10, 5)],
            copies=2,
            inv=inv
        )
        assert result["from_inventory"] == {"7x5": 6, "10x5": 1}
        assert result["need_print"] == {"10x5": 5}
        assert result["match_score"] == 7
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inventory.py::TestGetInventoryMatch -v`
Expected: FAIL

**Step 3: Write implementation**

Add to `scripts/inventory.py`:

```python
def get_inventory_match(tiles, copies, inv):
    """计算方案的库存匹配情况

    Args:
        tiles: list of (w, h) tuples from scheme
        copies: 打印份数
        inv: 当前库存 dict

    Returns:
        {
            "from_inventory": {"7x5": 3},  # 从库存取用
            "need_print": {"10x5": 3},     # 需新打印
            "match_score": 3               # 库存匹配 stack 数
        }
    """
    # 统计每种尺寸的需求
    tile_counts = {}
    for w, h in tiles:
        key = f"{w}x{h}"
        tile_counts[key] = tile_counts.get(key, 0) + 1

    from_inventory = {}
    need_print = {}
    match_score = 0

    for key, count_per_copy in tile_counts.items():
        needed = count_per_copy * copies
        available = inv.get(key, 0)
        used = min(needed, available)

        if used > 0:
            from_inventory[key] = used
        remaining = needed - used
        if remaining > 0:
            need_print[key] = remaining
        match_score += used

    return {
        "from_inventory": from_inventory,
        "need_print": need_print,
        "match_score": match_score
    }
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inventory.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add scripts/inventory.py tests/test_inventory.py
git commit -m "feat: add get_inventory_match helper"
```

---

### Task 6: Modify split_calc.py scoring to be inventory-aware

**Files:**
- Modify: `scripts/split_calc.py:123-241` (find_best_scheme and _find_best_scheme_impl)
- Modify: `tests/test_split_calc.py`

**Step 1: Write the failing tests**

Add to `tests/test_split_calc.py`:

```python
class TestInventoryAwareScheme:
    """库存感知分割测试"""

    def test_no_inventory_same_as_before(self):
        """无库存时行为不变"""
        scheme_no_inv = find_best_scheme(17, 15)
        scheme_with_empty = find_best_scheme(17, 15, inventory={})
        assert scheme_no_inv['x_splits'] == scheme_with_empty['x_splits']
        assert scheme_no_inv['y_splits'] == scheme_with_empty['y_splits']

    def test_inventory_biases_toward_stocked_sizes(self):
        """库存应影响方案选择"""
        # 20x10: 不用库存时选 10x10 * 2（1种尺寸）
        scheme_no_inv = find_best_scheme(20, 10)
        assert scheme_no_inv['x_splits'] == [10, 10]
        assert scheme_no_inv['y_splits'] == [10]

        # 有 5x10 库存时，20x10 可以分为 4个5x10，同样1种尺寸
        # 但如果只有2个5x10库存，方案 [5,5,10]x[10] 可利用2个库存
        # 而 [10,10]x[10] 利用0个
        inv = {"5x10": 2}
        scheme_inv = find_best_scheme(20, 10, inventory=inv, copies=1)
        # 有库存时应倾向于使用有库存的尺寸
        # 不过如果两个方案的 unique_sizes 差异大，unique_sizes 仍然优先
        # 这里 [10,10]x[10]=1种, [5,5,10]x[10]=2种
        # 由于库存优先级最高，应选择能利用库存的方案
        assert scheme_inv is not None
        # 验证方案中包含 5x10 的瓦片
        tile_keys = set()
        for w, h in scheme_inv['tiles']:
            tile_keys.add(f"{w}x{h}")
        assert "5x10" in tile_keys

    def test_inventory_none_fallback(self):
        """inventory=None 时退回原始行为"""
        scheme = find_best_scheme(17, 15, inventory=None)
        assert scheme is not None
        assert scheme['unique_sizes'] >= 1
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_split_calc.py::TestInventoryAwareScheme -v`
Expected: FAIL (find_best_scheme doesn't accept inventory param)

**Step 3: Modify find_best_scheme and _find_best_scheme_impl**

In `scripts/split_calc.py`, modify the function signatures and scoring:

Change `find_best_scheme` (line 123):
```python
def find_best_scheme(x, y, verbose=False, inventory=None, copies=1):
```

Inside `find_best_scheme`, pass inventory to `_find_best_scheme_impl`:
```python
    best = _find_best_scheme_impl(x, y, verbose, inventory, copies)

    if x != y:
        rotated = _find_best_scheme_impl(y, x, verbose, inventory, copies)
```

Change `_find_best_scheme_impl` (line 168):
```python
def _find_best_scheme_impl(x, y, verbose=False, inventory=None, copies=1):
```

Inside `_find_best_scheme_impl`, add inventory score calculation after line 211 (after `balance = ...`):

```python
                    # 计算库存匹配分数
                    inv_score = 0
                    if inventory:
                        for xd in xs:
                            for yd in ys:
                                key = f"{xd}x{yd}"
                                inv_score += min(
                                    tiles.count((xd, yd)) * copies,
                                    inventory.get(key, 0)
                                )
```

Change the comparison logic (lines 225-228) to include inventory score:

```python
                    # 优先级: 1)库存匹配最多 2)独特尺寸最少 3)瓦片数最少 4)均衡度最好
                    if best is None or \
                       (inv_score > best.get('inv_score', 0)) or \
                       (inv_score == best.get('inv_score', 0) and len(unique) < best['unique_sizes']) or \
                       (inv_score == best.get('inv_score', 0) and len(unique) == best['unique_sizes'] and len(tiles) < best['tile_count']) or \
                       (inv_score == best.get('inv_score', 0) and len(unique) == best['unique_sizes'] and len(tiles) == best['tile_count'] and balance < best['balance']):
                        best = scheme
                        best['inv_score'] = inv_score
```

Also add `inv_score` to the scheme dict (after line 222):
```python
                    scheme = {
                        'x_parts': x_parts,
                        'y_parts': y_parts,
                        'x_splits': xs,
                        'y_splits': ys,
                        'tiles': tiles,
                        'unique_sizes': len(unique),
                        'tile_count': len(tiles),
                        'balance': balance,
                        'inv_score': inv_score
                    }
```

Update early termination condition (line 234): only terminate early when there's no inventory to optimize for:
```python
                    if len(unique) == 1 and not inventory:
                        if verbose:
                            print(f"  [DEBUG] Checked {candidates_checked} candidates")
                        return best
```

**Step 4: Run all tests**

Run: `python3 -m pytest tests/test_split_calc.py -v`
Expected: PASS (all old tests + new inventory tests)

**Step 5: Commit**

```bash
git add scripts/split_calc.py tests/test_split_calc.py
git commit -m "feat: make find_best_scheme inventory-aware"
```

---

### Task 7: Add inventory display and confirmation to print_plan

**Files:**
- Modify: `scripts/split_calc.py:525-644` (print_plan function)
- Modify: `scripts/split_calc.py:1011-1184` (main function)

**Step 1: Add inventory import at top of split_calc.py**

After line 13 (`from concurrent.futures import ...`), add:

```python
try:
    from inventory import load_inventory, deduct_inventory, get_inventory_match
    HAS_INVENTORY = True
except ImportError:
    HAS_INVENTORY = False
```

**Step 2: Modify print_plan to show inventory info**

Add a new parameter `inventory_match=None` to `print_plan`:

```python
def print_plan(width, depth, scheme, copies=1, verbose=False, inventory_match=None):
```

After the `--- 瓦片清单 ---` section (around line 620), add:

```python
    if inventory_match and (inventory_match['from_inventory'] or inventory_match['need_print']):
        print()
        print("--- 库存利用 ---")
        for size_key in sorted(set(
            list(inventory_match['from_inventory'].keys()) +
            list(inventory_match['need_print'].keys())
        )):
            from_inv = inventory_match['from_inventory'].get(size_key, 0)
            need = inventory_match['need_print'].get(size_key, 0)
            total = from_inv + need
            if from_inv > 0 and need > 0:
                print(f"{size_key}: 需要 {total}，库存取用 {from_inv}，需新打印 {need}")
            elif from_inv > 0:
                print(f"{size_key}: 需要 {total}，全部从库存取用")
            else:
                print(f"{size_key}: 需要 {total}，全部需新打印")
```

**Step 3: Modify main() to use inventory**

In `main()`, after `scheme = find_best_scheme(...)` (line 1105), add inventory logic:

```python
    # 加载库存
    inv = {}
    inventory_match = None
    if HAS_INVENTORY and not args.no_inventory:
        inv = load_inventory()
        if inv:
            scheme = find_best_scheme(x, y, args.verbose, inventory=inv, copies=copies)
        if inv:
            inventory_match = get_inventory_match(scheme['tiles'], copies, inv)
```

Pass `inventory_match` to `print_plan`:

```python
    stats = print_plan(width, depth, scheme, copies, args.verbose, inventory_match)
```

Add confirmation prompt after `print_plan` and before STL generation:

```python
    # 交互确认扣库
    if inventory_match and inventory_match['from_inventory'] and not args.json:
        confirm = input("\n接受此方案并扣除库存？(y/n): ").strip().lower()
        if confirm == 'y':
            deduct_inventory(
                inventory_match['from_inventory'],
                reason=f"用于 {width}x{depth}mm 抽屉 x{copies}"
            )
            print("库存已更新")
        else:
            print("已取消，库存未变更")
            return
```

Add `--no-inventory` argument to parser (around line 1052):

```python
    parser.add_argument('--no-inventory', action='store_true', help='不使用库存')
```

**Step 4: Manual smoke test**

```bash
# 先添加一些库存
python3 scripts/inventory.py add 7x5:6 10x5:3

# 运行计算，应该显示库存利用信息
python3 scripts/split_calc.py 485 425 -c 1

# 运行不使用库存
python3 scripts/split_calc.py 485 425 --no-inventory
```

**Step 5: Commit**

```bash
git add scripts/split_calc.py
git commit -m "feat: integrate inventory into print_plan and main"
```

---

### Task 8: Add inventory support to batch mode

**Files:**
- Modify: `scripts/split_calc.py:913-979` (batch_mode function)
- Modify: `scripts/split_calc.py:808-910` (print_batch_plan function)

**Step 1: Modify batch_mode to pass inventory**

In `batch_mode`, after loading items, add inventory loading:

```python
def batch_mode(input_str, verbose=False, use_inventory=True):
```

After parsing items, add:

```python
    inv = {}
    if HAS_INVENTORY and use_inventory:
        inv = load_inventory()
```

Pass inventory to `calculate_single`:

```python
def calculate_single(width, depth, copies=1, verbose=False, inventory=None):
```

In `calculate_single`, pass inventory to `find_best_scheme`:

```python
    scheme = find_best_scheme(x, y, verbose, inventory=inventory, copies=copies)
```

In `batch_mode`, pass it through:

```python
    result = calculate_single(width, depth, copies, verbose, inventory=inv if inv else None)
```

**Step 2: Modify print_batch_plan to show inventory info and confirm**

After printing the merged plan, add inventory match calculation and confirmation:

```python
def print_batch_plan(batch_results, merged_tiles, inventory=None):
```

After the totals section, add:

```python
    # 显示库存利用情况
    if inventory:
        print("\n--- 库存利用 ---")
        total_from_inv = 0
        deduct_items = {}
        for (w, h), info in sorted_tiles:
            key = f"{w}x{h}"
            needed = info['total']
            available = inventory.get(key, 0)
            used = min(needed, available)
            if used > 0:
                deduct_items[key] = used
                total_from_inv += used
                remaining_print = needed - used
                print(f"  {key}: 需要 {needed}，库存取用 {used}，需新打印 {remaining_print}")
            else:
                print(f"  {key}: 需要 {needed}，全部需新打印")

        if deduct_items:
            confirm = input("\n接受方案并扣除库存？(y/n): ").strip().lower()
            if confirm == 'y':
                deduct_inventory(deduct_items, reason="批量方案")
                print("库存已更新")
```

**Step 3: Run existing tests**

Run: `python3 -m pytest tests/ -v`
Expected: PASS (all existing tests still pass)

**Step 4: Commit**

```bash
git add scripts/split_calc.py
git commit -m "feat: add inventory support to batch mode"
```

---

### Task 9: Clean up inventory.json from git tracking and add to .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add inventory.json to .gitignore**

Append to `.gitignore`:

```
scripts/inventory.json
```

This ensures user's inventory data isn't committed to the repo.

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add inventory.json to gitignore"
```

---

### Task 10: Final integration test and cleanup

**Files:**
- All modified files

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 2: Manual end-to-end test**

```bash
# Clean slate
rm -f scripts/inventory.json

# Add inventory
python3 scripts/inventory.py add 7x5:6 10x5:3
python3 scripts/inventory.py list

# Run single mode with inventory
python3 scripts/split_calc.py 485 425 -c 1

# Run batch mode
python3 scripts/split_calc.py -b "400x400:1 485x425:1"

# Run without inventory
python3 scripts/split_calc.py 485 425 --no-inventory

# Undo last deduction
python3 scripts/inventory.py undo
python3 scripts/inventory.py list
```

**Step 3: Verify no regressions**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "test: verify full inventory integration"
```
