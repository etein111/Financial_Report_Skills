---
name: "Archive Change"
description: 归档指定 OpenSpec change，并把 proposal/design 智能整合进 docs/REQUIREMENTS.md 与 docs/ARCHITECTURE.md
category: Workflow
tags: [workflow, archive, docs, openspec]
---

归档指定 change，并把该 change 的 `proposal.md`（需求）与 `design.md`（架构/设计）整合进仓库主文档，形成“项目全貌文档”，而不是仅合并 specs delta。

**输入**：`/archive_change <change_name>`（必须提供 change 名称）。可选：`--skip-specs`（仅文档/工具变更，不合并 specs）。

## Steps

1. 运行 `openspec list --json`，确认 `<change_name>` 存在。
2. 运行 `openspec validate <change_name> --type change`。若失败，先修复（常见原因：某些 Requirement 缺少 `#### Scenario:`）。
3. 预览并确认会更新：
   - `docs/REQUIREMENTS.md`
   - `docs/ARCHITECTURE.md`
4. 归档：
   - 默认：`openspec archive <change_name> -y`
   - 若指定 `--skip-specs`：`openspec archive <change_name> -y --skip-specs`
5. 在 `openspec/changes/archive/` 找到最新的 `YYYY-MM-DD-<change_name>/`，读取其中的 `proposal.md` 与 `design.md`（缺失则跳过）。
6. 智能合并到主文档（去重/整合/重组/更新覆盖）：
   - 不按时间追加“## <change>”作为主干
   - 把内容按主题整合进稳定结构
   - 冲突以新 change 为准，并标记：`Last updated by <change_name> on <YYYY-MM-DD>.`
   - 在两份主文档追加 Sources 记录：`- <change_name>: openspec/changes/archive/YYYY-MM-DD-<change_name>`
7. 输出总结：归档路径与更新的主文档列表。

