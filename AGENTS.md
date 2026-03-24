@docs/README.md

# AGENTS.md

AI 编程助手的统一指导文件。Claude Code 和 Codex 共享此配置。

## 文档索引

## 语言偏好

- 默认使用中文与用户沟通，思考过程也使用中文
- 产出的文档、说明、计划与总结默认使用中文
- 仅在用户明确要求时切换语言

## 沟通原则

向用户提问澄清需求或做决策时，避免只抛问题，必须同时给出：
- 推荐选项（默认）
- 关键考量/取舍
- 不确定时的默认决策

## 编码原则

### Python 项目

- **使用 uv 作为包管理工具**：优先使用 `uv` 而非 `pip` 或 `poetry` 进行依赖管理和项目初始化
- 安装依赖：`uv pip install <package>` 或 `uv sync`
- 创建项目：`uv init` 或 `uv venv`

### Skills 开发

- **严格遵循 Anthropic Agent Skills Open Standard**：所有 skill 必须符合官方标准规范
  - 官方文档：[agentskills.io](https://agentskills.io/home)
  - 官方仓库：[github.com/anthropics/skills](https://github.com/anthropics/skills)
  - 完整指南：[The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
  - **必需**：SKILL.md 必须包含 YAML frontmatter（name 和 description 字段）
  - **标准结构**：代码文件放在 `scripts/` 子目录，SKILL.md 在根目录

- **使用 skill-creator skill 开发新技能**：
  - 在创建或修改 skill 之前，**必须先调用** skill-creator skill
  - 使用 `init_skill.py` 脚本初始化正确的目录结构
  - 使用 `package_skill.py` 脚本验证和打包 skill
  - 参考 skill-creator 的设计模式和最佳实践

---
