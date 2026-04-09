# neolyst Skill 开发路线图

## 范围与状态

| 范围 | 状态 | 说明 |
|------|------|------|
| 设计文档与 schema 对齐 | 已完成 | `docs/skills_neolyst_design.md` 已按当前 `supabase/migrations/` 同步 |
| connection + analyst | 进行中 | 已有 `connection.py` 与连接测试；`analyst.py` 及对应测试未完成 |
| storage + template | 未完成 | 需要补文件上传下载与模板相关 RPC |
| coverage | 未完成 | 需要补 `resolve_coverage` / `create_coverage` 及对应 RPC |
| draft_report | 未完成 | 需要补 `save_draft_report`，并在 Supabase 端统一维护 `report` / `report_version` / `report_analyst` |
| validators + submit | 未完成 | 需要补提交前校验 RPC 与提交 RPC |
| 收尾 | 未完成 | 需要补全测试、更新 `skills/neolyst/SKILL.md`、完成联调验证 |

## 说明

- schema 真相源：`supabase/migrations/`
- 复杂读写默认走 Supabase 侧 RPC / 稳定接口
- 原则上尽量不用外键，跨表一致性由 RPC 负责
