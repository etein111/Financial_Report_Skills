# neoskills

`neoskills` 是 AI 工作台中的 skills 能力仓库，用于沉淀和组织可被工作台调用的业务能力。

当前项目仍处于需求和设计整理阶段。第一期先用 `opencode` 作为临时工作台，后续再考虑自研工作台 `neospace`。

## 说明

- **[PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md)** - 项目目录组织规范
- `platform.md` 和 `workbench-req.md` 是背景参考文档
- `skills-report.md` 是当前项目的核心文档

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
