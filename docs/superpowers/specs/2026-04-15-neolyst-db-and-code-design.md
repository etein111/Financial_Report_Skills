# neolyst 数据库变更 + Python 代码

## 背景

report 表有 status 状态机（draft / submitted / published / rejected），但缺少 is_active 字段，无法在不破坏状态机的前提下标记报告废弃。

## 变更 1：report 表增加 is_active 字段

- migration：`ALTER TABLE report ADD COLUMN is_active boolean NOT NULL DEFAULT true`
- 不影响现有数据（默认 true）
- 查询示例加 `.eq("is_active", True)` 过滤

## 变更 2：deactivate_report 接口

- 实现位置：`scripts/report.py`
- 签名：`deactivate_report(client, report_id) -> {"report_id": str, "is_active": False}`
- 行为：将 report.is_active 设为 false
- 权限：admin only
- 校验：report 存在 + 当前 is_active = true，否则抛 ValueError
- 文档位置：`references/interfaces.md`（作为 #16 接口）
- 测试：`tests/test_report.py` 新增 deactivate 用例

## 不做的

- 报告记录删除（有审计要求）
- 报告文件删除
- Coverage / Template Storage 清理
