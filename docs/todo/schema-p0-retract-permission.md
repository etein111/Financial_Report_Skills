# P0 Schema 调整：收紧 submitted 权限 + 增加撤回路径

> 调整日期：2026-04-12
> 优先级说明：权限缺陷导致 analyst 可在 submitted 状态下修改报告，与业务语义矛盾，需优先修复

---

## 设计决策

- `submitted` 语义上是"已提交审阅"，报告应被冻结，analyst 不可修改
- 当前 RLS 允许 analyst 在 submitted 状态下 UPDATE report 和上传/修改文件，存在逻辑矛盾
- 增加 submitted→draft 撤回路径，analyst 可主动撤回已提交的报告重新编辑
- 新增 `retract_report` RPC 封装撤回操作

## 状态机变更

原状态机：
```
draft → submitted → published
                    └→ rejected → draft
```

新状态机：
```
draft ──submit──→ submitted ──publish──→ published
  ↑                  │
  │    retract ──────┘
  │                  └──reject──→ rejected
  │                                  │
  └────── retract ───────────────────┘
```

新增合法路径：`submitted → draft`

## `report_status_is_valid` 函数变更

新增条件：`(from_status = 'submitted' and to_status = 'draft')`

## RLS 权限修正

当前问题：analyst 在 `submitted` 状态下仍可 UPDATE report、INSERT report_version、上传/修改 Storage 文件，与"已提交审阅应冻结"的语义矛盾。

| 对象 | 现状（analyst） | 变更后（analyst） |
|------|-----------------|-------------------|
| `report` UPDATE | `status in ('draft','submitted')` 且 `owner_user_id = auth.uid()` | `status = 'draft'` 且 `owner_user_id = auth.uid()` |
| `report_version` INSERT | 同上，跟随 report 的 draft/submitted | `status = 'draft'` 且 `owner_user_id = auth.uid()` |
| `reports` bucket INSERT/UPDATE | analyst 自己的 draft/submitted 报告 | analyst 自己的 draft 报告 |

## 新增 RPC

| 函数 | 签名 | 说明 |
|------|------|------|
| `retract_report` | `retract_report(p_report_id uuid) returns table(report_id uuid, version_no integer, status text)` | analyst 将 submitted/rejected 报告撤回为 draft |

`retract_report` 权限：仅 analyst 且 `owner_user_id = auth.uid()` 可调用。

## `report_status_log` RLS 变更

| 角色 | 现有 | 变更后 |
|------|------|--------|
| analyst | 仅 draft→submitted | 增加 submitted→draft、rejected→draft |

## 完整受影响清单

### 新增

- `retract_report` RPC
- `submitted → draft` 状态路径

### 修改

- `report_status_is_valid` 函数：新增 submitted→draft 路径
- `report` UPDATE RLS：analyst 可操作状态从 `draft/submitted` 收窄为 `draft`
- `report_version` INSERT RLS：analyst 可操作状态从 `draft/submitted` 收窄为 `draft`
- `reports` bucket INSERT/UPDATE RLS：analyst 可操作状态从 `draft/submitted` 收窄为 `draft`
- `report_status_log` INSERT RLS：analyst 增加 submitted→draft、rejected→draft 流转
