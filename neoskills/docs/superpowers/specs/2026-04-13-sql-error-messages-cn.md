# P0：SQL 错误消息统一为中文

> 日期：2026-04-13
> 优先级：P0
> 数据库验证：已从 Supabase 实例查询确认

## 背景

SQL 函数中 `raise exception` 的错误消息中英文混用。coverage、draft_report、submit_report、validate_report、retract_report 已是中文；validate_sector_hierarchy、report_enforce_status_transition、resolve_analyst_by_email、reuse_template 仍为英文。

## 变更范围

### 层 1：SQL 迁移（新文件）

文件：`supabase/migrations/20260413000500_114_sql_error_messages_cn.sql`

4 个函数，11 处英文消息改为中文。仅改消息文本，不改函数签名、参数、返回类型、属性（language/stable/security definer 等）。

#### validate_sector_hierarchy() — 5 处

| # | 当前 | 改为 |
|---|------|------|
| 1 | `sector parent cannot reference itself` | `sector 父级不能引用自身` |
| 2 | `level 1 sector cannot have parent` | `一级行业不能设置父级` |
| 3 | `level 2 sector must reference an existing parent` | `二级行业必须引用已存在的父级` |
| 4 | `level 2 sector parent must be level 1` | `二级行业的父级必须是一级行业` |
| 5 | `sector hierarchy supports only two levels` | `行业层级最多支持两级` |

#### report_enforce_status_transition() — 1 处

| # | 当前 | 改为 |
|---|------|------|
| 6 | `invalid report status transition: % -> %` | `无效的报告状态转换：% → %` |

#### resolve_analyst_by_email(text) — 2 处

基于 105 版本（无 SECURITY DEFINER），保持函数属性不变。

| # | 当前 | 改为 |
|---|------|------|
| 7 | `Analyst not found: %` | `找不到分析师：%` |
| 8 | `Analyst is inactive: %` | `分析师已停用：%` |

#### reuse_template(text, text, text) — 3 处

| # | 当前 | 改为 |
|---|------|------|
| 9 | `Cannot reuse self: report_type=''%''` | `不能复用自身：report_type=''%''` |
| 10 | `Source template not found: ''%''` | `源模板未找到：''%''` |
| 11 | `Source template not published (empty path): ''%''` | `源模板未发布（路径为空）：''%''` |

### 层 2：Python 测试（2 个文件，4 处）

SQL RPC 错误通过 `rpc.call_rpc` → `ValueError(str(e))` 透传，测试断言需匹配中文消息。

#### tests/test_analyst.py

| 行 | 当前 | 改为 |
|---|------|------|
| 68 | `match="Analyst not found"` | `match="找不到分析师"` |
| 76 | `match="Analyst is inactive"` | `match="分析师已停用"` |

#### tests/test_template.py（仅 TestReuseTemplate）

| 行 | 当前 | 改为 |
|---|------|------|
| 91 | `match="self"` | `match="不能复用自身"` |
| 96 | `match="not found"` | `match="未找到"` |

### 层 3：文档（1 个文件，2 处）

#### references/interfaces.md

| 行 | 当前 | 改为 |
|---|------|------|
| 16 | `` `ValueError: Analyst is inactive: {email}` `` | `` `ValueError: 分析师已停用：{email}` `` |
| 229 | `"找不到分析师" 或 "Analyst is inactive"` | `"找不到分析师" 或 "分析师已停用"` |

### 不需要改的

- `scripts/template.py:99,103` — Python 侧 ValueError（`Template not found`、`Template not published`），非 RPC 错误
- `scripts/analyst.py:31` — 已经是中文 `"找不到分析师"`
- `tests/test_template.py:128,135` — 测试 Python 侧 resolve_template 的错误，不走 RPC

## 不改的内容

- 函数签名、参数类型、返回类型
- 函数属性（language, stable/volatile, security definer 等）
- 已是中文的函数（coverage、draft_report、submit_report、validate_report、retract_report）
