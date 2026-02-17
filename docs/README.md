# Docs

项目文档唯一入口（给人和 coding agent 共用）。
目标：在开始开发前，快速、完整、无冲突地获得上下文，减少返工。

## 1. 启动必读协议（强制）

每次启动 coding agent 处理本仓库任务时，默认执行：
- 先读取本文件（`docs/README.md`）
- 再按下方顺序读取全部核心文档（全量读取，不跳读）

推荐读取顺序：
1. `docs/REQUIREMENTS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DATA_MODEL.md`
4. `docs/LOGIC.md`
5. `docs/UI.md`
6. `docs/TESTING.md`
7. `docs/DECISIONS.md`
8. `docs/CHANGELOG.md`

## 2. 核心文档索引（单一职责）

| 文档 | 定位 | 主要回答的问题 | 是否可直接改 |
|------|------|----------------|-------------|
| `docs/REQUIREMENTS.md` | 业务需求总览（WHAT） | 系统要做什么、角色能做什么、验收口径是什么 | 是（需求变更） |
| `docs/ARCHITECTURE.md` | 系统架构与技术边界（HOW-系统） | 系统怎么分层、边界如何划分、数据库规范是什么 | 是（架构变更） |
| `docs/DATA_MODEL.md` | 逻辑数据模型（表/约束/RLS） | 有哪些数据实体、表结构口径、权限矩阵是什么 | 是（数据模型变更） |
| `docs/LOGIC.md` | Web 代码实现规范（HOW-代码） | 代码放哪里、依赖怎么走、触库规则是什么 | 是（工程规范变更） |
| `docs/UI.md` | UI 组件与视觉一致性规范 | 页面/组件应该长什么样、如何避免视觉漂移 | 是（设计系统变更） |
| `docs/TESTING.md` | 测试与验收规范 | 怎么测、覆盖什么、通过标准是什么 | 是（测试策略变更） |
| `docs/DECISIONS.md` | 长期决策（ADR） | 哪些约束长期固定、为什么固定 | 是（新增/调整 ADR） |
| `docs/CHANGELOG.md` | 变更日志（按时间） | 最近改了什么、影响范围是什么 | 是（每次关键变更后追加） |

## 3. 冲突处理优先级

当不同文档出现冲突时，按以下优先级处理：
1. `docs/DECISIONS.md`（长期决策优先）
2. `docs/ARCHITECTURE.md` 与 `docs/LOGIC.md`（系统/实现边界）
3. `docs/DATA_MODEL.md`（数据口径）
4. `docs/REQUIREMENTS.md`（业务需求）
5. `docs/UI.md` 与 `docs/TESTING.md`（界面/测试）
6. `docs/CHANGELOG.md`（记录事实，不定义规则）

## 4. 文档边界规则（避免重叠）

- 一条规则只允许一个“主文档”完整定义。
- 非主文档只允许一句摘要或引用，不复制完整段落/矩阵。
- 术语统一：
  - “需求”只在 `REQUIREMENTS.md` 定义
  - “架构/分层”只在 `ARCHITECTURE.md` 与 `LOGIC.md` 定义
  - “表结构/RLS矩阵”只在 `DATA_MODEL.md` 定义

## 5. OpenSpec 回填映射

- `proposal.md` 回填优先：`REQUIREMENTS.md`、`DATA_MODEL.md`
- `design.md` 回填优先：`ARCHITECTURE.md`、`LOGIC.md`、`UI.md`、`TESTING.md`
- 具有长期约束的结论回填：`DECISIONS.md`
- 每次关键完成后追加：`CHANGELOG.md`
