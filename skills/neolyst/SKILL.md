---
name: neolyst
description: 当用户提到“neolyst"、"查询分析师"、"上传模板"、"发布模板"、"创建 coverage"、"查询 coverage"、"保存 draft"、"提交报告"、"校验报告"、"查询历史报告"，或任何需要读写 Neolyst 数据库的操作时，使用此 skill。
---

# neolyst

neolyst skill 是 Neolyst Supabase 数据访问层,实现位置：`skills/neolyst/scripts/`
前置条件：已安装 `uv`（Python 由 `uv` 自动管理）。执行接口时使用 `uv run python ...`。
所有接口必须先通过 `connection.get_client()` 获取已认证的 client。

## 接口

| # | 接口 | 模块 | 说明 |
|---|------|------|------|
| 1 | `resolve_analyst_by_email(client, email)` | `analyst` | 按邮箱查询标准化 analyst 记录 |
| 2 | `resolve_template(client, report_type, language)` | `template` | 下载模板 + schema 到本地路径 |
| 3 | `upsert_template(client, report_type, language, template_local_path, schema_local_path)` | `template` | 上传模板文件并 upsert `report_template` 记录 |
| 4 | `reuse_template(client, report_type, language, same_as_report_type)` | `template` | 静态复制另一个 report_type 的模板路径 |
| 5 | `resolve_coverage(client, ticker, first_analyst_email)` | `coverage` | 按 ticker + 分析师定位唯一 coverage |
| 6 | `create_coverage(client, ticker, english_name, sector_id, ...)` | `coverage` | 创建 coverage 及初始分析师关系 |
| 7 | `save_draft_report(client, draft_input)` | `draft_report` | 保存 draft 版本，上传文件，返回 report_id + version_no |
| 8 | `validate_draft(client, report_id, version_no)` | `validators` | 校验 draft 是否满足提交条件，收集全部错误 |
| 9 | `submit_report(client, report_id, version_no)` | `submit_report` | 将 draft 提交为 submitted，内部执行校验 |
| 10 | `list_coverage_history(client, ticker, first_analyst_email)` | `coverage` | 返回 coverage 下已发布的历史报告 |

完整签名、参数、返回值和代码示例见 `references/interfaces.md`。

## 认证

通过 `connection.get_client()` 获取 client。
若 `user.json` 不存在，向用户索取邮箱和密码后调用 `get_client(email=..., password=...)`。
认证流程、配置文件和测试连接约束详见 `references/authentication.md`。

## 业务约束

- `save_draft_report`：`report_id` 首次为 `None`，后续版本沿用同一 ID
- `create_coverage`：仅在 `resolve_coverage` 未命中且用户确认"Coverage 已完成审批"后调用
- `submit_report`：内部执行校验；调用方也可单独调用 `validate_draft` 做预检
- `reuse_template`：静态路径复制；主模板重新上传后需重新执行才能同步
- `contact_person`：必须属于 `analysts[].analyst_email`
- 分析师列表：最多 8 人；`author_order=1` 为第一作者
- `report_type` 取值：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`

## 参考文件

- **`references/interfaces.md`** — 全部 10 个接口的完整签名、参数、返回值和代码示例
- **`references/authentication.md`** — 认证流程、配置文件、凭据管理、首次使用、测试连接约束
