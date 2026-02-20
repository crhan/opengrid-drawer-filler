# openGrid 双方案对比实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 改进 opengrid-drawer-filler skill，当有库存时自动计算并展示两种方案供用户选择。

**Architecture:** 在 Agent 交互流程中，自动调用两次 split_calc.py（有无库存各一次），解析输出并组装对比表格展示给用户。

**Tech Stack:** Python, shell, Claude Code skill system

---

## Task 1: 更新 SKILL.md 描述

**Files:**
- Modify: `SKILL.md:62-72` (Step 4 区域)
- Modify: `SKILL.md:138-155` (Step 5 对比表格区域)

**Step 1: 更新 Step 4 描述**

修改 Step 4 的描述，从：
```
### Step 4: 计算方案

根据用户选择执行：

- **不使用库存**：按原有逻辑计算最优方案
- **使用库存**：计算并展示两种方案：
  1. 不考虑库存的最优方案
  2. 考虑库存的方案（显示节省多少打印）

展示两种方案供用户选择
```

改为：
```
### Step 4: 计算方案

**自动双方案**：当检测到有库存时，自动计算两种方案：
1. 方案 A：不考虑库存（最优打印次数）
2. 方案 B：使用库存

**无库存时**：只计算方案 A（标准最优方案）

调用 `split_calc.py`：
```bash
# 方案 A：不使用库存
python3 scripts/split_calc.py -b "265x365:2 325x365:2" -i ""

# 方案 B：使用库存（默认）
python3 scripts/split_calc.py -b "265x365:2 325x365:2"
```
```

**Step 2: 更新 Step 5 对比表格描述**

修改 Step 5 的描述，确保包含覆盖率分析和对比表格的完整展示规范。

**Step 3: 验证格式**

确认 markdown 格式正确，代码块语法高亮。

---

## Task 2: 验证当前流程（可选测试）

**Step 1: 运行测试验证**

```bash
cd /Users/ruohanc/.claude/skills/opengrid-drawer-filler
.venv/bin/python -m pytest -v
```

预期：所有测试通过

---

## Task 3: 创建实现验证测试

**Files:**
- Create: `tests/test_dual_scheme_comparison.py`

**Step 1: 编写测试用例**

测试双方案对比的逻辑：
1. 测试有库存时是否计算两种方案
2. 测试无库存时是否只计算一种方案
3. 测试对比表格生成

**Step 2: 运行测试**

```bash
.venv/bin/python -m pytest tests/test_dual_scheme_comparison.py -v
```

预期：FAIL（功能未实现）

---

## Task 4: 实现双方案对比逻辑（Agent 流程层面）

**注意：** 这个任务的实现是在 Claude Code 的 skill 层面，不需要修改 Python 代码。而是更新 SKILL.md 中的 Agent 行为描述。

**Step 1: 确认 SKILL.md 已更新**

检查 SKILL.md 中 Step 4 和 Step 5 的描述是否已更新为自动双方案对比流程。

**Step 2: 手动验证流程**

在当前会话中模拟完整流程：
1. 检查配置
2. 确认库存
3. 调用两种方案的 split_calc.py
4. 展示对比表格

确认流程正确。

---

## Task 5: 更新设计文档状态

**Files:**
- Modify: `docs/plans/2026-02-20-scheme-display-optimization-design.md`

**Step 1: 更新状态**

将设计文档的 Status 从 "Draft" 改为 "Implemented"。

**Step 2: 添加实现笔记**

记录实现过程中的关键决策和变更。

---

## Task 6: 提交更改

**Step 1: 提交 SKILL.md 更新**

```bash
git add SKILL.md docs/plans/2026-02-20-scheme-display-optimization-design.md
git commit -m "docs: update SKILL.md with dual-scheme comparison workflow"
```

预期：提交成功

---

## 执行顺序

1. Task 1: 更新 SKILL.md 描述
2. Task 2: 验证当前流程（可选）
3. Task 3: 创建测试（可选）
4. Task 4: 验证实现
5. Task 5: 更新设计文档
6. Task 6: 提交更改
