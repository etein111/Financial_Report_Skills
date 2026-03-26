# skills_neolyst 设计文档

## 1. 背景

本设计文档定义 `neolyst` skill 第一版的目标、边界与实现方案。

设计背景：

- 当前存在一个典型工作流：`report_maker` 先生成标准格式报告，再由 `neolyst` skill 提交到 Neolyst 的 Supabase。
- 第一版目标是先把链路跑通，不处理“代替分析师登录 / impersonation / act_as_analyst”。
- 因此，第一版所有写入都以当前登录用户的 Supabase 身份执行；如果是 Admin 通过工作台提交报告，则 Supabase 中记录的 actor 与 owner 都是 Admin。

## 2. 第一版目标

`neolyst` skill 第一版只解决以下问题：

- 在工作目录中保存并复用 Supabase 登录态
- 在需要时提示用户输入 `email/password` 完成登录
- 使用 `@supabase/supabase-js` 访问 Neolyst 的 Supabase
- 提供一个核心业务能力：`submit_report`
- `submit_report` 对齐当前 `Analyst Submit` 已实现行为，而不是未来理想目标态

## 3. 第一版非目标

以下内容明确不属于第一版：

- 代分析师提交报告
- `act_as_analyst`
- editor 角色设计
- 多身份切换
- 独立的 `save_draft` 对外能力
- 已有 draft 再提交
- 用户/模板/区域/分析师资料等管理能力的 skill 化
- 把工作台逻辑放入 `neolyst-web`

## 4. 核心决策

### 4.1 Skill 形态

- 第一版只做一个 skill：`neolyst`
- 不拆成 `neolyst_admin` / `neolyst_analyst`
- 不按角色拆 skill
- skill 内部不再暴露过多对外业务能力，第一版先聚焦 `submit_report`

### 4.2 身份模型

- 第一版不做代理执行
- skill 使用当前操作者自己的 Supabase 身份
- Admin 调用 `submit_report` 时，Supabase 中的 actor 和 `owner_user_id` 都是 Admin
- 如果未来需要“归属 analyst”或“代 analyst 执行”，作为第二阶段需求单独设计

### 4.3 技术访问方式

- 使用 `@supabase/supabase-js`
- 不使用 Supabase CLI 作为业务访问入口
- skill 直接访问 Supabase
- `neolyst-web` 保持面向人的薄界面，不承载工作台专用逻辑

### 4.4 登录态持久化

- skill 在工作目录根目录保存配置文件 `/.neolyst`
- 文件格式为 JSON
- 第一版结构如下：

```json
{
  "auth": {
    "email": "",
    "password": ""
  },
  "session": {}
}
```

- `session` 保存 Supabase 登录成功后返回的 session 对象
- 第一版允许同时保存明文 `email/password`，用于自动重新登录

完整示例：

```json
{
  "auth": {
    "email": "admin@neolyst.com",
    "password": "Admin123"
  },
  "session": {
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "token_type": "bearer",
    "expires_in": 3600,
    "expires_at": 1770000000,
    "user": {
      "id": "<user_id>",
      "email": "admin@neolyst.com",
      "app_metadata": {
        "role": "admin"
      },
      "user_metadata": {}
    }
  }
}
```

## 5. 认证与会话设计

### 5.1 登录方式

- 第一版只支持 `email + password` 登录
- 使用 Supabase Auth 的 `signInWithPassword`
- 不支持 magic link
- 不支持 SSO

### 5.1.1 当前联调测试环境

第一版生成和联调 `neolyst` skill 时，可使用以下 Neolyst Supabase 测试环境：

- URL：`http://47.57.213.88:80`
- Admin username：`admin@neolyst.com`
- Admin password：`Admin123`

说明：

- 这组信息用于本地测试与 skill 联调
- 第一版 skill 实现允许将测试账号的明文 `email/password` 与登录后的 session 一并写入 `/.neolyst`

### 5.2 何时提示登录

工作流如下：

1. 调用 `submit_report`
2. 读取工作目录根下的 `/.neolyst`
3. 如果存在有效 session，则直接继续
4. 如果 session 不存在或已失效，则提示输入 `email` 和 `password`
5. 登录成功后，将新 session 写回 `/.neolyst`
6. 继续当前这次提交

### 5.3 会话存储原则

- 第一版允许同时保存 session 与明文密码
- session 文件名固定为 `/.neolyst`
- 当前版本默认只支持一个登录身份
- 建议将 `/.neolyst` 加入 `.gitignore`

## 6. 内部公共入口

第一版不再拆分 `ensure login` 和 `create client`。

统一收敛为一个内部函数：

- `getAuthenticatedClient()`

职责：

1. 读取 `/.neolyst`
2. 检查是否存在可用 session
3. 如果缺失或失效，则提示用户登录
4. 登录成功后更新 `/.neolyst`
5. 创建 Supabase client
6. 返回 `{ client, session, user }`

推荐返回结构：

```ts
type AuthenticatedClient = {
  client: SupabaseClient
  session: Session
  user: User
}
```

设计原则：

- 对外业务能力不直接操作 session 文件
- 所有需要访问 Supabase 的逻辑都通过 `getAuthenticatedClient()` 获取 client
- skill 内其他脚本不直接创建原始 Supabase client

## 7. 第一版对外业务能力

第一版只暴露一个核心业务能力：

- `submit_report`

说明：

- `submit_report` 是一个完整业务动作，不再拆成多个对外动作
- 它内部已经包含新建 report、上传文件、保存内容、执行提交
- 第一版不对外暴露 `upload file`
- 第一版不对外暴露 `save draft`
- 第一版不支持“基于已有 draft 提交”

## 8. submit_report 与现有 Web 行为的对齐原则

第一版 `submit_report` 明确对齐当前已实现的 `Analyst Submit` 行为，而不是文档中的未来理想目标态。

原因：

- 与当前线上/当前仓库实现一致，落地成本最低
- 可以直接复用当前数据库、RLS 和提交校验口径
- 避免 skill 的行为与现有 Web 提交逻辑产生分叉

这意味着：

- 某些字段以当前代码实现为准
- 如果未来要把 skill 行为收敛到文档目标态，应通过第二阶段变更统一处理

## 9. submit_report 输入模型

### 9.1 输入来源

第一版默认 `submit_report` 接收：

- 一份结构化报告元数据
- 一组本地文件路径

这份输入建议由 `report_maker` 直接产出，减少中间转换。

### 9.2 建议输入结构

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

### 9.3 字段说明

- `title`：报告标题
- `report_type`：报告类型，必须来自有效模板类型
- `ticker`：公司类报告使用
- `rating`：`company` 必填
- `target_price`：`company` 必填
- `region_code`：`sector` / `sector_flash` / `common` 必填
- `sector_id`：`sector` / `sector_flash` 必填
- `report_language`：`en` 或 `zh`
- `contact_person_id`：第一版按当前实现视为可选
- `investment_thesis`：提交前必填
- `certificate_confirmed`：提交前必须为 `true`
- `analysts`：至少 1 个，最多 4 个，必须唯一
- `files.report_file`：报告主文件路径
- `files.pdf_file`：可选 PDF
- `files.model_file`：`company` 必填

## 10. 字段必填规则

### 10.1 所有 report type 通用要求

提交前必须满足：

- `title` 非空
- `report_type` 非空
- `report_language` 非空
- `investment_thesis` 非空
- `analysts` 至少 1 个
- `certificate_confirmed = true`
- `report_file` 已提供并上传成功

### 10.2 company

必须额外提供：

- `ticker`
- `rating`
- `target_price`
- `model_file`

### 10.3 company_flash

必须额外提供：

- `ticker`

### 10.4 sector

必须额外提供：

- `region_code`
- `sector_id`

### 10.5 sector_flash

必须额外提供：

- `region_code`
- `sector_id`

### 10.6 common

必须额外提供：

- `region_code`

## 11. 来源合法性校验

第一版 skill 需要对齐当前服务端的来源校验：

- `report_type` 必须是有效 active type
- `region_code` 必须来自有效 region
- `sector_id` 必须来自有效 sector
- `analysts[].analyst_id` 必须来自 active analyst

对于公司类报告，还必须满足 Coverage 关系：

- `ticker` 必须能匹配有效 Coverage
- Coverage 必须有 analyst 映射
- report 中提交的 analyst 列表必须与 Coverage analyst 至少有一个交集

## 12. 文件上传规则

### 12.1 skill 负责上传

第一版由 skill 自己负责上传文件，不依赖前端页面。

### 12.2 允许的文件类型

- 报告主文件：`.doc` / `.docx` / `.ppt` / `.pptx`
- PDF：`.pdf`
- Model：`.xls` / `.xlsx` / `.csv`

### 12.3 上传顺序

建议顺序：

1. 通过 `getAuthenticatedClient()` 拿到 client
2. 创建 report
3. 根据 report id 和版本号上传文件到 Storage
4. 将上传后的文件路径写入 report 内容保存
5. 执行 direct submit

### 12.4 第一版不处理的文件

第一版设计中，不将 `chief approval screenshot` 纳入 skill 的核心提交流程。

原因：

- 当前工作流主目标是“生成报告并提交”
- `chief approval screenshot` 不是主链路最小闭环必需项

## 13. submit_report 执行流程

第一版 `submit_report` 建议按以下顺序执行：

1. 调用 `getAuthenticatedClient()`
2. 读取/验证输入 payload
3. 校验基础字段
4. 校验 report type / region / sector / analyst 来源合法性
5. 创建 report 记录
6. 上传 report file
7. 如存在则上传 PDF
8. 若 `report_type = company`，上传 model file
9. 保存 report 内容与文件路径
10. 执行 direct submit
11. 返回 report id、状态、版本号等结果

## 14. 失败处理策略

第一版对齐现有 Web 的“先创建/保存，再提交”的内部思路。

即便对外只暴露 `submit_report`，内部也可以分两步：

1. 先建立 report 与最新内容
2. 再执行提交

如果提交阶段失败：

- 返回错误
- 保留已创建的 report / draft 状态

这样做的原因：

- 避免文件已上传但业务对象丢失
- 与当前 Web 的 direct submit 容错思路一致

## 15. 与当前实现的一个已知差异

文档目标态中，`Contact Person` 被列为提交必填项；
但当前代码实现并未在提交前强制要求 `contact_person_id`。

第一版 skill 设计按“当前已实现行为”收敛，因此：

- `contact_person_id` 第一版先按可选处理

后续如果需要与需求文档完全收敛，再单独调整。

## 16. Skill 内部模块建议

第一版可按以下最小结构组织：

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

职责建议：

- `auth.ts`：登录、刷新、session 读写
- `config.ts`：处理根目录 `/.neolyst`
- `client.ts`：导出 `getAuthenticatedClient()`
- `submit-report.ts`：实现完整提交流程
- `storage.ts`：上传文件、构造 Storage 路径
- `validators.ts`：输入校验、业务前置校验

## 17. 第一版建议结果结构

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

## 18. 第二阶段议题（暂不实现）

以下内容明确放入后续阶段，不在第一版落地：

- 代分析师执行
- `delegate mode`
- editor 角色重新引入
- report 归属 analyst 而非当前操作者
- 多账号切换
- 更多对外能力，如 `save_draft`、`list_reports`、`get_report_detail`
- skill 与 Web 的更深层交互整合

## 19. neoskills 落地结构

本节用于指导将本设计文档拷贝到 `neoskills` 项目后，如何组织第一版 `neolyst` skill 的落地目录与文件职责。

### 19.1 建议目录结构

```text
neolyst/
  SKILL.md
  scripts/
    auth.ts
    config.ts
    client.ts
    validators.ts
    storage.ts
    submit-report.ts
```

### 19.2 SKILL.md 的职责

`SKILL.md` 建议只做以下几件事：

- 说明 skill 名称为 `neolyst`
- 说明第一版只聚焦 `submit_report`
- 说明 skill 会在工作目录根下使用 `/.neolyst`
- 说明当 `/.neolyst` 缺失或 session 失效时，会提示输入 `email/password`
- 说明输入应对齐 `report_maker` 输出的结构化 payload
- 说明 skill 会自己上传文件，再创建并提交 report

`SKILL.md` 不建议承载过多实现细节，例如：

- Supabase client 创建细节
- 具体 JSON 字段逐一解释
- 复杂的异常分支

这些细节应放在 `scripts/*.ts` 中实现。

### 19.3 scripts/config.ts

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

### 19.4 scripts/auth.ts

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

- 第一版允许使用 `/.neolyst.auth.email/password`
- 第一版不做复杂的账户切换能力

### 19.5 scripts/client.ts

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

### 19.6 scripts/validators.ts

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

### 19.7 scripts/storage.ts

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

### 19.8 scripts/submit-report.ts

职责：

- 实现第一版 `submit_report` 全流程
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

### 19.9 submitReport 的建议入参与返回值

建议入参：

```ts
type SubmitReportPayload = {
  title: string
  report_type: string
  ticker?: string | null
  rating?: string | null
  target_price?: string | null
  region_code?: string | null
  sector_id?: string | null
  report_language: "en" | "zh"
  contact_person_id?: string | null
  investment_thesis?: string | null
  certificate_confirmed: boolean
  analysts: Array<{
    analyst_id: string
    role: number
    sort_order: number
  }>
  files: {
    report_file: string
    pdf_file?: string | null
    model_file?: string | null
  }
}
```

建议返回值：

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

### 19.10 建议开发顺序

在 `neoskills` 中落地时，建议开发顺序如下：

1. 先完成 `config.ts`
2. 再完成 `auth.ts`
3. 再完成 `client.ts`
4. 再完成 `validators.ts`
5. 再完成 `storage.ts`
6. 最后完成 `submit-report.ts`
7. 最后补 `SKILL.md`

这样做的原因：

- 先把认证和配置跑通
- 再补业务提交主链路
- 避免先写业务脚本再反复返工登录/配置层

## 20. 结论

`skills_neolyst` 第一版的设计方向是：

- 一个 skill：`neolyst`
- 一个核心业务能力：`submit_report`
- 一个内部公共入口：`getAuthenticatedClient()`
- 一个本地配置文件：工作目录根下 `/.neolyst`
- 一个统一技术栈入口：`@supabase/supabase-js`

第一版优先级不是做完整权限代理体系，而是先把
“`report_maker` 生成标准格式报告 -> `neolyst` skill 登录 Supabase -> 上传文件 -> 创建并提交 report”
这条链路稳定打通。
