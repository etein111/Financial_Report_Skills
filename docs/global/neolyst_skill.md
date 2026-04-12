# neolyst Skill 全局规则

整体长期规则与跨接口共享规则。实现细节见 `skills/neolyst/` 目录下的 README、代码注释和 references。

### 定位

neolyst 是 neoskills 中面向 Neolyst 的数据库操作 skill。

### 边界

report_maker 负责生成报告并组装输入，neolyst 负责执行查询、校验、上传、写入和提交。对上游暴露稳定的业务接口，不暴露底层数据库操作集合。neolyst 不负责：与用户对话补字段、替上游做业务决策、对上游暴露零散的底层数据库动作。

### 契约主权

save_draft_report 的输入由 neolyst 定义并维护，report_maker 依赖该契约，而不是反过来。

### 架构原则

业务一致性、状态流转、关系维护、主表/版本表同步的逻辑，均优先在 Supabase 侧实现为稳定接口。复杂读写（涉及路径规则、多表维护、跨表判断、校验+写入原子操作）默认走 RPC，不在 skill 侧拼接底层表操作。skill 负责认证、文件上传、参数整理和调用 Supabase 接口。不用外键，跨表一致性由 RPC 负责。

### 身份与权限

使用自身维护的 Neolyst 账号操作，所有操作以实际执行者身份为准。审计遵循"谁保存/提交，系统就记谁"；分析师身份仅用于报告署名，不影响审计记录。不做代理执行。系统按 admin、sa、analyst 三级角色控制访问权限，skill 设计必须兼容该模型。

### 错误语义

所有接口失败时直接抛出具体错误，不做静默吞错。错误信息必须足够明确，让上游 LLM 或人工据此补字段、重新确认或中止流程。

### 模板语义

模板以 report_type + language 定位。数据库层只有 report_template.id 主键和 (report_type, language) 普通索引，无唯一约束；同一组合出现重复记录视为数据异常。report_template.report_type 即报告类型本身，不引入 template_type。

### draft 契约

draft 输入采用全打平结构，业务字段和本地文件路径都位于顶层。不携带执行上下文字段（workspace_root、trace_id、server_url_override、dry_run）。report_language 由 report_maker 自动识别并向用户确认后写入 draft。

### 数据准源

文件路径的唯一准源是 report_version 表和 report_template 表的持久化字段，不是调用方传入的本地路径，不由 report_type 公式推导。snapshot_json 如保留文件字段，只作为版本快照，不作为校验和提交的判定来源。
