# 设计文档：submit_report 字段完整性校验下沉

日期：2026-04-13

## 背景

`submit_report` RPC 当前只校验状态和版本存在性，业务字段完整性校验完全在 Python 侧 `validate_draft` 中实现。其他客户端（Web、其他 skill）可绕过 Python 层直接调用 RPC，提交不完整数据。

## 目标

1. 将字段完整性校验下沉到 DB 侧，使 `submit_report` 成为数据一致性的最终守门员
2. 新增独立可调的 `validate_report` RPC，供任何客户端在提交前单独触发校验
3. Python 侧 `validate_draft` 删除，新增 `validate_report` 接口封装同名 RPC 调用

## 架构决策

- **DB 是单一事实源**：校验逻辑全部在 `validate_report` RPC 中实现，Python 层只封装调用
- **错误收集方式**：RPC 内部使用 `text[]` 数组收集所有错误，最后一次性 `RAISE EXCEPTION`，消息以"；"分隔——与原 `validate_draft` 的全量展示行为一致
- **submit_report 调用 validate_report**：`submit_report` 在状态检查后调用 `validate_report`，确保任何路径提交都经过完整校验
- **Python validate_draft 删除**：不保留兼容性包装，直接删除，接口表从 #8 validate_draft 替换为 validate_report

## DB 侧变更

### 新迁移 1：`validate_report` RPC

**签名**：`public.validate_report(p_report_id uuid) returns void`

**权限**：`grant execute to authenticated`

**校验项**（按顺序收集，全部错误一次抛出）：

| # | 校验内容 | 错误消息示例 |
|---|----------|-------------|
| 1 | 报告存在 | `报告不存在: {uuid}`（立即 RAISE，不进入数组） |
| 2 | status in (draft, rejected) | `报告状态为 submitted，仅 draft/rejected 可提交` |
| 3 | 必填字段非空：title / report_type / report_language / investment_thesis / contact_person | `缺少必填字段：标题（title）` |
| 4 | current_version_no > 0 | `报告当前没有可校验版本` |
| 5 | 当前版本行存在 | `当前版本 v{n} 不存在` |
| 6 | word_file_path / pdf_file_path 非空 | `缺少 Word 文件路径` / `缺少 PDF 文件路径` |
| 7 | report_analyst 非空 | `报告没有分析师（report_analyst 为空）` |
| 8 | contact_person 在分析师列表中（大小写不敏感） | `contact_person（{email}）不在分析师列表中` |
| 9 | 每个分析师在 analyst 表中存在且 is_active | `分析师不存在：{email}` / `分析师已停用：{email}` |
| 10 | company / company_flash：coverage_id 非空且存在 | `公司类报告（company）必须关联 coverage_id` / `coverage 不存在：{uuid}` |
| 11 | sector_id 有值时验证存在性 | `sector 不存在：{id}` |
| 12 | region_code 有值时验证存在性 | `region 不存在：{code}` |

报告不存在时立即 RAISE，其余校验项全部收集后一次抛出。

### 新迁移 2：更新 `submit_report` RPC

在现有状态校验（status in draft/rejected）之后、`UPDATE report` 之前，插入：

```sql
perform public.validate_report(p_report_id);
```

`submit_report` 保留自身的状态检查作为快速失败路径（在进入 `validate_report` 之前先拦截状态错误），`validate_report` 内部同样校验状态，保证独立调用时完整。其余逻辑（UPDATE + INSERT report_status_log + RETURN）不变。

## Python 层变更

### `skills/neolyst/scripts/validators.py`

- 删除 `_record_exists` 辅助函数
- 删除 `validate_draft` 函数
- 新增 `validate_report(client, report_id)` 函数：

```python
def validate_report(client: Client, report_id: str) -> dict:
    """
    调用 validate_report RPC，校验报告是否满足提交条件。
    校验逻辑在 DB 侧，此函数只封装调用。

    Returns: {"report_id": report_id, "version_no": int}
    Raises:  ValueError（消息含所有校验失败项，以"；"分隔）
    """
    resp = client.table("report").select("current_version_no") \
        .eq("id", report_id).execute()
    if not resp.data:
        raise ValueError(f"报告不存在: {report_id}")
    version_no = resp.data[0]["current_version_no"] or 0

    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})
    return {"report_id": report_id, "version_no": version_no}
```

### `skills/neolyst/SKILL.md`

- 接口表第 8 条：`validate_draft` → `validate_report(client, report_id)`，说明更新为"调用 DB 侧 validate_report RPC 校验当前版本是否满足提交条件"
- 业务约束第 3 条（submit_report）：更新说明，指出 RPC 内部已调用 validate，也可显式先调 `validate_report` 获取友好错误展示

### `skills/neolyst/references/interfaces.md`

- §8 `validate_draft` → 替换为 `validate_report`，更新签名、说明和示例代码
- §9 `submit_report`：补充说明"RPC 内部调用 validate_report，字段不完整时抛出 ValueError"
- 错误处理策略：`validate_draft 校验失败` 节标题改为 `validate_report 校验失败`

## 测试变更

### `test_validators.py`（改）

现有 11 个测试全部保留，仅将：
- `from skills.neolyst.scripts.validators import validate_draft` → `validate_report`
- 所有 `validate_draft(...)` 调用 → `validate_report(...)`

行为断言不变。

### `test_submit_report.py`（增）

新增 2 个测试，验证 `submit_report` 的 DB 守门员行为（绕过 `validate_report` 直接 submit）：

| 测试名 | 场景 | 断言 |
|--------|------|------|
| `test_submit_missing_investment_thesis_raises` | 存入合法 draft 后将 `investment_thesis` 置 NULL，直接调 `submit_report` | 抛出 `ValueError`，消息含"投资论点" |
| `test_submit_company_without_coverage_raises` | 存入 company draft 后将 `coverage_id` 置 NULL，直接调 `submit_report` | 抛出 `ValueError`，消息含"coverage_id" |

## 受影响文件

| 文件 | 变更类型 |
|------|----------|
| `supabase/migrations/20260413XXXXXX_validate_report_rpc.sql` | 新建 |
| `supabase/migrations/20260413XXXXXX_submit_report_with_validate.sql` | 新建 |
| `skills/neolyst/scripts/validators.py` | 修改（删 validate_draft、_record_exists，增 validate_report） |
| `skills/neolyst/SKILL.md` | 修改 |
| `skills/neolyst/references/interfaces.md` | 修改 |
| `skills/neolyst/tests/test_validators.py` | 修改（函数名替换） |
| `skills/neolyst/tests/test_submit_report.py` | 修改（新增 2 个测试） |
