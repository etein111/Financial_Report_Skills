---
name: neolyst
description: 当用户提到”neolyst”、”研报”、”查询分析师”、”上传模板”、”发布模板”、”创建 coverage”、”查询 coverage”、”查询报告”、”我的报告”、”查看报告”、”报告审计”、”报告状态日志”、”下载报告”、”下载模板”、”停用报告”、”编辑报告”、”修改报告”、”保存 draft”、”提交报告”、”校验报告”、”查询历史报告”、”发布报告”、”退回报告”、”reject”、”行业”、”sector”、”区域”、”region”，或任何需要读写 Neolyst 数据库的操作时，使用此 skill。
---

# neolyst

Neolyst 数据库的唯一访问入口。用户和其他 skill 通过它完成所有 Neolyst 数据库操作——查询、写入、文件上传、状态流转。

两类调用场景共享同一套接口：
- **用户直接调用**：用户在对话中提到分析师、模板、coverage、报告等操作时，Claude 直接调用对应接口
- **skill 程序化调用**：report_maker 等上游 skill 在生成报告后，通过本 skill 的接口完成提交、上传和发布

实现位置：`skills/neolyst/scripts/`。执行接口时用 `uv run python ...`。
所有接口依赖 `connection.get_client()` 返回的已认证 client。

## 接口

完整签名、参数、返回值和代码示例见 `references/interfaces.md`。接口调用失败时，参考「错误处理策略」决定响应方式——不要把 ValueError 原文直接展示给用户。

### 报告生命周期

| 接口 | 模块 | 说明 |
|------|------|------|
| `save_report(client, draft_input)` | `report` | 创建新报告或更新已有报告的元数据 |
| `upload_report_files(client, report_id, report_file, pdf_file)` | `upload_files` | 上传报告正文（Word + PDF） |
| `upload_model_file(client, report_id, model_file)` | `upload_files` | 上传财务模型文件 |
| `validate_report(client, report_id)` | `report` | 提交前检查报告是否完整 |
| `submit_report(client, report_id)` | `report` | 将报告提交审批 |
| `retract_report(client, report_id)` | `report` | 撤回已提交的报告以便修改 |
| `publish_report(client, report_id)` | `report` | 审批通过后发布报告（SA/admin） |
| `reject_report(client, report_id, reason)` | `report` | 退回不合格的报告要求修改（SA/admin） |
| `deactivate_report(client, report_id)` | `report` | 废弃不再使用的报告（admin） |

### Coverage

| 接口 | 模块 | 说明 |
|------|------|------|
| `resolve_coverage(client, ticker, first_analyst_email)` | `coverage` | 确认某股票是否已被分析师覆盖 |
| `create_coverage(client, ticker, english_name, sector_id, ...)` | `coverage` | 为新股票建立覆盖关系 |
| `list_coverage_history(client, ticker, first_analyst_email)` | `coverage` | 查看某股票的历史研报记录 |

### 分析师

| 接口 | 模块 | 说明 |
|------|------|------|
| `resolve_analyst_by_email(client, email)` | `analyst` | 通过邮箱获取分析师完整信息 |
| `search_analyst_by_name(client, name)` | `analyst` | 按姓名搜索分析师 |
| `upsert_analyst(client, email, english_name, ...)` | `analyst` | 新增或更新分析师档案（admin） |
| `set_analyst_active(client, email, is_active)` | `analyst` | 启用或停用分析师账号（admin） |

### 模板

| 接口 | 模块 | 说明 |
|------|------|------|
| `resolve_template(client, report_type, language, dest_dir=".")` | `template` | 获取指定类型的报告模板 |
| `upsert_template(client, report_type, language, template_local_path, ...)` | `template` | 发布或更新报告模板 |
| `reuse_template(client, report_type, language, same_as_report_type)` | `template` | 让多种报告类型共用同一套模板 |

## 报告状态机

```
  draft ──submit──→ submitted ──publish──→ published
    ↑                  │
    └── retract ←──────┤
                       ↓ reject
                    rejected
                       │
    └── retract ←──────┘
```

- `submit_report`：draft / rejected → submitted
- `retract_report`：submitted / rejected → draft
- `publish_report`：submitted → published（SA/admin）
- `reject_report`：submitted → rejected（SA/admin，需 reason）
- `deactivate_report`：任何状态，设 is_active=false（admin）

## 典型工作流

新建并提交报告：

1. `resolve_coverage` → 获得 coverage_id（未命中则询问用户是否 `create_coverage`）
2. `save_report` → 获得 report_id
3. `upload_report_files` → 上传 Word + PDF
4. `validate_report` → 校验完整性（可选；submit 内部自动调用）
5. `submit_report` → 提交审批

提交失败后沿用原 report_id，重新 `save_report` + `upload_report_files`，再 validate → submit。

## 报告表直接查询

用户通常不会提供 report_id（UUID）。根据用户意图选择查询入口，从结果中获取 report_id 后再调用操作接口。

| 用户意图 | 查询条件 |
|----------|----------|
| 某只股票的报告 | `.eq("ticker", ...)` |
| 某个状态的报告 | `.eq("status", ...)` — draft / submitted / published / rejected |
| 某分析师的报告 | `.eq("lead_analyst_email", ...)` |
| 按标题搜索 | `.ilike("title", "%关键词%")` |
| 某段时间内的报告 | `.gte("created_at", ...)` / `.lte("created_at", ...)` |

多条件可组合；默认加 `.eq("is_active", True)` 排除废弃报告。

RLS 可见范围：admin 全部；SA 可见 submitted / published / rejected；analyst 可见自己 owned 的 + 所有 published。

查询示例、report_status_log 审计日志查询、报告文件下载，以及字典表操作，统一见 `references/direct-queries.md`。

## 字典表

`region`、`sector`、`rating`、`report_type` 直接用 `client.table()` 读写。其他表禁止直接写入，走专用接口或 RPC。详情和示例见 `references/direct-queries.md`「字典表」。

## 认证

通过 `connection.get_client()` 获取 client。
若 `user.json` 不存在，向用户索取邮箱和密码后调用 `get_client(email=..., password=...)`。
认证流程、配置文件和测试连接约束详见 `references/authentication.md`。

## 业务约束

- `save_report`：`report_id` 首次为 `None`，后续沿用同一 ID；只保存元数据，不操作文件
- `upload_report_files` / `upload_model_file`：需在 `save_report` 之后调用，report 必须处于 draft 或 rejected 状态
- `create_coverage`：仅在 `resolve_coverage` 未命中且用户确认"Coverage 已完成审批"后调用
- `reuse_template`：静态路径复制；主模板重新上传后需重新执行才能同步
- `report_type` 取值和分析师列表约束见 README「业务常量」

## 参考文件

- **`references/interfaces.md`** — 所有接口的完整签名、参数、返回值和代码示例
- **`references/authentication.md`** — 认证流程、配置文件、凭据管理、首次使用、测试连接约束
- **`references/direct-queries.md`** — 直接查表操作（report / report_status_log / coverage / analyst / 字典表等），含查询示例、文件下载、RLS 约束速查
