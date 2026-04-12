# neolyst

Neolyst Supabase 数据访问层。实现位置：`scripts/`。

技术栈：Python `supabase-py` + `uv` 管理依赖与执行环境。数据库结构真相以 `supabase/migrations/*.sql` 为准。

## 业务常量

- `report_type` 取值：`company`、`sector`、`company_flash`、`sector_flash`、`macro`、`strategy`、`quantitative`、`bond`
- 分析师列表：最多 8 人；`author_order=1` 为第一作者

## 报告生命周期

```
                    publish
  draft ──submit──→ submitted ────→ published
    ↑                  │
    │      retract     ↓ reject
    │              rejected
    │                  │
    └── retract ←─────┘
```

典型提交流程：

```
机器生成结果 → save_draft_report → [人工确认] → validate_draft → submit_report
                  ↑                                                      │
                  └──────── 提交失败：save_draft 追加新版本 ←──────────────┘
```

- draft 驱动：机器结果先存 draft，不要求满足提交条件；人工确认后再提交
- 提交失败后沿用原 report_id 追加新版本，重新走 validate → submit
- 撤回（retract）：submitted 或 rejected 的报告可撤回为 draft 重新编辑；rejected 不能直接重提，必须先撤回 draft 再提交
- 整体行为对齐 Neolyst Web 的 Analyst Submit

## 内部架构

### Storage 结构

两个独立 bucket：

| Bucket | 用途 | 路径规则 |
|--------|------|---------|
| `templates` | 模板资产 | `templates/{report_type}/{language}/template.docx` / `schema.yaml`（RPC `get_template_storage_paths` 生成） |
| `reports` | 报告版本资产 | `reports/{report_id}/v{version_no}/{原始文件名}`（draft_report.py 生成，版本间独立目录） |

DB 中存储的路径包含 bucket 前缀。`storage.py` 只负责上传/下载，不拼路径。

### 模块依赖方向

依赖保持单向，`connection` 是基础设施层，不依赖任何业务模块：

```
connection  ←  storage, analyst, coverage, rpc
connection + storage + rpc  ←  draft_report
connection + rpc  ←  coverage, submit_report, retract_report
connection  ←  validators
```

`rpc.py` 是 RPC 调用薄封装（异常转换 + 结果提取），不依赖 connection，被 coverage、draft_report、submit_report、retract_report 等模块统一使用。

## 文件路径准源

- `save_draft_report` 输入中的 `report_file`、`pdf_file`、`model_file` 仅用于上传前定位本地文件；文件路径的唯一准源是 `report_version` 表的持久化字段。
- `snapshot_json` 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
- 模板文件路径以 `report_template.template_file_path` 与 `report_template.schema_file_path` 为准，不由 `report_type` 公式推导。

## 开发与测试

### 连接配置

| 配置来源 | 用途 | 提交到版本库 |
|---------|------|------------|
| `neolyst.yaml` | 运行时默认连接（URL + anon_key） | 是（anon_key 是公开客户端 key） |
| `user.json` | 用户凭据（email + password） | 否 |
| `session.json` | 登录态（access_token + refresh_token） | 否 |

`neolyst.yaml` 当前可指向 staging。anon key 是公开客户端 key，不是密钥。

### 测试环境变量

本地测试必须设置以下环境变量，**不允许回落到 `neolyst.yaml` 默认值**：

```bash
export NEOLYST_TEST_URL="https://xxx.supabase.co"
export NEOLYST_TEST_ANON_KEY="eyJ..."
export NEOLYST_TEST_EMAIL="test@neolyst.com"
export NEOLYST_TEST_PASSWORD="xxx"
```

pytest 的 `conftest.py` 会将 `NEOLYST_TEST_URL` / `NEOLYST_TEST_ANON_KEY` 映射为运行时的 `NEOLYST_URL` / `NEOLYST_ANON_KEY`。
