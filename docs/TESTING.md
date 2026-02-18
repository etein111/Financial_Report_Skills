# Testing & Verification

本文件定义测试策略、执行方式与通过标准。
不承载业务需求定义（见 `REQUIREMENTS.md`）与代码分层规则（见 `LOGIC.md`）。

## 1. 测试目标

- 保证关键业务流程可重复验证。
- 保证权限与 RLS 不被回归破坏。
- 保证测试执行不会污染交付目录与线上数据。

## 2. 测试分层

- 单元测试：纯函数/Schema/工具函数。
- 集成测试：repo/action 与数据访问行为。
- E2E：用户流程、权限矩阵、关键异常路径。
- 数据库验证：RLS 与迁移结果一致性。

## 3. 目录与临时文件规范

目录约束：
- 测试代码仅放 `tests/`。
- 开发/运维脚本放 `scripts/`。
- 临时输出仅放 `temp/`。

临时文件规则：
- 输出命名：`<tool>-<yyyyMMdd-HHmmss>.<ext>`。
- 禁止在源码目录写入 `*.out/*.log/*.tmp`。

## 4. 执行命令（基线）

E2E：
```bash
cd tests
pnpm exec playwright test
```

数据库验收脚本：
```bash
cd tests
node scripts/verify/verify-db-admin-and-rls.mjs
```

## 5. 覆盖要求

每个 change 至少覆盖：
- 正常路径（Happy Path）
- 权限拒绝路径（403 / RLS 拒绝）
- 关键校验失败路径（必填、唯一性、状态机非法流转）

对于高风险能力（权限、审批、状态机、文件路径）：
- 必须有 E2E 用例
- 必须有角色维度断言

Coverage 管理回归至少包含：
- 创建/编辑时 `sector_id` 非活跃列表值必须失败。
- 创建/编辑时 `analyst_id` 非活跃列表值必须失败。
- 创建/编辑时重复选择同一 analyst 必须失败。

## 6. 通过标准（Gate）

- 必跑测试集全部通过。
- 新增能力必须有对应测试，不允许“仅手测”。
- 发现阻断缺陷必须先修复再合并。

## 7. 数据副作用控制

- 能只读验证的场景，禁止写入。
- 必须写入时，优先事务回滚或 `__test__` 前缀隔离并清理。
- 不在 migration/seed 中放测试专用数据。
