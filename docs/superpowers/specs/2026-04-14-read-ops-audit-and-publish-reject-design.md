# 读操作架构边界审计 & 补 publish/reject RPC

日期：2026-04-14

## 背景

审计 neolyst 所有 Supabase 读操作，发现架构边界不一致：Python 侧 `resolve_template` 直接查表却含校验逻辑，SQL 侧 `resolve_analyst_by_email` 走 RPC 却只做了简单过滤。同时报告状态机缺少 SA 审批所需的 publish 和 reject 两个写操作。

## 变更范围

### 1. resolve_analyst_by_email：RPC → 直接查表

**问题**：该 RPC 只做了 lower/trim + 按 PK 查 + is_active 检查，不属于需要集中在服务端的业务逻辑。

**方案**：
- Python 侧 `analyst.py` 改为 `client.table("analyst").select("*").eq("email", email_lower).execute()`
- Python 侧自行做 lower/trim 和 is_active 校验
- SQL 侧新迁移中 DROP 函数 `resolve_analyst_by_email` 及其 GRANT

**涉及文件**：
- `skills/neolyst/scripts/analyst.py` — 重写函数体
- `skills/neolyst/tests/test_analyst.py` — 适配新行为（错误信息可能变化）
- `skills/neolyst/SKILL.md` — 更新接口描述
- `skills/neolyst/references/interfaces.md` — 更新接口文档
- `supabase/migrations/` — 新迁移，DROP 函数

### 2. resolve_template：按 id 查 → 按 report_type + language 查

**问题**：当前拼 `{report_type}_{language}` 作为 id 查询，Python 侧依赖了 id 拼接规则。

**方案**：
- Python 侧 `template.py` 改为 `.eq("report_type", report_type).eq("language", language)`
- 不再拼组合 id，id 规则成为服务端实现细节

**涉及文件**：
- `skills/neolyst/scripts/template.py` — 修改查询条件（L90-96）

### 3. 补 publish_report + reject_report RPC

**问题**：报告状态机 submitted → published / submitted → rejected 两条路径无 RPC 实现。

**RLS 修改**：
- `report_update` policy 的 USING 追加：`OR (current_app_role() = 'sa' AND status = 'submitted')`
- `report_update` policy 的 WITH CHECK 追加：`OR (current_app_role() = 'sa' AND status IN ('published', 'rejected'))`
- SA 只能 UPDATE 状态为 submitted 的报告，且新状态只能是 published 或 rejected

**SQL 函数 publish_report(p_report_id uuid)**：
- 校验报告存在且 status = submitted
- UPDATE status = published, published_by = auth.uid(), published_at = now()
- 返回 TABLE(report_id uuid, status text)
- 不用 SECURITY DEFINER，依赖 RLS 控制权限
- 中文注释

**SQL 函数 reject_report(p_report_id uuid, p_rejection_reason text)**：
- 校验 p_rejection_reason 非空非空白
- 校验报告存在且 status = submitted
- UPDATE status = rejected, rejection_reason = p_rejection_reason
- 返回 TABLE(report_id uuid, status text)
- 不用 SECURITY DEFINER，依赖 RLS 控制权限
- 中文注释

**Python 侧**（`scripts/report.py`）：
- `publish_report(client, report_id) → dict` — 模式与 submit_report 一致
- `reject_report(client, report_id, reason) → dict` — 多一个 reason 参数

**涉及文件**：
- `supabase/migrations/` — 新迁移：DROP 旧 policy、CREATE 新 policy、CREATE 两个函数、GRANT
- `skills/neolyst/scripts/report.py` — 新增两个函数
- `skills/neolyst/SKILL.md` — 更新接口列表
- `skills/neolyst/references/interfaces.md` — 补充接口文档

## 不在范围内

- analyst / coverage 的 CRUD RPC（admin 操作，后续迭代）
- 测试用例编写（TDD 阶段处理）
- ARCHITECTURE.md 读操作标准更新（独立任务）
- 迁移文件必须用 `supabase migration new` 生成

## 设计原则

- 权限控制与现有 submit/retract 一致：不用 SECURITY DEFINER，依赖 RLS
- 错误信息用中文，与其他 RPC 保持一致
- Python 函数签名和返回格式与现有 report.py 中的函数统一
