# P0 Schema 调整：SQL 错误消息统一为中文

> 调整日期：2026-04-13
> 优先级说明：错误消息中英文混用，需统一为中文

---

## 现状

SQL 函数中 `raise exception` 的错误消息中英文混用。coverage、draft_report、submit_report 已是中文；analyst、template、sector/trigger 仍为英文。

## 需修改的英文消息（10 处）

### 030_table_functions_and_triggers.sql（6 处）

| 行 | 当前 | 改为 |
|---|------|------|
| 10 | `sector parent cannot reference itself` | `sector 父级不能引用自身` |
| 15 | `level 1 sector cannot have parent` | `一级行业不能设置父级` |
| 26 | `level 2 sector must reference an existing parent` | `二级行业必须引用已存在的父级` |
| 30 | `level 2 sector parent must be level 1` | `二级行业的父级必须是一级行业` |
| 34 | `sector hierarchy supports only two levels` | `行业层级最多支持两级` |
| 50 | `invalid report status transition: % -> %` | `无效的报告状态转换：% → %` |

### 045_analyst_functions.sql（2 处）

| 行 | 当前 | 改为 |
|---|------|------|
| 21 | `Analyst not found: %` | `找不到分析师：%` |
| 25 | `Analyst is inactive: %` | `分析师已停用：%` |

### 050_template_functions.sql（3 处）

| 行 | 当前 | 改为 |
|---|------|------|
| 63 | `Cannot reuse self: report_type=''%''` | `不能复用自身：report_type=''%''` |
| 71 | `Source template not found: ''%''` | `源模板未找到：''%''` |
| 76 | `Source template not published (empty path): ''%''` | `源模板未发布（路径为空）：''%''` |

### 105_remove_analyst_security_definer.sql（2 处，与 045 重复）

| 行 | 当前 | 改为 |
|---|------|------|
| 22 | `Analyst not found: %` | `找不到分析师：%` |
| 26 | `Analyst is inactive: %` | `分析师已停用：%` |

## 实现方式

新建迁移文件，逐个 `create or replace function` 重写受影响的函数，仅改错误消息文本，不改逻辑。

受影响的函数：
- `check_sector_parent()`（trigger function）
- `check_report_status_transition()`（trigger function）
- `resolve_analyst_by_email(text)`
- `reuse_template(text, text, text)`

## 注意

- 045 和 105 的 `resolve_analyst_by_email` 是同一函数的不同版本，105 是最终版本，两者都需改
- trigger function 的错误消息面向开发者而非终端用户，但统一中文仍有助于日志可读性
