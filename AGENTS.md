
# AGENTS.md
AI 编程助手的统一指导文件。Claude Code 和 Codex 共享此配置。

## 文档索引

本文件只保留协作入口，不展开具体规范细则。

后续遇到代码实现、重构、代码评审等问题时，查阅 [docs/CODING_STANDARDS.md](./docs/CODING_STANDARDS.md)。

后续遇到 Skill 目录结构、测试目录组织等问题时，查阅 [docs/SKILL_STANDARD.md](./docs/SKILL_STANDARD.md)。

## 语言偏好

- 默认使用中文与用户沟通，思考过程也使用中文
- 产出的文档、说明、计划与总结默认使用中文
- 仅在用户明确要求时切换语言

## 沟通原则

向用户提问澄清需求或做决策时，避免只抛问题，必须同时给出：
- 推荐选项（默认）
- 关键考量/取舍
- 不确定时的默认决策

## 临时文件位置规则

- 不要在项目根目录下创建任何临时目录或文件。
- 临时文件只允许放在 `/tmp/`,`~/tmp/`

## 相关概念

`neoskills` 不是完整工作台，而是 AI 工作台中的业务能力集合。

### Neolyst 系统（现有平台）

- **技术栈**：Next.js App Router + React + TypeScript（前端），Supabase（后端）
- **角色**：`admin`（管理员）、`sa`（审批）、`analyst`（分析师）
- **核心实体**：Analyst（分析师）、Sector（行业）、Coverage（覆盖）、Template（模板）、Report（报告）
- **报告状态流转**：`draft → submitted → published/rejected`

## 技术栈与工具库

### Word 文档操作

本项目大量处理 Word 模板和报告，默认按以下规则选型：
- 创建、读取和精细修改 `.docx` 时，优先使用 `python-docx`
- 模板变量替换和批量渲染时，优先使用 `docxtpl`
- 纯文本分析或结构摸底时，优先使用 `docx2txt`
- 合并文档时，优先使用 `docxcompose`
处理注意事项：
- `python-docx` 的 `cell.text` 不包含嵌套表格内容, 涉及嵌套表格时，必须显式遍历 `cell.tables`.

