# Neolyst Iter 9: 文档与实现同步

**Goal:** 审核并修正 neolyst skill 的接口文档（interfaces.md、SKILL.md）和设计文档（design.md、integration.md），消除文档与实际代码之间的差异。

**背景：** Iter 8 将 `validate_draft` 和 `submit_report` 收口为仅按 `report_id` 操作后，接口签名和内部行为发生变更。部分文档未同步更新，导致描述与实现不一致。

---

## 变更清单

### 接口文档修正

| 文件 | 变更 | 说明 |
|------|------|------|
| `skills/neolyst/references/interfaces.md` | 修正 | 补全遗漏参数（`dest_dir`、`created_at`/`updated_at`、`sector_id`/`region_code`）；标注可选参数默认值；修正文件名描述；`validate_draft` 校验范围拆为列表 |
| `skills/neolyst/SKILL.md` | 同步 | 速查表中 `resolve_template` 补 `dest_dir`，`upsert_template` 标注 `schema_local_path=None` |

### 设计文档修正

| 文件 | 变更 | 说明 |
|------|------|------|
| `docs/skills_neolyst_design.md` | 直接回写 | `validate_draft`/`submit_report` 签名改为仅 `report_id`；`submit_report` 内部行为改为直接调 RPC；模块依赖去掉 validators；Storage 路径生成归属修正；`resolve_template` 补 `dest_dir` |
| `docs/skills_neolyst_integration.md` | 直接回写 | `upsert_template` 的 `schema_local_path` 标注可选；`resolve_template` 补 `dest_dir` 参数说明 |

### 清理

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/glm/`、`docs/codex/`、`docs/kimi/` | 删除 | 平台特定文档副本，已过时且不再维护 |

---

## 状态

- [x] interfaces.md 修正并提交
- [x] SKILL.md 同步并提交
- [x] glm/codex/kimi 目录删除并提交
- [x] design.md 回写
- [x] integration.md 回写
- [x] iter plan 创建并提交
