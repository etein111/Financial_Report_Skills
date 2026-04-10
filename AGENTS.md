
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

## 业务逻辑落点原则

**所有业务逻辑必须在 Supabase 侧实现，Python skill 只做 I/O（文件上传、参数整理、调用接口）。**

具体规则：
- 路径生成规则、字段计算、一致性校验、状态流转 → 全部在 Supabase 函数/RPC 里实现，Python 不硬编码
- 直接读取（无逻辑）→ 直接查表，不需要 RPC
- 需要写入或有逻辑 → 必须走 RPC

**所有 schema 变更（包括函数、触发器、RPC）必须写入 `supabase/migrations/` 文件，不允许手动在 Studio 里操作。**



**写任何实现计划之前，必须先向用户提出不确定的问题，等待确认后再动笔。**

不清楚的事情包括但不限于：
- 命名规则（bucket 名、路径格式、文件名）
- 接口边界（哪些逻辑在 Supabase 侧实现，哪些在 skill 侧）
- 文件落地位置（本地路径、临时目录）
- 迭代范围边界（哪些留给后续迭代）

提问方式：圈出设计文档中已明确的内容，列出不确定项，一次性问完，等用户回答后再写计划。



**每次完成实现变更后，必须在同一次任务内检查并更新相关文档，不允许留到下次。**

### 触发条件（满足任一即需检查）

- 接口契约变化：函数签名、返回类型、错误类型
- 配置/文件结构变化：新增、重命名、移动文件
- 认证/会话机制变化
- 新增模块或移除模块
- 测试账号、环境地址变化

### 需要同步的文档

| 文档 | 何时更新 |
|------|---------|
| `docs/skills_neolyst_design.md` | 设计决策、架构、配置、接口契约有变 |
| 当前迭代的 `plans/*.md` | 步骤完成时打勾；迭代外的补丁写入 "Post-iter 补丁" 段 |
| `plans/2026-04-07-neolyst-skill-roadmap.md` | 迭代完成时标记状态 |

### 检查方式

完成一个任务后，问自己：**"这个改动有没有改变文档里已经写定的内容？"** 有则立刻更新，没有则跳过。不需要每次都把文档从头读一遍。


- 以场景为中心组织框架，不按技术分类
- 只写看了就能上手的内容，深度细节交给资料链接
- 一眼能看懂，太长没人看

## 迭代执行工作流

每次开始一个新迭代时，**必须按以下顺序执行**，每步都通过 superpowers skill 完成：

1. 读取 `plans/2026-04-07-neolyst-skill-roadmap.md` 了解当前进度
2. 读取上一迭代的计划文件（`plans/` 目录）
3. 向用户提出所有不确定的问题，等待确认后再动笔
4. **调用 `superpowers:writing-plans` skill 写本迭代计划**，保存到 `plans/` 目录
5. **调用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` skill 执行计划**
6. 完成后更新 roadmap 状态和相关文档

> **重要**：计划撰写和计划执行都必须通过 superpowers skill 完成，不允许自行用 Plan Mode 写计划或自行逐步实现。

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

## Skill 管理原则

- 日常开发操作（数据库管理、环境推送等）统一收进 `skills/dev_ops/`
- 相关的脚本和文档随 skill 归档，不在 `supabase/` 下散落
- 需要整理时记在 `docs/TODO.md`，不要当场顺手做

