# neolyst Skill 开发路线图

## 工作流（每次迭代必须遵守）

1. 调用 `writing-plans` skill 写本迭代计划，保存到 `plans/` 目录
2. 用 `subagent-driven-development` 或 `executing-plans` skill 执行
3. 完成后在本文件更新状态和计划文件链接
4. 后续迭代开始前先阅读前面迭代的计划文件

## 迭代状态

| 迭代 | 范围 | 状态 | 计划文件 |
|------|------|------|----------|
| Iter 1 | connection + analyst | 已完成 | [2026-04-09-neolyst-iter1.md](2026-04-09-neolyst-iter1.md) |
| Iter 2 | storage + template | 已完成 | [2026-04-09-neolyst-iter2.md](2026-04-09-neolyst-iter2.md) |
| Iter 3 | coverage | 已完成 | [2026-04-09-neolyst-iter3.md](2026-04-09-neolyst-iter3.md) |
| Iter 4 | draft_report | 已完成 | [2026-04-09-neolyst-iter4.md](2026-04-09-neolyst-iter4.md) |
| Iter 5 | validators + submit | 未开始 | — |
| Iter 6 | 收尾 | 未开始 | — |

## 说明

- schema 真相源：`supabase/migrations/`
- 复杂读写默认走 Supabase 侧 RPC / 稳定接口
- 原则上尽量不用外键，跨表一致性由 RPC 负责
