---
name: openspec-archive-change-docs
description: 归档指定 OpenSpec change，并把该 change 的 `proposal.md` 与 `design.md` 智能整合进主文档 `docs/REQUIREMENTS.md` 与 `docs/ARCHITECTURE.md`（去重/整合/重组/覆盖旧内容）。当用户输入 `/archive_change <change_name>` 或要求“归档并形成项目全貌文档”时使用。
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: neolyst
  version: "1.0"
---

# Archive Change + Consolidate Docs

目标：解决 `openspec archive` 只合并 `specs/` 但不会形成“项目全貌文档”的问题。该 skill 在归档 change 的同时，把 `proposal.md`（需求）与 `design.md`（架构/设计）沉淀到仓库主文档中，形成随仓库演进的统一全貌视图。

约束：
- **必须带参数**：`/archive_change <change_name>`。
- 默认使用 `openspec archive` 完成归档与 spec 合并；**不要手动 `mv`**。
- 合并主文档时遵循：**去重、整合、重组、更新覆盖**（非按时间追加）。

## 输入

- `<change_name>`：要归档并合并文档的 change 名称（例如 `auth-and-users-mvp`）。
- 可选语义开关（从对话理解，不要求 CLI 参数）：
  - `skip-specs`：该 change 仅为文档/工具变更，不需要合并 specs（等价于 `openspec archive --skip-specs`）。
  - `yes`：跳过确认（仅在用户明确说“直接执行”时使用）。

## 步骤

## 1. 校验 change 存在且可归档

1. 运行 `openspec list --json`，确认 `<change_name>` 存在。
2. 运行 `openspec validate <change_name> --type change`。
3. 若 validate 失败：先修复 change 产物（通常是某些 `specs/*/spec.md` 的 Requirement 缺少 `#### Scenario:`），修复后再继续。

## 2. 预览与确认（默认推荐继续）

输出预览，明确会修改哪些文件：

```text
## Archive Preview

Change:
- <change_name>

Will update:
- docs/REQUIREMENTS.md
- docs/ARCHITECTURE.md

Proceed? (yes/no)
```

推荐选项：`yes`（前提是 validate 已通过）。

## 3. 归档 change（并合并 specs）

默认执行：
- `openspec archive <change_name> -y`

如果用户明确要求不合并 specs：
- `openspec archive <change_name> -y --skip-specs`

注意：
- 除非用户明确要求，否则不要使用 `--no-validate`。

## 4. 定位归档目录并读取 proposal/design

1. 在 `openspec/changes/archive/` 下找到以 `-<change_name>` 结尾、且日期最新的目录：
   - `openspec/changes/archive/YYYY-MM-DD-<change_name>/`
2. 尝试读取（不存在则静默跳过）：
   - `proposal.md`
   - `design.md`
3. 记录 `archive_path` 与 `archived_date`（从目录名提取 `YYYY-MM-DD`）。

## 5. 智能整合到主文档（核心）

目标文件（不存在则创建）：
- `docs/REQUIREMENTS.md`
- `docs/ARCHITECTURE.md`

### 5.1 文档结构（稳定、非按时间）

`docs/REQUIREMENTS.md` 建议结构：
1. Purpose & Scope
2. Roles & Permissions (RBAC)
3. Authentication & Sessions
4. Admin Capabilities (User management, etc.)
5. Navigation Contract (Desktop-as-Launcher)
6. Data Access Baseline (RLS)
7. Operational & Security Constraints
8. Sources (traceability)

`docs/ARCHITECTURE.md` 建议结构：
1. System Overview
2. Tech Stack & Boundaries
3. App Structure & Dependency Rules（引用 `docs/LOGIC.md`）
4. Auth/Session Architecture
5. Request Boundary Gate (`proxy.ts`) and Route Protection
6. Supabase Client Layering (browser/server/admin)
7. Data Layer (PostgREST + RLS, time semantics)
8. Operational/Security Notes
9. Sources (traceability)

### 5.2 合并规则（必须遵守）

- 去重：
  - 规范化空白后，完全重复的段落只保留一份。
  - 已在 `docs/DECISIONS.md`/`docs/LOGIC.md` 固化的长期约束，**优先引用**而不是大段重复粘贴。
- 整合：
  - 把新 change 的内容放进最相关的主题段落（例如 RBAC、Session、RLS），不要按 change 追加“## <change>”章节作为主干。
- 重组：
  - 若 `proposal.md`/`design.md` 的叙述顺序不理想，允许改写为更清晰的“当前系统事实”，但必须保持语义一致。
- 更新覆盖：
  - 如果新 change 明确修改/覆盖旧约束，以新 change 为准。
  - 在被覆盖的段落末尾追加一行标记：
    - `Last updated by <change_name> on <YYYY-MM-DD>.`
- 可追溯：
  - 每次归档后，都要在两份主文档的 `Sources` 段落更新一条记录：
    - `- <change_name>: <archive_path>`

### 5.3 实施策略（推荐做法）

1. 先阅读当前 `docs/REQUIREMENTS.md`/`docs/ARCHITECTURE.md`（若不存在则创建骨架）。
2. 从 `<archive_path>/proposal.md` 提取“需求事实”，映射到 `REQUIREMENTS` 的各段落。
3. 从 `<archive_path>/design.md` 提取“架构事实”，映射到 `ARCHITECTURE` 的各段落。
4. 对每个段落执行：合并同义项、删重复、补充缺口、标注更新来源。
5. 最后更新 `Sources`。

## 6. 输出总结

```text
## Archive + Consolidation Complete

Archived:
- <change_name> -> <archive_path>

Updated:
- docs/REQUIREMENTS.md
- docs/ARCHITECTURE.md
```

