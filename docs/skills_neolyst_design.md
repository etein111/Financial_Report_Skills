# skills_neolyst 设计文档

## 1. 定位与范围

### 1.1 背景

`report_maker` 是一条流程，最后一步调用 `neolyst` skill 提交报告到 Neolyst。

### 1.2 职责定位

- 接收标准化提交数据，执行报告提交
- 负责与 Neolyst Supabase 的读写交互
- 管理和复用 Neolyst Supabase 的登录身份
- 不绑定 `report_maker` 的内部目录结构
- 不负责报告生成、模板渲染、要素抽取和目录整理

### 1.3 目标

- 提供 `submit_report(submission)`，作为 `report_maker` 流程的最后一步，将报告提交到 Neolyst
- 在本 skill 内管理和复用 Neolyst Supabase 身份，支撑与 Neolyst Supabase 的相关读写

## 2. 核心设计

### 2.1 Skill 形态

- 本 skill 后续可以扩展其他与 Neolyst Supabase 交互的接口，当前先集中实现 `submit_report(submission)`。

### 2.2 与 `report_maker` 的关系

- `report_maker` 负责报告处理和提交数据准备，本 skill 负责与 Neolyst Supabase 交互并执行提交，两者通过标准化 `submission` 衔接。

### 2.3 Supabase 身份与会话策略

- Neolyst Supabase 的登录身份由本 skill 管理和复用，`submit_report` 的相关读写都使用该身份。
- 本 skill 使用 `email + password` 登录，登录态保存在工作目录根目录的 `/.neolyst`；当前只支持一个登录身份，会话失效时重新登录并更新 `/.neolyst`。
- 本 skill 不做代理执行，因为这会破坏 Neolyst 的安全性，也不符合实际业务关系；代理问题本质上来自当前尚未实现分析师直接对接 Agent。

### 2.4 技术访问方式

- 本 skill 直接使用 `@supabase/supabase-js` 与 Neolyst Supabase 交互，不使用 Supabase CLI 作为业务入口。

### 2.5 来源合法性校验

- 提交前由本 skill 负责来源合法性校验，校验口径对齐当前服务端实现。
- 公司类报告额外校验 Coverage 与 analyst 关系。

### 2.6 两段式提交

- 提交流程采用两段式：先创建并保存 report 相关内容，再执行提交；提交失败时保留已创建的中间结果。
- 整体行为对齐当前 Web 的 `Analyst Submit`。

## 3. 实现落地

### 3.1 对外接口

- 当前对外核心接口：`submit_report(submission)`
- 不单独暴露 `upload file` 和 `save draft`
- 不支持基于已有 draft 再提交

### 3.2 登录与会话细节

- 当前只支持 `email + password` 登录
- 使用 Supabase Auth 的 `signInWithPassword`
- 不支持 magic link
- 不支持 SSO
- 当前版本允许同时保存明文 `email/password` 与 session，用于自动重新登录
- 建议将 `/.neolyst` 加入 `.gitignore`

建议最小结构如下：

```json
{
  "auth": {
    "email": "",
    "password": ""
  },
  "session": {}
}
```

### 3.3 内部公共入口

- 统一使用 `getAuthenticatedClient()`
- 所有需要访问 Supabase 的逻辑都通过该入口获取 client
- session 无效时，先尝试恢复，失败后提示登录

推荐返回结构：

```ts
type AuthenticatedClient = {
  client: SupabaseClient
  session: Session
  user: User
}
```

### 3.4 输入来源

- `submit_report` 接收结构化报告元数据和本地文件路径
- 当前输入由 `report_maker` 直接产出

### 3.5 建议输入结构

```json
{
  "title": "string",
  "report_type": "company | sector | company_flash | sector_flash | common",
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
  "files": {
    "report_file": "/abs/or/relative/path/to/report.docx",
    "pdf_file": "/abs/or/relative/path/to/report.pdf",
    "model_file": "/abs/or/relative/path/to/model.xlsx"
  }
}
```

### 3.6 字段约束

- `title`：报告标题
- `report_type`：报告类型，必须来自有效模板类型
- `ticker`：公司类报告使用
- `rating`：`company` 必填
- `target_price`：`company` 必填
- `region_code`：`sector` / `sector_flash` / `common` 必填
- `sector_id`：`sector` / `sector_flash` 必填
- `report_language`：`en` 或 `zh`
- `contact_person_id`：当前按现有实现视为可选
- `investment_thesis`：提交前必填
- `certificate_confirmed`：提交前必须为 `true`
- `analysts`：至少 1 个，最多 4 个，必须唯一
- `files.report_file`：报告主文件路径
- `files.pdf_file`：可选 PDF
- `files.model_file`：`company` 必填

通用要求：

- `title` 非空
- `report_type` 非空
- `report_language` 非空
- `investment_thesis` 非空
- `analysts` 至少 1 个
- `certificate_confirmed = true`
- `report_file` 已提供并上传成功

按类型补充要求：

- `company`：`ticker`、`rating`、`target_price`、`model_file`
- `company_flash`：`ticker`
- `sector`：`region_code`、`sector_id`
- `sector_flash`：`region_code`、`sector_id`
- `common`：`region_code`

来源合法性校验：

- `report_type` 必须是有效 active type
- `region_code` 必须来自有效 region
- `sector_id` 必须来自有效 sector
- `analysts[].analyst_id` 必须来自 active analyst
- 公司类报告还需满足 Coverage 与 analyst 交集约束

### 3.7 文件上传

- 由本 skill 自己负责上传文件
- 允许的文件类型：
  - 报告主文件：`.doc` / `.docx` / `.ppt` / `.pptx`
  - PDF：`.pdf`
  - Model：`.xls` / `.xlsx` / `.csv`
- 当前不将 `chief approval screenshot` 纳入核心提交流程

### 3.8 执行流程

1. 调用 `getAuthenticatedClient()`
2. 读取并校验输入
3. 校验来源合法性
4. 创建 report
5. 上传文件
6. 保存 report 内容与文件路径
7. 执行提交
8. 返回结果

### 3.9 失败处理与已知差异

失败处理：

- 提交失败时，保留已创建的 report / draft 状态
- 避免文件已上传但业务对象丢失

已知差异：

- `contact_person_id` 当前按现有实现仍可选
- 如果后续要与需求文档完全收敛，再单独调整

### 3.10 Skill 内部模块建议

可按以下最小结构组织：

```text
neolyst/
  SKILL.md
  scripts/
    auth.ts
    config.ts
    client.ts
    submit-report.ts
    storage.ts
    validators.ts
```

模块职责：

- `auth.ts`：登录、刷新、session 读写
- `config.ts`：处理根目录 `/.neolyst`
- `client.ts`：导出 `getAuthenticatedClient()`
- `submit-report.ts`：实现完整提交流程
- `storage.ts`：上传文件、构造 Storage 路径
- `validators.ts`：输入校验、业务前置校验

### 3.11 建议结果结构

`submit_report` 成功时建议返回：

```json
{
  "ok": true,
  "report_id": "uuid",
  "status": "submitted",
  "version_no": 1
}
```

失败时建议返回：

```json
{
  "ok": false,
  "error": "human readable message"
}
```

### 3.12 SKILL.md 的职责

`SKILL.md` 建议只做以下几件事：

- 说明 skill 名称为 `neolyst`
- 说明当前先聚焦 `submit_report`
- 说明 skill 会在工作目录根下使用 `/.neolyst`
- 说明当 `/.neolyst` 缺失或 session 失效时，会提示输入 `email/password`
- 说明输入应对齐 `report_maker` 输出的结构化 payload
- 说明 skill 会自己上传文件，再创建并提交 report

`SKILL.md` 不建议承载过多实现细节，例如：

- Supabase client 创建细节
- 具体 JSON 字段逐一解释
- 复杂的异常分支

这些细节应放在 `scripts/*.ts` 中实现。

### 3.13 scripts/config.ts

职责：

- 定位工作目录根下的 `/.neolyst`
- 读取 `/.neolyst`
- 写入 `/.neolyst`
- 提供一个稳定的数据结构给其他脚本使用

建议导出：

- `getNeolystConfigPath()`
- `readNeolystConfig()`
- `writeNeolystConfig(config)`

建议内部数据结构：

```ts
type NeolystConfig = {
  auth?: {
    email?: string
    password?: string
  }
  session?: Record<string, unknown> | null
}
```

### 3.14 scripts/auth.ts

职责：

- 使用 `email + password` 登录 Supabase
- 根据 `/.neolyst` 中保存的 `auth` 做自动登录
- 当 session 不可用时，执行重新登录
- 登录成功后回写最新 session 到 `/.neolyst`

建议导出：

- `signInWithStoredPassword()`
- `signInWithPrompt()`
- `refreshOrReLoginIfNeeded()`

说明：

- 当前允许使用 `/.neolyst.auth.email/password`
- 当前不做复杂的账户切换能力

### 3.15 scripts/client.ts

职责：

- 统一创建可用的 Supabase client
- 对外提供单一公共入口：`getAuthenticatedClient()`

建议导出：

- `getAuthenticatedClient()`

建议返回：

```ts
type AuthenticatedClient = {
  client: SupabaseClient
  session: Session
  user: User
}
```

推荐行为：

- 优先使用 `/.neolyst.session`
- 如果 session 无效，则尝试使用 `/.neolyst.auth` 自动登录
- 如仍失败，再提示用户输入账号密码
- 成功后统一回写 `/.neolyst`

### 3.16 scripts/validators.ts

职责：

- 校验 `submit_report` 的输入 payload
- 执行业务前置校验
- 对齐当前 `Analyst Submit` 已实现行为

建议至少覆盖：

- 基础字段非空检查
- report type 对应字段必填关系
- analysts 数量与唯一性校验
- 文件路径存在性检查
- 可选的本地文件扩展名预校验

建议导出：

- `validateSubmitReportPayload(payload)`
- `assertRequiredFieldsByReportType(payload)`
- `validateAnalystAssignments(payload)`

### 3.17 scripts/storage.ts

职责：

- 处理报告文件上传
- 生成 storage 路径
- 对齐当前 Neolyst 的文件命名方式

建议导出：

- `buildReportStoragePath(params)`
- `uploadReportFiles(client, params)`

`uploadReportFiles` 建议负责：

- 上传 report 主文件
- 可选上传 PDF
- 对 `company` 类型上传 model
- 返回上传后的路径与原始文件名

建议返回结构：

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

### 3.18 scripts/submit-report.ts

职责：

- 实现 `submit_report` 全流程
- 调用 `getAuthenticatedClient()`
- 校验输入
- 查询动态来源数据
- 创建 report
- 上传文件
- 保存 report 内容
- 执行 direct submit

建议导出：

- `submitReport(payload)`

建议内部流程：

1. 获取已认证 client
2. 校验 payload
3. 查询 report type / region / sector / analyst 合法性
4. 创建 report
5. 上传文件
6. 保存 report 内容
7. 执行 direct submit
8. 返回结果

### 3.19 submitReport 的建议返回值

```ts
type SubmitReportResult =
  | {
      ok: true
      report_id: string
      status: "submitted"
      version_no: number
    }
  | {
      ok: false
      error: string
    }
```

## 4. 联调与环境

### 4.1 当前联调测试环境

- URL：`http://47.57.213.88:80`
- Admin username：`admin@neolyst.com`
- Admin password：`Admin123`
