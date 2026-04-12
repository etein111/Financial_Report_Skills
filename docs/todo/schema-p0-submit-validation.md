# P0 Schema 调整：submit_report RPC 补充字段完整性校验

> 调整日期：2026-04-12
> 优先级说明：当前 submit_report RPC 仅校验状态和版本存在性，不校验业务字段完整性（coverage_id、必填字段、分析师列表等）。字段校验完全依赖 Python 侧 validate_draft，其他客户端（Web、其他 skill）绕过 validate_draft 直接调 RPC 时可提交不完整数据。

---

## 现状

`submit_report` RPC（`100_submit_report_current_version.sql`）当前只校验：

1. 报告存在
2. 状态为 draft / rejected
3. `current_version_no > 0`
4. 当前版本行存在

以下校验完全在 Python 侧 `validators.py` 的 `validate_draft` 中实现，RPC 不做：

- 必填字段：title / report_type / report_language / investment_thesis / contact_person
- 文件路径：word_file_path / pdf_file_path 非空
- 分析师列表非空，contact_person 在列表中
- 每个分析师存在且 is_active
- 公司类报告（company / company_flash）必须有 coverage_id 且存在
- sector_id / region_code 有值时验证存在性

## 目标

将以上业务字段校验下沉到 `submit_report` RPC，使其成为数据一致性的最终守门员。Python 侧 `validate_draft` 保留，用于提前收集全部错误并友好展示。

## 设计约束

- RPC 内校验失败时应明确抛出具体错误信息（如中文提示），而非笼统的 constraint violation
- Python 侧 `validate_draft` 的校验范围应与 RPC 保持同步，但不要求实现方式完全相同（Python 侧可以一次收集所有错误，RPC 可以逐项 RAISE）
- 校验逻辑变更需要配套测试覆盖

## 完整受影响清单

### 修改

- `submit_report` RPC：新增字段完整性校验（coverage_id、必填字段、分析师、文件路径）
- `validators.py`：校验范围与 RPC 保持对齐，定位从"唯一守门员"变为"前置友好提示"

### 测试

- RPC 侧：新增 submit_report 的字段校验测试用例
- Python 侧：现有 validate_draft 测试保持通过，确保行为一致
