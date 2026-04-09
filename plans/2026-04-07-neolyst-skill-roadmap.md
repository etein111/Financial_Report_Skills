# neolyst Skill 开发路线图

## 目标

实现 `skills/neolyst/` skill，封装所有对 Neolyst Supabase 的业务操作，对外暴露 9 个稳定的业务接口。

## 原则

1. **迭代式推进**：每轮迭代做完验证后再规划下一轮，避免基于假设的大计划
2. **设计文档持续更新**：每轮迭代结束后，将学到的真实信息更新到 `docs/skills_neolyst_design.md`
3. **Schema 真相源**：`supabase/migrations/` 为数据库结构唯一真相，代码紧跟 migration
4. **业务逻辑下沉**：写操作优先走 Supabase 侧存储过程（RPC），skill 层负责认证、参数整理和调用

## 设计文档状态

`docs/skills_neolyst_design.md` 已与实际 schema 对齐（7 项差异已修正）。

**`certificate_confirmed`**：report 表无此列，纯 skill 层校验（validators 检查 draft 输入中该字段为 true，不写入数据库）。

## 迭代

### Iter 1：connection + analyst

**范围：** 验证登录认证，确认 analyst 表可读

**模块：**
- `connection.py` — 认证与 session 管理（已有代码，需验证和可能修复）
- `analyst.py` — `resolve_analyst_by_email(client, email) → analyst_email`

**入口条件：**
- 本地 Supabase 环境可用（`supabase start` 成功）
- 获得本地 URL 和 anon key

**出口条件：**
- `test_connection.py` 3/3 通过（登录、session 复用、无凭据报错）
- `test_analyst.py` 2/2 通过（按 email 查到、查不到报错）

**本迭代交付物：**
- 确认 anon key 获取方式
- 确认 analyst 表实际查询行为
- 连接可复用于后续所有迭代

---

### Iter 2：storage + template

**范围：** 文件上传下载 + 模板的查询、发布、复用

**模块：**
- `storage.py` — 文件上传/下载、路径生成
- `template.py` — `resolve_template`, `upsert_template`, `reuse_template`

**Supabase 侧 RPC（本迭代创建）：**
- `upsert_report_template(report_type, language, template_file_path, schema_file_path)`
- `reuse_report_template(target_report_type, language, source_report_type)`

**入口条件：** Iter 1 通过

**出口条件：**
- `test_storage.py` 通过（路径生成、上传下载、报告文件上传）
- `test_template.py` 通过（upsert 创建记录、resolve 下载、reuse 复制、自复用报错、源不存在报错）
- 模板 upsert 通过 RPC 实现

**本迭代交付物：**
- 确认 Storage bucket 名称和权限
- 模板 RPC 函数上线

---

### Iter 3：coverage

**范围：** coverage 的解析与创建

**模块：**
- `coverage.py` — `resolve_coverage`, `create_coverage`

**Supabase 侧 RPC（本迭代创建）：**
- `resolve_coverage(ticker, analyst_email)`
- `create_coverage(ticker, english_name, ..., analysts jsonb)`

**入口条件：** Iter 1 通过

**出口条件：**
- `test_coverage.py` 通过（create+resolve、未命中报错、analyst 不匹配报错）
- coverage RPC 函数上线

**本迭代交付物：**
- 确认 coverage.ticker 大小写处理
- 确认 coverage_analyst 写入行为

---

### Iter 4：draft_report

**范围：** draft 版本保存

**模块：**
- `draft_report.py` — `save_draft_report`

**Supabase 侧 RPC（本迭代创建）：**
- `save_draft_report(draft jsonb, user_id uuid)`

**入口条件：** Iter 2 + Iter 3 通过

**出口条件：**
- `test_draft_report.py` 通过（首次保存返回 version_no=1、追加保存 version_no 递增）
- draft RPC 函数上线

**本迭代交付物：**
- 确认 report 写入字段映射
- 确认 report_analyst delete+insert 刷新模式与 RLS 兼容

---

### Iter 5：validators + submit

**范围：** 提交前校验 + 提交

**模块：**
- `validators.py` — `validators(report_id, version_no)`
- `submit_report.py` — `submit_report(report_id, version_no)`

**Supabase 侧 RPC（本迭代创建）：**
- `validate_report_for_submission(report_id, version_no)`
- `submit_report(report_id, version_no, user_id uuid)`

**入口条件：** Iter 4 通过

**出口条件：**
- `test_validators.py` 通过（完整 draft 通过校验、缺少必填字段失败）
- `test_submit_report.py` 通过（提交后 status 变为 submitted、无效 report 报错）
- 端到端流程：resolve_analyst → resolve_coverage → save_draft → validators → submit_report

**本迭代交付物：**
- 校验和提交 RPC 函数上线
- 确认 RLS 对 analyst 角色的实际影响

---

### 收尾

**范围：** 全量测试、文档同步、旧 plan 归档

- 全量测试 `uv run pytest skills/neolyst/tests/ -v` 全部通过
- 所有模块 import 正常
- 更新 `skills/neolyst/SKILL.md` 接口签名与实际实现对齐
- 更新 `docs/skills_neolyst_design.md` 对齐清单中所有 7 项差异
- 清理 memory 和旧 TaskList

## 模块依赖关系

```
connection.py (无依赖)
    ↑
    ├── storage.py (只依赖 connection)
    ├── analyst.py (只依赖 connection)
    ├── coverage.py (只依赖 connection)
    │
    ├── template.py (依赖 connection + storage)
    ├── draft_report.py (依赖 connection + storage)
    ├── validators.py (依赖 connection + analyst + coverage)
    └── submit_report.py (依赖 connection + validators)
```

## 已有资产

| 资产 | 状态 | 位置 |
|------|------|------|
| 设计文档 | 需更新 7 处差异 | `docs/skills_neolyst_design.md` |
| 数据库 schema | 已落地 | `supabase/migrations/` (5 个文件) |
| SKILL.md | 已创建，接口签名需更新 | `skills/neolyst/SKILL.md` |
| connection.py | 已实现，需验证 | `skills/neolyst/scripts/connection.py` |
| test_connection.py | 已创建，需验证 | `skills/neolyst/tests/test_connection.py` |
| 旧 plan | 归档保留 | `plans/2026-04-07-neolyst-skill.md` |

## 风险与待确认项

1. **本地 Supabase 环境**：Iter 1 的前置条件，需先完成 `supabase start`
2. **Storage bucket**：Iter 2 时确认 bucket 名称和权限配置
3. **RLS 影响**：Iter 4 时验证 analyst 角色对 report 表的写权限范围
4. **测试数据清理**：每轮迭代产生的测试数据需要清理策略（ticker 前缀标记）
