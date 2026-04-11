# `skills/neolyst/SKILL.md` 调整要点

## 1. 为什么 `docs/skills_neolyst_integration.md` 的第 7 章应删除

第 7 章写的是 `validate_draft`、`submit_report`、校验失败后怎么处理。

这部分不属于 `report_maker` 的职责：

- `report_maker` 的职责止于 `save_draft_report`
- `validate_draft` 和 `submit_report` 由 `neolyst` 或上层流程调用
- 校验失败后的补字段、重保存、重校验，也不该写成 `report_maker` 的职责

所以这部分不该放在 `docs/skills_neolyst_integration.md` 里，应该删掉。

## 2. `skills/neolyst/SKILL.md` 需要改什么

### 2.1 去掉不存在的审批前置条件

当前 `SKILL.md` 里仍写着：

- `create_coverage` 只能在用户已确认“Coverage 已完成审批”后调用

这和当前实现不一致。现有 skill 没有 Coverage 审批能力，也没有审批接口或审批状态。

应改为：

- 删掉“已完成审批”这句
- 只保留 `create_coverage` 是显式创建接口
- 是否调用 `create_coverage` 由调用方决定

### 2.2 `resolve_coverage` 未命中后的表述要放松

当前 `SKILL.md` 写的是：

- 未命中：需进入 `create_coverage` 流程

这个表述过死。未命中时，skill 只负责返回明确错误；后续是调用 `create_coverage`，还是转人工去 Neolyst 中补建或修正，由调用方决定。

应改为：

- 未命中：抛出 `ValueError`，由调用方决定后续处理

### 2.3 `validate_draft` 要明确只负责报错

当前 `SKILL.md` 已经写到校验失败时会抛 `ValueError`，但边界还不够清楚。

应补一句：

- `validate_draft` 只负责校验并返回完整错误
- 不自动补字段
- 不自动重试
- 不自动保存 draft

建议把这句加在 `validate_draft` 小节里。

### 2.4 `submit_report` 要明确失败时只抛错

当前 `submit_report` 已经写到内部先调用 `validate_draft`。这里还应补一句：

- 校验失败时直接抛出异常
- 不自动补字段
- 不自动重试

### 2.5 “错误处理”章节要补一条总规则

当前“错误处理”章节列了各种异常，但没写清谁负责后续处理。

应补一句总规则：

- 本 skill 只负责返回明确错误
- 后续交互、补字段、重保存、重试，由调用方负责

## 3. 建议直接替换的表述

### 3.1 `resolve_coverage`

把：

```text
# 未命中：抛出 ValueError（需进入 create_coverage 流程）
```

改成：

```text
# 未命中：抛出 ValueError，由调用方决定后续处理
```

### 3.2 `create_coverage`

把：

```text
# 必须先经过 resolve_coverage 未命中，且用户已确认"该 Coverage 已完成审批"，才可调用
```

改成：

```text
# 显式创建接口；调用方在确认需要创建 coverage 时调用
```

### 3.3 `validate_draft`

把失败说明补成：

```text
# 失败：抛出 ValueError（消息以"；"分隔所有失败项）；调用方据此补字段、修正数据或重新保存后再重校验
```

并补一句：

```text
`validate_draft` 只负责校验并返回完整错误，不自动补字段、不自动重试、不自动保存 draft。
```

### 3.4 `submit_report`

把说明补成：

```text
# 内部先调用 validate_draft；校验失败时直接抛出异常，不自动补字段或重试
```

### 3.5 “错误处理”

在章节里补一句：

```text
本 skill 只负责返回明确错误，不负责后续交互、补字段、重保存或重试；这些动作由调用方负责。
```

## 4. 修改顺序

1. 先删掉所有“Coverage 已完成审批”的表述
2. 再改 `resolve_coverage` 未命中的说明
3. 然后补齐 `validate_draft` 和 `submit_report` 的失败处理边界
4. 最后统一“错误处理”章节和“业务约束（调用方须知）”章节的口径

## 5. 备注

后续真正修改 `skills/neolyst/SKILL.md` 时，按 [principles/SKILL.md](/mnt/c/_code/neoskills/principles/SKILL.md:19) 需要使用 `skill-creator`，不能手写。
