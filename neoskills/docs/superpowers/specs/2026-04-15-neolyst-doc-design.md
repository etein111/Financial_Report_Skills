# neolyst 提示词 / 文档变更

## 背景

neolyst skill 缺少 6 张表（report / report_status_log / coverage / coverage_analyst / analyst / report_template）的读操作引导和报告文件下载引导。字典表文档与新增的"直接查表"内容属于同类，应集中到一个文件管理。

## 变更 1：SKILL.md 更新

### 1a. description 触发词补充

新增：`"查询报告"、"我的报告"、"查看报告"、"报告审计"、"报告状态日志"`

### 1b. 新增"报告表直接查询"段落

添加引导内容（加在 ## 接口 表格之后）：

- 用户不会给 report_id（UUID），按用户意图选择查询入口
- 查询入口对照表（ticker / status / analyst / title 模糊匹配 / 时间范围）
- 多条件可组合；report_id 从查询结果中获得，用于后续操作接口
- RLS 约束说明（admin 全部 / SA submitted+published+rejected / analyst 自己 owned + 已发布）
- 详细示例见 `references/direct-queries.md`

## 变更 2：新建 references/direct-queries.md

集中所有"直接用 client.table() 操作"的文档，替代 interfaces.md 中的"字典表直接操作"章节。

### 文件结构

```
# 直接查表操作

所有认证用户可读，写操作有角色约束。不封装函数，直接用 client.table() 操作。

## RLS 约束速查

| 表 | 读 | 写 |
|----|----|----|
| report | 按角色分级（见下方说明） | 走专用接口，不直接写 |
| report_status_log | 随 report 可见 | 触发器自动写入 |
| coverage | 所有认证用户 | admin only |
| coverage_analyst | 所有认证用户 | INSERT: admin/sa/analyst；其他: admin |
| analyst | 所有认证用户 | admin only |
| report_template | 所有认证用户 | admin only |
| region / sector / rating / report_type | 所有认证用户 | admin only |

## report

- 查询入口（ticker / status / lead_analyst_email / title 模糊 / created_at 范围）
- 查询示例
- 废弃提示：用 deactivate_report 接口，见 interfaces.md
- **文件下载**：查 report 表获取 word_path / pdf_path / model_path，调用 `storage.download(client, path, local_path)` 下载

## report_status_log

- 查询示例（按 report_id 查审计记录）

## coverage

- 字段说明、查询示例（按 ticker / sector / is_active）
- 写入示例（upsert / 停用）— admin only

## coverage_analyst

- 字段说明、查询示例（按 coverage_id）
- 写入示例（追加 / 移除）— INSERT: admin/sa/analyst；其他: admin

## analyst

- 查询示例（列出全部 / 按区域过滤 / 按在职状态过滤）
- 专用接口（resolve / search / upsert / set_active）仍保留在 interfaces.md

## report_template

- 查询示例（列出全部模板 / 按 report_type 过滤 / 按 language 过滤）
- 专用接口（resolve / upsert / reuse）仍保留在 interfaces.md

## 字典表（region / sector / rating / report_type）

- 从 interfaces.md 迁移，内容不变
- **sector 写入约束**：标注 `validate_sector_hierarchy` 触发器规则（二级树、level=1 无 parent、level=2 parent 必须是 level=1），避免写入失败
```

## 变更 3：interfaces.md 更新

### 3a. 删除"字典表直接操作"章节

整节迁移到 direct-queries.md 后删除。

### 3b. 新增 deactivate_report 接口（#16）

```python
from skills.neolyst.scripts.report import deactivate_report

result = deactivate_report(client, report_id)
# 返回：{"report_id": str, "is_active": False}
# admin only；report 不存在或已是 inactive：抛出 ValueError
```

## 不做的

- Storage 文件删除（Report / Coverage / Template）
- 报告记录删除
