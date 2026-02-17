# Docs

项目文档统一入口（给人和 coding agent 共用）。
目标：启动即获得完整上下文，避免遗漏与规则漂移。

## 1. 启动加载协议（强制）

每次启动 coding agent 处理本仓库任务时，必须一次性全量读取以下文档（不跳读）：
1. `docs/README.md`
2. `docs/REQUIREMENTS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DATA_MODEL.md`
5. `docs/LOGIC.md`
6. `docs/UI.md`
7. `docs/TESTING.md`
8. `docs/DECISIONS.md`
9. `docs/CHANGELOG.md`
10. `docs/OPENSPEC_ARCHIVE_BACKFILL.md`

执行要求：
- 启动阶段不得“按需只读部分文档”。
- 完成加载后应先给出“已加载文档清单”再进入实现。

## 2. 文档索引（单一职责）

| 文档 | 定位 | 主要回答的问题 | 是否可直接改 |
|------|------|----------------|-------------|
| `docs/README.md` | 文档入口与加载协议 | 启动时必须加载哪些文档、冲突怎么判定 | 是（流程调整） |
| `docs/REQUIREMENTS.md` | 业务需求总览（WHAT） | 系统要做什么、角色能做什么、验收口径是什么 | 是（需求变更） |
| `docs/ARCHITECTURE.md` | 系统架构与技术边界（HOW-系统） | 系统怎么分层、边界如何划分、数据库规范是什么 | 是（架构变更） |
| `docs/DATA_MODEL.md` | 逻辑数据模型（表/约束/RLS） | 有哪些数据实体、表结构口径、权限矩阵是什么 | 是（数据模型变更） |
| `docs/LOGIC.md` | Web 代码实现规范（HOW-代码） | 代码放哪里、依赖怎么走、触库规则是什么 | 是（工程规范变更） |
| `docs/UI.md` | UI 组件与视觉一致性规范 | 页面/组件应该长什么样、如何避免视觉漂移 | 是（设计系统变更） |
| `docs/TESTING.md` | 测试与验收规范 | 怎么测、覆盖什么、通过标准是什么 | 是（测试策略变更） |
| `docs/DECISIONS.md` | 长期决策（ADR） | 哪些约束长期固定、为什么固定 | 是（新增/调整 ADR） |
| `docs/CHANGELOG.md` | 变更日志（按时间） | 最近改了什么、影响范围是什么 | 是（每次关键变更后追加） |
| `docs/OPENSPEC_ARCHIVE_BACKFILL.md` | OpenSpec 归档与回填流程 | 如何触发归档并把 change 结论回填到 docs | 是（流程调整） |

## 3. 冲突处理优先级

流程约定冲突：
1. `docs/README.md`
2. `docs/OPENSPEC_ARCHIVE_BACKFILL.md`

业务与技术口径冲突：
1. `docs/DECISIONS.md`（长期决策优先）
2. `docs/ARCHITECTURE.md` 与 `docs/LOGIC.md`（系统/实现边界）
3. `docs/DATA_MODEL.md`（数据口径）
4. `docs/REQUIREMENTS.md`（业务需求）
5. `docs/UI.md` 与 `docs/TESTING.md`（界面/测试）
6. `docs/CHANGELOG.md`（记录事实，不定义规则）

## 4. 文档边界规则（避免重叠）

- 一条规则只允许一个“主文档”完整定义。
- 非主文档只允许一句摘要或引用，不复制完整段落或矩阵。
- 术语统一：
  - “需求”只在 `docs/REQUIREMENTS.md` 定义
  - “架构/分层”只在 `docs/ARCHITECTURE.md` 与 `docs/LOGIC.md` 定义
  - “表结构/RLS 矩阵”只在 `docs/DATA_MODEL.md` 定义

## 5. OpenSpec 回填映射

回填映射、触发方式与完整步骤以以下文档为唯一来源：
- `docs/OPENSPEC_ARCHIVE_BACKFILL.md`

推荐触发语句：
- `归档并回填 <change_name>`
- `执行 OpenSpec 归档并同步 docs: <change_name>`
