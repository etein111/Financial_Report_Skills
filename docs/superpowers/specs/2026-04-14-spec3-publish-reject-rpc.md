# Spec 3: 补 publish_report + reject_report RPC

## 变更

补全报告状态机中 submitted → published 和 submitted → rejected 两条路径。

## RLS 修改

`report_update` policy 追加 SA 条件：

```sql
-- USING 追加：
OR (current_app_role() = 'sa' AND status = 'submitted')
-- WITH CHECK 追加：
OR (current_app_role() = 'sa' AND status IN ('published', 'rejected'))
```

## SQL 函数

### publish_report(p_report_id uuid) → TABLE(report_id uuid, status text)

- 校验报告存在且 status = submitted
- UPDATE：status = published, published_by = auth.uid(), published_at = now()
- 不用 SECURITY DEFINER，依赖 RLS
- 中文注释

### reject_report(p_report_id uuid, p_rejection_reason text) → TABLE(report_id uuid, status text)

- 校验 p_rejection_reason 非空非空白
- 校验报告存在且 status = submitted
- UPDATE：status = rejected, rejection_reason = p_rejection_reason
- 不用 SECURITY DEFINER，依赖 RLS
- 中文注释

## Python 侧（scripts/report.py）

```python
def publish_report(client: Client, report_id: str) -> dict:
    """发布报告，返回 {"report_id": str, "status": "published"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "publish_report", {
        "p_report_id": report_id,
    }))
    return {"report_id": str(row["report_id"]), "status": row["status"]}

def reject_report(client: Client, report_id: str, reason: str) -> dict:
    """退回报告，返回 {"report_id": str, "status": "rejected"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "reject_report", {
        "p_report_id": report_id,
        "p_rejection_reason": reason,
    }))
    return {"report_id": str(row["report_id"]), "status": row["status"]}
```

## 文档更新

- `SKILL.md` 接口表格追加 publish_report 和 reject_report
- `references/interfaces.md` 追加两个接口的完整签名和示例

## 测试

- 新建 `tests/test_publish_report.py`，模式参考 `test_retract_report.py`
- 新建 `tests/test_reject_report.py`
- 测试用户需 admin 或 SA 角色

## 依赖

- 需先运行迁移，RPC 函数存在后 Python 才能调用
- 使用 `supabase migration new` 创建迁移文件
