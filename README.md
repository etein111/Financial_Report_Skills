# neoskills

`neoskills` 是 AI 工作台中的 skills 能力仓库，用于沉淀和组织可被工作台调用的业务能力。

## 当前状态

✅ **report_maker** - 分析师报告自动化处理（已完成）
- 两阶段工作流：抽取确认 → 渲染输出
- 支持 7 种报告类型（company, sector, macro, strategy, quantitative, bond, flash）
- 84 个测试全部通过
- 完整文档和示例脚本

⏳ **template_maker** - 模板制作与维护（规划中）

## 说明

- **[PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md)** - 项目目录组织规范
- `platform.md` 和 `workbench-req.md` 是背景参考文档
- **[skills-report.md](./docs/skills-report.md)** - 分析师报告系统的完整需求和设计文档
- **[report_maker 用户指南](./docs/report_maker_user_guide.md)** - 如何使用 report_maker
- **[report_maker 部署文档](./docs/report_maker_deployment.md)** - 部署和配置说明

## 开发指南

### 核心文档

- **[AGENTS.md](./AGENTS.md)** - AI 编程助手的核心指导文件（必读）
- **[CODING_STANDARDS.md](./docs/CODING_STANDARDS.md)** - 代码规范和设计原则
- **[CODE_REVIEW_CHECKLIST.md](./docs/CODE_REVIEW_CHECKLIST.md)** - 代码审查检查清单

### 快速开始

1. 阅读 [AGENTS.md](./AGENTS.md) 了解项目编程原则
2. 参考 [CODING_STANDARDS.md](./docs/CODING_STANDARDS.md) 编写代码
3. 使用 [CODE_REVIEW_CHECKLIST.md](./docs/CODE_REVIEW_CHECKLIST.md) 审查代码

### 核心原则

- **函数式编程优先**：纯函数、I/O 分离、批量操作
- **模块高内聚低耦合**：单一职责、按数据类型分
- **扁平化数据结构**：减少嵌套、用 type 区分
- **删除冗余代码**：避免无意义包装、合并重复逻辑
