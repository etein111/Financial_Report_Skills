# Neolyst Iter 7: 契约与文档对齐实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收口 `neolyst` 现有实现与对外契约之间的差异，统一校验接口命名、连接说明和测试说明，并彻底清理一遍 `SKILL.md`，为上游 skill 接入提供稳定文档基线。

**Architecture:**
- `validate_draft` 继续保留 Python 侧 SELECT 校验实现，不改为 RPC；本轮只统一“公开接口名”和“设计文档表述”。
- 连接配置保持当前实现：`neolyst.yaml` 作为运行时默认配置，测试强制使用环境变量覆盖；认证信息拆分为 `user.json` + `session.json`。
- 本轮不新增业务能力，不改 Supabase schema，不动 `report_maker` / `template_maker`。
- `SKILL.md` 本轮按“全面清理”处理，不只修单点命名；凡是与当前实现不一致、已过期或会误导上游接入的内容都要一起收掉。

**Tech Stack:** Markdown, Python 3.14, pytest, supabase-py

**已确认的设计决策：**
- `validators.py` 模块名保留不变，公开接口名统一为 `validate_draft`
- `validate_draft` 当前实现继续放在 Python 侧，不下沉为 RPC
- `neolyst.yaml` 允许指向 staging；本地测试不得再依赖该文件中的本地配置
- roadmap 本轮只新增正式计划链接，不回填实施结果

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/neolyst/SKILL.md` | 修改 | 统一公开接口名、连接说明、测试说明，并全面清理过期文案 |
| `docs/skills_neolyst_design.md` | 修改 | 回写当前实现边界与连接模型 |
| `skills/neolyst/tests/README.md` | 修改 | 明确本地测试环境变量约束 |
| `plans/2026-04-07-neolyst-skill-roadmap.md` | 修改 | 挂上 Iter 7 / Iter 8 计划链接 |

## 背景与约束

- 当前实现中公开可调用的校验函数是 [`validate_draft`](/mnt/c/_code/neoskills/skills/neolyst/scripts/validators.py)，但设计文档和部分说明仍写 `validators`
- 当前认证实现已经拆成 `user.json` 与 `session.json` 两个文件，测试也已改为显式注入 `NEOLYST_URL` / `NEOLYST_ANON_KEY`
- `skills/neolyst/neolyst.yaml` 已改为 staging 配置，不能再把它描述为“本地默认配置”
- 按仓库规范，修改 `SKILL.md` 时必须使用 `skill-creator`

## Task 1: 彻底清理 `SKILL.md`，统一对外接口与连接说明

**Files:**
- Modify: `skills/neolyst/SKILL.md`

- [ ] **Step 1: 用 `skill-creator` 全面扫描并清理 `SKILL.md` 的过期内容**

要求：
- 不只改 `validate_draft` 相关命名
- 一并清理所有与当前实现不一致的接口说明、文件说明、测试说明、调用约束
- 重点检查：`validators`、`user.json` 单文件描述、`neolyst.yaml` 本地默认描述、测试连接方式、提交前约束表述

- [ ] **Step 2: 用 `skill-creator` 更新 `SKILL.md` 中的校验接口命名**

要求：
- 将“### 8. validate_draft ✅ 已实现”作为唯一公开名称保留
- 删除“见 validators”一类旧表述，统一改为“见 `validate_draft`”
- 保留 `validators.py` 模块路径示例，但不再把 `validators` 当成对外函数名

- [ ] **Step 3: 用 `skill-creator` 更新认证与测试说明**

要求：
- 将认证文件说明改为 `user.json` + `session.json`
- 说明 `neolyst.yaml` 是运行时默认配置，可指向 staging
- 说明本地测试必须通过 `NEOLYST_URL` / `NEOLYST_ANON_KEY` 覆盖，不依赖 yaml 默认值

- [ ] **Step 4: 运行 grep 验证 `SKILL.md` 清理结果**

Run:
```bash
rg -n "validators|validate_draft|session.json|user.json|NEOLYST_URL|NEOLYST_ANON_KEY|127.0.0.1:54321|本地 Supabase" skills/neolyst/SKILL.md
```

Expected:
- `validate_draft` 为主命名
- `session.json` / 环境变量说明存在
- 不再出现“`submit_report` 之前必须先通过 `validators`”这类旧表述
- 不再出现把 yaml 默认配置写成本地环境的旧文案

## Task 2: 回写设计文档，确认当前实现边界

**Files:**
- Modify: `docs/skills_neolyst_design.md`

- [ ] **Step 1: 更新接口命名与校验落点描述**

要求：
- 将“`validators`”统一改为“`validate_draft`”
- 在“业务逻辑落点”或“执行流程”中明确：当前 `validate_draft` 由 Python 侧实现，不是 Supabase RPC
- 保持 `submit_report` 仍通过 RPC 完成状态流转

- [ ] **Step 2: 更新连接与测试配置描述**

要求：
- 将认证文件说明改为 `user.json` + `session.json`
- 删除“`neolyst.yaml` 默认本地 Supabase”之类表述
- 将“测试通过环境变量覆盖”改成强约束，而不是可选备注

- [ ] **Step 3: 校验设计文档不再误导上游接入**

Run:
```bash
rg -n "validators|validate_draft|user.json|session.json|本地 Supabase URL|neolyst.yaml" docs/skills_neolyst_design.md
```

Expected:
- `validate_draft` 为唯一对外校验接口名
- 文档中不再把 `neolyst.yaml` 写成本地默认环境

## Task 3: 收口测试说明与 roadmap

**Files:**
- Modify: `skills/neolyst/tests/README.md`
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 更新测试 README**

要求：
- 写明本地测试使用 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` / `NEOLYST_TEST_EMAIL` / `NEOLYST_TEST_PASSWORD`
- 明确 pytest 运行过程中会映射到 `NEOLYST_URL` / `NEOLYST_ANON_KEY`

- [ ] **Step 2: 更新 roadmap 中 Iter 7 / Iter 8 的范围与计划文件链接**

要求：
- Iter 7 范围写为“契约与文档对齐”
- Iter 8 范围写为“report_maker + template_maker 接入”
- 两行都补上计划文件链接

- [ ] **Step 3: 跑 `neolyst` 测试确认文档收尾未影响现状**

Run:
```bash
uv run pytest skills/neolyst/tests -q
```

Expected:
- 全量通过

- [ ] **Step 4: 更新本计划状态**

要求：
- 将本文件中的完成项打勾
- 在 roadmap 中将 Iter 7 状态改为“已完成”

## 完成标准

- [ ] `SKILL.md` 已完成一轮彻底清理，不再保留已知过期文案
- [ ] `SKILL.md`、设计文档、测试 README 对 `validate_draft` / 连接配置 / 测试配置的表述完全一致
- [ ] roadmap 已挂出 Iter 7 / Iter 8 正式计划文件
- [ ] `uv run pytest skills/neolyst/tests -q` 通过
