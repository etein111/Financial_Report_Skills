# Neolyst Iter 8: 当前版本校验与提交契约收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `validate_draft` 与 `submit_report` 收口为仅按 `report_id` 操作当前版本，去掉 `version_no` 入参，并同步 Python、Supabase、测试与活跃文档。

**Architecture:**
- `validate_draft` 保留在 Python 侧，用 `report.current_version_no` 决定当前版本，完成只读提交前校验并返回真实 `version_no`。
- `submit_report` 的 Python 包装层不再做客户端预校验，只调用新的 `submit_report(p_report_id)` RPC；RPC 在数据库侧读取当前版本、做最低一致性保护并写入 `report_status_log.version_no`。
- 仓内直接硬切换为新契约，不保留 `version_no` 兼容层；历史过程文档留在 `docs/superpowers/`，活跃文档正文直接回写为当前实现。

**Tech Stack:** Python 3.14, supabase-py, PostgreSQL PL/pgSQL, pytest, Markdown

**已确认的设计决策：**
- `validate_draft` 只校验 `report.current_version_no` 指向的当前版本
- `submit_report` 也去掉 `version_no`，只接收 `report_id`
- `submit_report` 不再在 Python 侧预调用 `validate_draft`
- 活跃文档直接硬切换；历史 spec / plan 文档保留

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/neolyst/scripts/validators.py` | 修改 | `validate_draft(client, report_id)` 读取当前版本并返回真实 `version_no` |
| `skills/neolyst/scripts/submit_report.py` | 修改 | `submit_report(client, report_id)` 只调用 RPC |
| `supabase/migrations/20260411000100_100_submit_report_current_version.sql` | 新增 | 用 `submit_report(uuid)` 替换旧的 `submit_report(uuid, integer)` |
| `skills/neolyst/tests/test_validators.py` | 修改 | 删除旧签名调用并补充当前版本异常场景 |
| `skills/neolyst/tests/test_submit_report.py` | 修改 | 删除旧签名调用并校验当前版本日志写入 |
| `skills/neolyst/SKILL.md` | 修改 | 将公开接口收口为 `report_id` 单参数 |
| `skills/neolyst/references/interfaces.md` | 修改 | 更新示例、返回值与调用约束 |
| `docs/skills_neolyst_design.md` | 修改 | 让正文与实际实现一致 |
| `docs/skills_neolyst_integration.md` | 修改 | 同步上游接入说明 |

## 背景与约束

- `report.current_version_no` 已经是当前 draft 版本的唯一事实源，调用方不应再参与版本选择。
- `validate_draft` 保留在 Python 侧，只做 SELECT 查询；`submit_report` 的状态流转继续放在 Supabase RPC。
- 本轮为破坏性接口调整，不保留 `version_no` 兼容层。
- 迭代记录以后直接以 `plans/` 目录下的 iter 文件为准，不再维护独立 roadmap。

## Task 1: 收口 `validate_draft` 到当前版本

**Files:**
- Modify: `skills/neolyst/scripts/validators.py`
- Test: `skills/neolyst/tests/test_validators.py`

- [x] **Step 1: 修改 `validate_draft` 公开签名**

将公开接口从 `validate_draft(client, report_id, version_no)` 改为 `validate_draft(client, report_id)`，由函数内部读取 `report.current_version_no`。

- [x] **Step 2: 收口当前版本错误语义**

明确覆盖以下最小保护：
- `report` 不存在
- `status` 不是 `draft` / `rejected`
- `current_version_no <= 0`
- `current_version_no` 指向的 `report_version` 不存在

- [x] **Step 3: 同步校验测试**

删除测试中的 `version_no` 调用，补充以下场景：
- `current_version_no = 0`
- 当前版本行缺失
- 返回值中的 `version_no` 为真实当前版本

## Task 2: 收口 `submit_report` 到当前版本

**Files:**
- Create: `supabase/migrations/20260411000100_100_submit_report_current_version.sql`
- Modify: `skills/neolyst/scripts/submit_report.py`
- Test: `skills/neolyst/tests/test_submit_report.py`

- [x] **Step 1: 在 Supabase 侧改签名**

删除旧的 `public.submit_report(uuid, integer)`，新建 `public.submit_report(p_report_id uuid)`，由 RPC 自行读取 `report.current_version_no`。

- [x] **Step 2: 增加提交 RPC 的最低一致性保护**

RPC 内最小保护包括：
- 报告存在
- 状态为 `draft` / `rejected`
- `current_version_no > 0`
- 当前版本行存在

RPC 成功后更新 `report.status = 'submitted'`，并把真实版本号写入 `report_status_log.version_no`。

- [x] **Step 3: 收口 Python 包装层与测试**

`submit_report.py` 只负责调用 RPC 并返回 `{report_id, version_no, status}`。测试同步删除 `version_no` 入参，并新增：
- `current_version_no = 0` 报错
- 当前版本行缺失报错
- `report_status_log.version_no` 写入真实当前版本

## Task 3: 硬切换公开接口与活跃文档

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `skills/neolyst/references/interfaces.md`
- Modify: `docs/skills_neolyst_design.md`
- Modify: `docs/skills_neolyst_integration.md`

- [x] **Step 1: 更新公开接口说明**

将 `SKILL.md` 与 `references/interfaces.md` 中的 `validate_draft` / `submit_report` 全部改为只接收 `report_id`。

- [x] **Step 2: 更新活跃文档正文**

将 `docs/skills_neolyst_design.md` 与 `docs/skills_neolyst_integration.md` 的正文直接回写为当前实现，不再依赖追加勘误说明。

- [x] **Step 3: 保留历史过程文档**

`docs/superpowers/specs/2026-04-11-neolyst-validate-draft-current-version-design.md` 与 `docs/superpowers/plans/2026-04-11-neolyst-current-version-submit.md` 保留为过程记录，不回填。

## Task 4: 验证与交付

**Files:**
- Modify: `plans/2026-04-11-neolyst-iter8.md`

- [x] **Step 1: 重置本地 Supabase 并导入测试数据**

Run:
```bash
supabase db reset
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f supabase/tests/test_data.sql
```

- [x] **Step 2: 运行针对性测试**

Run:
```bash
uv run pytest skills/neolyst/tests/test_validators.py skills/neolyst/tests/test_submit_report.py -q
```

Expected:
- `17 passed`

- [x] **Step 3: 运行 `neolyst` 全量测试**

Run:
```bash
uv run pytest skills/neolyst/tests -q
```

Expected:
- `61 passed`

- [x] **Step 4: 交付到主分支**

本轮代码修改已完成并合入主分支；Git 操作由用户手工完成。

## 完成标准

- [x] `validate_draft` 已改为只接收 `report_id`，并返回真实当前版本号
- [x] `submit_report` 已改为只接收 `report_id`，Python 侧不再传 `version_no`
- [x] Supabase 侧已存在新的 `submit_report(uuid)` migration，最低一致性保护已生效
- [x] 仓内公开接口、测试和活跃文档已切换为当前版本契约
- [x] 本地验证记录已覆盖 `validate_draft` / `submit_report` 相关测试
