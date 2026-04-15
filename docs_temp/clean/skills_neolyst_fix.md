# Schema 调整设想（待讨论）

核心目标：将文件编辑与审批工作分离，简化版本模型。

## 1. report_analyst 简化

`report_analyst` 本质是 `report` 的列表字段，无需两个时间戳。
可选方案：删除该表，在 `report` 上加两个字段——主作 email 和全部作者 email 列表。

## 2. report_status_log 增加元数据

新增 JSON 字段，保存状态流转时的 report 元数据（分析师、文件路径等）。

## 3. 文件版本存储

在 `reports/{report_id}/` 下按文档类型（report/model）和时间分目录。

## 4. 版本表替代方案

考虑用 `report_log` + `model_log` 替代 `report_version`：
- `report_log`: report_id, word_file_path, pdf_file_path, created_by, created_at
- `model_log`: report_id, model_file_path, created_by, created_at

待定：是否需要统一 file_log？是否需要保存 elements/abstract/body？

## 5. report 表精简

删除 `current_version_no`，直接记录 `word_path` 和 `pdf_path`。

## 6. 状态与权限梳理

原则：仅 `draft` 状态可修改 report 信息。文件可随时保存。
