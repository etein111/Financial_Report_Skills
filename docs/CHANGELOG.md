# Changelog

记录项目级关键变更（按时间倒序）。

## 2026-02-17

### OpenSpec 归档触发流程调整
- 新增 `docs/OPENSPEC_ARCHIVE_BACKFILL.md`，统一归档并回填 docs 的触发语句、执行步骤与输出要求。
- `docs/README.md` 重整为“启动全量加载清单”，将 `README` 与 `OPENSPEC_ARCHIVE_BACKFILL` 一并纳入启动必读。
- `docs/README.md` 去除回填映射重复内容，改为只保留唯一入口引用（以 `OPENSPEC_ARCHIVE_BACKFILL` 为准）。
- 移除自定义 skill：`.codex/skills/openspec-archive-change-docs`。

### 文档治理重构
- 新增 `docs/DATA_MODEL.md` 作为逻辑数据模型唯一入口。
- 新增 `docs/CHANGELOG.md` 作为项目变更摘要入口。
- 重写 `docs/README.md`：加入启动必读协议、文档边界、冲突优先级、OpenSpec 回填映射。
- 重写 `docs/REQUIREMENTS.md`：按“已上线 + 已确认待开发”统一业务需求口径。
- 重写 `docs/ARCHITECTURE.md`：收敛为系统级架构与数据库规范，不再承载表级细节。
- 重写 `docs/DECISIONS.md`：整理为 ADR 风格长期决策清单。
- 重写 `docs/TESTING.md`：明确分层测试、覆盖要求与通过门槛。
- 合并视觉规范到 `docs/UI.md`（并入原前端视觉一致性内容）。

### OpenSpec 进展（摘要）
- `coverage-sector-template-management`：proposal/design/specs/tasks 已完成。
- `report-management-and-approval`：proposal/design/specs/tasks 已完成，文档口径已统一到 owner 模型与状态历史方案。
- 归档完成：`region-and-analyst-management`。

## 2026-02-15 ~ 2026-02-17

### 基线能力建设
- 完成认证与用户管理 MVP（登录、邀请、角色、禁用/启用、改密、删除）。
- 完成 Region 与 Analyst Info 管理基线。
- 建立 `region` / `analyst` RLS 基线策略。
