# skills_neolyst 设计文档

## 1. 定位与边界

`neolyst` 是 `neoskills` 中面向 Neolyst 的数据库操作 skill。它负责承接所有需要访问和操作 Neolyst 数据库的能力。`submit_report` 是当前优先落地的能力之一。

`report_maker` 负责生成报告产物、补齐业务所需信息，并组装出满足 `neolyst` 契约的输入。`neolyst` 负责拿到完整输入后执行查询、校验、文件上传、数据写入和提交相关操作。

`neolyst` 对上游暴露的是稳定的业务接口，而不是底层数据库操作集合。

`neolyst` 明确不负责以下事项：

- 与用户对话补字段
- 替上游做业务决策
- 对上游暴露零散的底层数据库动作

## 2. 设计决策

### 2.1 接口形态

- `neolyst` 对外暴露四个接口：`resolve_coverage`、`create_coverage`、`validators` 与 `submit_report`。
- `resolve_coverage` 用于解析并确认 `coverage_id`。
- `create_coverage` 用于创建新的 `coverage` 与 `coverage_analyst` 关系。
- `validators` 用于执行提交前校验并暴露阻断项。
- `submit_report` 用于执行完整提交。

### 2.2 submission 契约

- `submission` 由 `neolyst` 定义并维护，`report_maker` 依赖该契约，而不是反过来。
- `submission` 采用全打平结构，业务字段和文件路径字段都位于顶层。
- `submission` 不携带执行上下文字段，例如 `workspace_root`、`trace_id`、`server_url_override`、`dry_run`。
- 文件输入统一使用本地路径，由 `neolyst` 自行上传到 Neolyst Storage。
- `company` / `company_flash` 的 `submission` 必须携带已经确认好的 `coverage_id`。

### 2.3 身份与会话策略

- Neolyst Supabase 的登录身份由 `neolyst` 管理和复用，`validators` 与 `submit_report` 的相关读写都使用该身份。
- 使用 `email + password` 登录，账号、密码和登录态保存在工作目录根目录的 `/.neolyst`；只支持一个登录身份，会话失效时重新登录并更新 `/.neolyst`。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系。

### 2.4 技术访问方式

- 本 skill 直接使用 `@supabase/supabase-js` 与 Neolyst Supabase 交互，不使用 Supabase CLI 作为业务入口。
- 本 skill 的 TypeScript 脚本通过 `pnpm` 管理和执行。

### 2.5 Supabase URL

- Supabase URL 由 skill 负责确定；skill 内置默认 Supabase URL，`/.neolyst.server.url` 可作为覆盖项。

### 2.6 提交流程

- 提交流程采用两段式：先创建并保存 report 相关内容，再执行提交；提交失败时保留已创建的中间结果。
- 整体行为对齐 Neolyst Web 的 `Analyst Submit`，不引入独立提交流程。

### 2.7 校验与错误语义

- 提交前校验由 `neolyst` 负责，`validators` 用于暴露结构校验、来源合法性校验，以及公司类报告所需的 Coverage 与 analyst 关系校验。
- `resolve_coverage` 按 `ticker` 查询候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_id` 是否属于该 `coverage` 的分析师列表；只要该 `1作` 出现在列表中，不要求其在 `coverage_analyst` 中也必须是 `role = 1`。
- `resolve_coverage` 命中唯一 `coverage` 时返回 `coverage_id`；命中多条或未命中时直接抛出具体错误。
- `create_coverage` 创建成功时返回新的 `coverage_id`；创建失败时直接抛出具体错误。
- `validators` 和 `submit_report` 在失败时都直接抛出具体错误，不返回包裹态结果；错误信息必须足够明确，让上游 LLM 据此补字段、重新确认，或中止流程。

## 3. 实现落地

### 3.1 对外接口

- 对外接口包括：`resolve_coverage`、`create_coverage`、`validators`、`submit_report`
- `resolve_coverage(ticker, first_analyst_id)` 用于 `company` / `company_flash` 在提交前确认 `coverage_id`
- `create_coverage(payload)` 用于创建新的 `coverage` 与 `coverage_analyst` 关系，并返回 `coverage_id`
- `validators(submission)` 用于校验输入并暴露阻断项
- `submit_report(submission)` 接收结构化报告元数据和本地文件路径并执行提交
- `submission` 由 `report_maker` 直接产出
- 不单独暴露 `upload file` 和 `save draft`
- 不支持基于已有 draft 再提交

输入结构与字段说明：

```json
{
  "title": "string",
  "report_type": "company | sector | company_flash | sector_flash | common",
  "coverage_id": "uuid | null",
  "ticker": "string | null",
  "rating": "string | null",
  "target_price": "string | null",
  "region_code": "string | null",
  "sector_id": "uuid | null",
  "report_language": "en | zh",
  "contact_person_id": "uuid | null",
  "investment_thesis": "string | null",
  "certificate_confirmed": true,
  "analysts": [
    {
      "analyst_id": "uuid",
      "role": 1,
      "sort_order": 1
    }
  ],
  "report_file": "/abs/or/relative/path/to/report.docx",
  "pdf_file": "/abs/or/relative/path/to/report.pdf",
  "model_file": "/abs/or/relative/path/to/model.xlsx"
}
```

- `title`：报告标题
- `report_type`：报告类型
- `coverage_id`：公司类报告对应的 coverage ID
- `ticker`：股票代码
- `rating`：评级
- `target_price`：目标价
- `region_code`：地区代码
- `sector_id`：行业 ID
- `report_language`：`en` 或 `zh`
- `contact_person_id`：联系人 analyst ID，属于提交元数据的一部分
- `investment_thesis`：投资要点
- `certificate_confirmed`：合规确认标记
- `analysts`：分析师列表
- `report_file`：报告主文件路径
- `pdf_file`：可选 PDF
- `model_file`：模型文件路径

`coverage_id` 规则：

- `company` / `company_flash` 在提交前必须先通过 `resolve_coverage(ticker, first_analyst_id)` 确认 `coverage_id`
- `resolve_coverage` 先按 `ticker` 查找候选 `coverage`，再通过 `coverage_analyst` 判断报告 `1作 analyst_id` 是否属于该 `coverage` 的分析师列表
- 只要 `1作 analyst_id` 出现在该 `coverage` 的分析师列表中，不要求它在 `coverage_analyst` 中也必须是 `role = 1`
- 唯一命中时，将该 `coverage_id` 写入 `submission`
- 未命中时，调用 `create_coverage` 创建新的 `coverage`，并将返回的 `coverage_id` 写入 `submission`
- 命中多条时，直接抛出具体错误，由上游处理

`contact_person_id` 规则：

- `contact_person_id` 由 `report_maker` 在提交前确认后写入 `submission` 元数据
- 当 `analysts` 只有 1 人时，可直接使用该 analyst 作为 `contact_person_id`
- 当 `analysts` 超过 1 人时，应由 `report_maker` 通过对话交互确认

返回结构：

`submit_report` 成功时返回：

```json
{
  "ok": true,
  "report_id": "uuid",
  "status": "submitted",
  "version_no": 1
}
```

失败时直接抛出具体错误，不返回包裹态错误对象。


### 3.2 整体结构

整体骨架如下：

```text
neolyst/
  SKILL.md
  scripts/
    auth.ts
    config.ts
    client.ts
    coverage.ts
    submit-report.ts
    storage.ts
    validators.ts
```

模块分工：

- `auth.ts`：登录、刷新、session 读写
- `config.ts`：处理根目录 `/.neolyst`
- `client.ts`：导出 `getAuthenticatedClient()`
- `coverage.ts`：实现 `resolve_coverage` 与 `create_coverage`
- `submit-report.ts`：实现完整提交流程
- `storage.ts`：上传文件、构造 Storage 路径
- `validators.ts`：输入校验、业务前置校验


### 3.3 SKILL.md 的职责

`SKILL.md` 只做以下几件事：

- 说明 skill 名称为 `neolyst`，聚焦 `submit_report`
- 说明 skill 会在工作目录根下使用 `/.neolyst`
- 说明当 `/.neolyst` 缺失或 session 失效时，会提示输入 `email/password`
- 说明输入应对齐 `report_maker` 输出的结构化 payload
- 说明 skill 会自己上传文件，再创建并提交 report

`SKILL.md` 不承载过多实现细节，例如：

- Supabase client 创建细节
- 具体 JSON 字段逐一解释
- 复杂的异常分支

实现细节放在 `scripts/*.ts`。

### 3.4 提交流程

`scripts/submit-report.ts` 负责主流程实现。

职责：

- 串联认证、校验、建 report、上传文件、保存内容与执行提交

主流程入口：

- `submitReport(payload)`

内部流程：

1. 获取已认证 client
2. 校验 payload 与来源合法性
3. 创建 report
4. 上传文件
5. 保存 report 内容与文件路径
6. 执行 direct submit
7. 返回结果

失败处理：

- 提交失败时，保留已创建的 report / draft 状态
- 避免文件已上传但业务对象丢失

### 3.5 配置

`/.neolyst` 配置由 `scripts/config.ts` 负责。

职责：

- 定位工作目录根下的 `/.neolyst`
- 读取 `/.neolyst`
- 写入 `/.neolyst`
- 提供一个稳定的数据结构给其他脚本使用

导出：

- `getNeolystConfigPath()`
- `readNeolystConfig()`
- `writeNeolystConfig(config)`

内部数据结构：

```ts
type NeolystConfig = {
  auth?: {
    email?: string
    password?: string
  }
  session?: Record<string, unknown> | null
}
```

### 3.6 身份与会话

- 只支持 `email + password` 登录
- 使用 Supabase Auth 的 `signInWithPassword`
- 不支持 magic link
- 不支持 SSO
- 保存明文 `email/password` 与 session，用于自动重新登录
- 将 `/.neolyst` 加入 `.gitignore`

配置结构如下：

```json
{
  "auth": {
    "email": "",
    "password": ""
  },
  "session": {}
}
```

公共入口：

- 统一使用 `getAuthenticatedClient()`
- 所有需要访问 Supabase 的逻辑都通过该入口获取 client
- session 无效时，尝试恢复，失败后提示登录

返回结构：

```ts
type AuthenticatedClient = {
  client: SupabaseClient
  session: Session
  user: User
}
```

`scripts/auth.ts`：

职责：

- 使用 `email + password` 登录 Supabase
- 根据 `/.neolyst` 中保存的 `auth` 做自动登录
- 当 session 不可用时，执行重新登录
- 登录成功后回写最新 session 到 `/.neolyst`

导出：

- `signInWithStoredPassword()`
- `signInWithPrompt()`
- `refreshOrReLoginIfNeeded()`

说明：

- 使用 `/.neolyst.auth.email/password`
- 不提供复杂的账户切换能力

`scripts/client.ts`：

职责：

- 统一创建可用的 Supabase client
- 对外提供单一公共入口：`getAuthenticatedClient()`

导出：

- `getAuthenticatedClient()`

行为约定：

- 优先使用 `/.neolyst.session`
- 如果 session 无效，则尝试使用 `/.neolyst.auth` 自动登录
- 如仍失败，再提示用户输入账号密码
- 成功后统一回写 `/.neolyst`


### 3.7 校验

`scripts/validators.ts` 负责校验逻辑。

职责：

- 校验 `submit_report` 的输入 payload
- 执行业务前置校验
- 对齐 `Analyst Submit` 已实现行为

校验范围：

- 基础字段非空检查
- report type 对应字段必填关系
- analysts 数量与唯一性校验
- 文件路径存在性检查
- 可选的本地文件扩展名预校验

输入约束：

- `title` 非空
- `report_type` 非空
- `report_language` 非空
- `investment_thesis` 非空
- `analysts` 至少 1 个
- `contact_person_id` 必须提供
- `certificate_confirmed = true`
- `report_file` 已提供

按类型要求：

- `company`：`coverage_id`、`ticker`、`rating`、`target_price`、`model_file`
- `company_flash`：`coverage_id`、`ticker`
- `sector`：`region_code`、`sector_id`
- `sector_flash`：`region_code`、`sector_id`
- `common`：`region_code`

来源合法性校验：

- `report_type` 必须是有效 active type
- `region_code` 必须来自有效 region
- `sector_id` 必须来自有效 sector
- `analysts[].analyst_id` 必须来自 active analyst
- `contact_person_id` 必须属于 `analysts[].analyst_id`
- 公司类报告还需满足 `coverage_id`、`ticker` 与 `coverage_analyst` 的交叉校验
- `resolve_coverage` 使用规则为：先按 `ticker` 查询候选 `coverage`，再用报告 `1作 analyst_id` 过滤 `coverage_analyst`
- 只要该 `1作 analyst_id` 存在于某条 `coverage` 的分析师列表中，就认定该 `coverage` 命中，不要求 `coverage_analyst.role = 1`

导出：

- `resolveCoverage(ticker, firstAnalystId)`
- `createCoverage(payload)`
- `validateSubmitReportPayload(payload)`
- `assertRequiredFieldsByReportType(payload)`
- `validateAnalystAssignments(payload)`

### 3.8 文件上传

- 由本 skill 自己负责上传文件
- 允许的文件类型：
  - 报告主文件：`.doc` / `.docx` / `.ppt` / `.pptx`
  - PDF：`.pdf`
  - Model：`.xls` / `.xlsx` / `.csv`
- 不将 `chief approval screenshot` 纳入核心提交流程

`scripts/storage.ts`：

职责：

- 处理报告文件上传
- 生成 storage 路径
- 对齐 Neolyst 的文件命名方式

导出：

- `buildReportStoragePath(params)`
- `uploadReportFiles(client, params)`

`uploadReportFiles` 负责：

- 上传 report 主文件
- 可选上传 PDF
- 对 `company` 类型上传 model
- 返回上传后的路径与原始文件名

上传结果：

```ts
type UploadedReportFiles = {
  word_file_path: string | null
  word_file_name: string | null
  pdf_file_path: string | null
  pdf_file_name: string | null
  model_file_path: string | null
  model_file_name: string | null
}
```

## 4. 联调与环境

### 4.1 联调测试环境

- URL：`http://47.57.213.88:80`
- Admin username：`admin@neolyst.com`
- Admin password：`Admin123`

## 5. 对 report_maker 的新增要求

为对接 `neolyst` 设计，`report_maker` 需要增加或调整以下能力：

- 在 `company` / `company_flash` 提交前，先调用 `resolve_coverage(ticker, first_analyst_id)` 确认 `coverage_id`
- 在 `resolve_coverage` 未命中时，调用 `create_coverage` 创建新的 `coverage`
- 在组装 `submission` 时，输出扁平结构，不再使用 `files` 嵌套对象
- 将最终确认后的 `coverage_id` 写入 `submission`
- 将报告 `1作 analyst_id` 明确传给 `resolve_coverage`，作为 coverage 解析依据
- 当 `resolve_coverage`、`create_coverage`、`validators` 或 `submit_report` 抛出具体错误时，负责根据错误内容继续补字段、重新确认或中止流程
- 在多人分析师场景下，继续负责确认 `contact_person_id`
- 在提交前继续负责准备完整文件路径，包括 `report_file`、可选 `pdf_file` 以及公司类报告所需的 `model_file`
