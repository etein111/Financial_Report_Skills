# 自动加载的规范

@principles/RULES.md
@principles/CODING.md
@principles/KARPATHY.md

# 按需读取的规范

- 业务逻辑边界、RPC、Supabase 职责划分 → [ARCHITECTURE.md](./principles/ARCHITECTURE.md)
- Supabase 迁移、schema → [SUPABASE.md](./principles/SUPABASE.md)
- 问题清单、差异清单、风险清单格式 → [DIALOG.md](./principles/DIALOG.md)
- 编码实现、代码审查、重构时的行为准则（避免过度设计、精准修改、先思考再动手） → [KARPATHY.md](./principles/KARPATHY.md)

# 交互规范

## 语言与沟通

- 默认使用中文与用户沟通；产出的文档、说明、计划与总结默认使用中文。
- 仅在用户明确要求时切换语言。
- 语言风格必须简洁明确、主动具体、客观克制；避免浮夸修饰、空洞大词、模糊表述和情绪化表达。
- 文档结构遵循正交性（章节独立，互不影响）和 MECE（分类不重叠、不遗漏）。
- 向用户提问时，不能只抛问题；必须同时给出推荐方案、关键取舍，以及用户未明确回复时的默认处理方式。

# 工作原则

- 做任何工作前，必须先阅读匹配的本地文档。
- 开发流程优先使用 superpowers skill，并按 superpowers 的流程指导执行。
- 写任何实现计划之前，特别是工作范围不清时，必须先向用户提出不确定的问题，等待确认后再动笔。
- 当用户确认内容与现有文档不一致时，必须及时补充相关文档；补充内容先追加在文档末尾，后续再统一整理。
- 新建或修改文档时，优先使用 `doc-coauthoring` skill 进行协作写作。
- 写作面向人类的文案（文档、提交信息、PR 描述、错误消息）时，应用 `elements-of-style` skill。
- 创建或修改 SKILL.md 时，必须通过 Skill 工具调用 skill-creator（`document-skills:skill-creator`），遵循其 draft → test → review → improve 循环
- Python 项目的依赖管理、环境同步和执行流程优先使用 `uv`

# 目录约束

- 临时文件只允许放在 `/tmp/` 或 `~/tmp/`。
- 不要在项目根目录下创建任何临时目录或文件。
