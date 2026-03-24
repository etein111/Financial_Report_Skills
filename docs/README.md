# Docs

此目录存放 `neoskills` 的需求、定位和设计文档。当前项目仍处于方案梳理阶段，文档会先于代码逐步完善。

## 阅读顺序

1. [platform.md](/mnt/c/_code/neoskills/docs/platform.md)：整体平台参考文档，描述完整业务平台的目标、角色、架构和阶段规划。
2. [workbench-req.md](/mnt/c/_code/neoskills/docs/workbench-req.md)：AI 工作台需求参考文档，用于说明工作台要承接的能力范围。
3. [skills-report.md](/mnt/c/_code/neoskills/docs/skills-report.md)：本项目当前的核心文档，聚焦 report 类 skills 的需求与设计。

## 文档分层

- 参考背景层：`platform.md` 和 `workbench-req.md`，用于帮助理解项目背景，不是本项目本身的主设计文档。
- 项目设计层：`skills-report.md`，用于沉淀 `neoskills` 内具体 skills 的需求与设计。

## 当前理解

- `neoskills` 不是完整工作台，而是工作台中的业务能力集合。
- 第一期开箱即用的工作台由 `opencode` 临时承担。
- 第二期会考虑建设更适配业务的自研工作台 `neospace`。

因此，阅读这些文档时可以按“平台背景 -> 工作台需求 -> 项目 skills 设计”这个层级来理解项目。
